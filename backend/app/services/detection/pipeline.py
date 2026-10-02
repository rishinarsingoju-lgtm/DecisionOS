import hashlib
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    AuditEvent,
    Decision,
    DecisionCandidate,
    DemandHistory,
    InventoryBatch,
    InventoryPolicy,
    Location,
    Medicine,
    SupplierOffer,
)
from app.services.analysis.metrics import ZERO, demand_profile, exact_batch_alerts, supplier_metrics
from app.services.analysis.service import build_analysis
from app.services.decision.selection import select_action
from app.services.simulation.service import run_simulations
from app.services.verification.service import verify_claims

TRIGGER_CODES = {
    "EXPIRY_RISK": "EXP",
    "STOCKOUT_RISK": "STK",
    "CDSCO_EXACT_BATCH": "REG",
    "EXCESS_INVENTORY": "EXC",
    "DEMAND_SURGE": "SUR",
    "SUPPLIER_RELIABILITY": "SUP",
    "PROCUREMENT_OPPORTUNITY": "PRC",
    "INVENTORY_IMBALANCE": "IMB",
}


def detect_candidates(session: Session, today: date | None = None) -> list[DecisionCandidate]:
    today = today or datetime.now(UTC).date()
    candidates: list[DecisionCandidate] = []
    locations = list(session.scalars(select(Location)))
    medicines = list(session.scalars(select(Medicine)))
    grouped: dict[int, list[dict[str, Any]]] = {medicine.id: [] for medicine in medicines}

    for medicine in medicines:
        for location in locations:
            batches = list(session.scalars(select(InventoryBatch).where(
                InventoryBatch.medicine_id == medicine.id,
                InventoryBatch.location_id == location.id,
            )))
            if not batches:
                continue
            demand_rows = list(session.scalars(select(DemandHistory).where(
                DemandHistory.medicine_id == medicine.id,
                DemandHistory.location_id == location.id,
            ).order_by(DemandHistory.period_date)))
            profile = demand_profile(demand_rows)
            daily = profile["daily_demand"]
            raw_batches = [{"quantity": Decimal(batch.quantity), "expiry_date": batch.expiry_date, "id": batch.id} for batch in batches]
            alerts_by_batch = {batch.id: exact_batch_alerts(session, medicine.normalized_name, batch.batch_number) for batch in batches}
            usable_stock = sum((row["quantity"] for row in raw_batches if not alerts_by_batch[row["id"]]), ZERO)
            total_stock = sum((row["quantity"] for row in raw_batches), ZERO)
            offers = list(session.scalars(select(SupplierOffer).where(SupplierOffer.medicine_id == medicine.id)))
            lead_times = [offer.lead_time_days for offer in offers if offer.lead_time_days is not None]
            lead = min(lead_times) if lead_times else None
            policy = session.scalar(select(InventoryPolicy).where(
                InventoryPolicy.medicine_id == medicine.id,
                InventoryPolicy.location_id == location.id,
            ))
            safety_days = policy.safety_stock_days if policy else settings.stockout_buffer_days
            days_cover = usable_stock / daily if daily is not None and daily > ZERO else None
            evidence_base = [
                {"source_ref": f"inventory_batches#{batch.id}", "batch_number": batch.batch_number, "quantity": str(batch.quantity), "expiry_date": batch.expiry_date.isoformat()}
                for batch in batches
            ]

            matching_alerts = [(batch, alert) for batch in batches for alert in alerts_by_batch[batch.id]]
            for batch, alert in matching_alerts:
                candidates.append(_upsert_candidate(session, "CDSCO_EXACT_BATCH", "CRITICAL", medicine, location, [
                    {"source_ref": f"inventory_batches#{batch.id}", "batch_number": batch.batch_number},
                    {"source_ref": f"cdsco_alerts#{alert.id}", "data_origin": alert.data_origin, "nsq_result": alert.nsq_result},
                ], today))

            at_risk_batches = []
            if daily is not None:
                for batch in batches:
                    days_to_expiry = (batch.expiry_date - today).days
                    if 0 <= days_to_expiry <= settings.expiry_threshold_days and Decimal(batch.quantity) > daily * days_to_expiry and not alerts_by_batch[batch.id]:
                        at_risk_batches.append(batch)
            if at_risk_batches:
                candidates.append(_upsert_candidate(session, "EXPIRY_RISK", "CRITICAL", medicine, location, evidence_base, today))

            if daily is not None and lead is not None and days_cover is not None and days_cover < Decimal(lead + safety_days):
                candidates.append(_upsert_candidate(session, "STOCKOUT_RISK", "CRITICAL" if days_cover < Decimal(lead) else "HIGH", medicine, location, evidence_base, today))
            if days_cover is not None and days_cover > Decimal(settings.excess_cover_days):
                candidates.append(_upsert_candidate(session, "EXCESS_INVENTORY", "MEDIUM", medicine, location, evidence_base, today))
            if profile["growth_ratio"] is not None and profile["growth_ratio"] >= Decimal("0.25"):
                candidates.append(_upsert_candidate(session, "DEMAND_SURGE", "HIGH", medicine, location, evidence_base, today))

            supplier_deterioration = False
            for offer in offers:
                metrics = supplier_metrics(session, offer.supplier_id, medicine.id)
                if metrics["n_delivered"] >= 3 and metrics["on_time_rate"] is not None and metrics["on_time_rate"] < Decimal("0.75"):
                    supplier_deterioration = True
            if supplier_deterioration:
                candidates.append(_upsert_candidate(session, "SUPPLIER_RELIABILITY", "HIGH", medicine, location, evidence_base, today))

            current_costs = [Decimal(offer.quoted_price) for offer in offers]
            if len(current_costs) >= 2 and min(current_costs) < max(current_costs) * Decimal("0.95"):
                candidates.append(_upsert_candidate(session, "PROCUREMENT_OPPORTUNITY", "MEDIUM", medicine, location, evidence_base, today))

            grouped[medicine.id].append({"location": location, "daily": daily, "stock": usable_stock, "cover": days_cover, "lead": lead, "evidence": evidence_base})

    for medicine in medicines:
        positions = grouped[medicine.id]
        shortage = next((row for row in positions if row["cover"] is not None and row["lead"] is not None and row["cover"] < Decimal(row["lead"])), None)
        surplus = next((row for row in positions if row["cover"] is not None and row["cover"] > Decimal(settings.excess_cover_days)), None)
        if shortage and surplus and shortage["location"].id != surplus["location"].id:
            candidates.append(_upsert_candidate(session, "INVENTORY_IMBALANCE", "HIGH", medicine, surplus["location"], [
                *surplus["evidence"],
                {"source_ref": f"locations#{shortage['location'].id}", "receiver": shortage["location"].name, "stockout_cover_days": float(shortage["cover"])},
            ], today))
    session.flush()
    return candidates


def run_pipeline(session: Session, candidate: DecisionCandidate, today: date | None = None) -> Decision:
    today = today or datetime.now(UTC).date()
    analysis, evidence, snapshot = build_analysis(session, candidate, today)
    simulations = run_simulations(snapshot)
    chosen = select_action(simulations, candidate.trigger)
    verification: dict[str, Any]
    status: str
    selected_action: dict[str, Any] | None = None
    expected_impact: dict[str, Any] = {}
    if chosen is None:
        status = "INSUFFICIENT_EVIDENCE"
        verification = {
            "status": status,
            "match": False,
            "ai_calculation": None,
            "independent_recomputation": None,
            "claims": [],
            "reason": "Required numeric inputs are missing or no simulated action satisfies the risk constraint.",
        }
    else:
        ai_claims = {
            "expiry_loss": chosen["expiry_loss"],
            "stockout_risk": chosen["stockout_risk"],
            "procurement_cost": chosen["procurement_cost"],
            "redistribution_cost": chosen["redistribution_cost"],
            "transfer_quantity": chosen["transfer_quantity"],
            "order_quantity": chosen["order_quantity"],
            "quarantine_quantity": chosen["quarantine_quantity"],
        }
        fault = next((item.get("demo_fault_injection") for item in candidate.evidence if item.get("demo_fault_injection")), None)
        if fault and fault.get("enabled"):
            claim_name = str(fault.get("claim", "expiry_loss"))
            if ai_claims.get(claim_name) is not None:
                ai_claims[claim_name] = float(ai_claims[claim_name]) + float(fault.get("delta", 50))
        proposed = {
            "action": chosen["action"],
            "transfer_quantity": chosen["transfer_quantity"],
            "order_quantity": chosen["order_quantity"],
            "supplier_id": chosen["supplier_id"],
            "lead_time_days": chosen["lead_time_days"],
        }
        proposed["quarantine_quantity"] = chosen["quarantine_quantity"]
        verification = verify_claims(session, candidate, proposed, ai_claims, today)
        status = verification["status"]
        if status == "VERIFIED":
            selected_action = {**proposed, "label": chosen["label"], "quantity": chosen["quantity"]}
            expected_impact = chosen["expected_impact"]
        else:
            analysis["recommendation_state"] = "WITHHELD"
            analysis["why_withheld"] = "Independent recomputation did not match the decision calculation; no action is released."
        analysis["selected_action_proposal"] = chosen["action"] if status == "WITHHELD" else None

    analysis["simulation_assumptions"] = sorted({assumption for result in simulations for assumption in result["assumptions"]})
    if candidate.evidence and any(item.get("demo_fault_injection", {}).get("enabled") for item in candidate.evidence if isinstance(item, dict)):
        analysis["demo_note"] = "Synthetic verification fault injected into the AI-side claim for demonstration; not a production calculation path."
    decision_id = _decision_id(candidate.id)
    decision = session.scalar(select(Decision).where(Decision.candidate_id == candidate.id))
    if decision is None:
        decision = Decision(id=decision_id, candidate_id=candidate.id)
        session.add(decision)
        session.flush()
    decision.status = status
    decision.verification_status = status
    decision.selected_action = selected_action
    decision.analysis = analysis
    decision.simulation_results = simulations
    decision.expected_impact = expected_impact
    decision.verification_details = verification
    decision.evidence = evidence
    candidate.status = "COMPLETE" if status in {"VERIFIED", "WITHHELD"} else status

    audit_entries = [
        ("ANALYZE", "EVIDENCE_ASSEMBLED", {"evidence_count": len(evidence), "signals_missing": analysis["signals_missing"]}),
        ("SIMULATE", "ACTIONS_EVALUATED", {"action_count": len(simulations)}),
        ("DECIDE", "ACTION_SELECTED" if selected_action else "ACTION_NOT_RELEASED", {"verification_status": status, "selected_action": selected_action["action"] if selected_action else None}),
        ("VERIFY", "INDEPENDENT_CHECK", {"status": status, "match": verification.get("match")}),
    ]
    for stage, event_type, payload in audit_entries:
        event = AuditEvent(decision_id=decision.id, stage=stage, event_type=event_type, payload=payload, actor="SYSTEM · DETERMINISTIC")
        session.add(event)
        decision.audit.append({"time": datetime.now(UTC).isoformat(), "actor": event.actor, "stage": stage, "event": event_type, **payload})
    session.flush()
    return decision


def _upsert_candidate(
    session: Session,
    trigger: str,
    priority: str,
    medicine: Medicine,
    location: Location,
    evidence: list[dict[str, Any]],
    today: date,
) -> DecisionCandidate:
    candidate_id = f"CAND-{TRIGGER_CODES[trigger]}-{medicine.id}-{location.id}"
    existing = session.get(DecisionCandidate, candidate_id)
    if existing is not None:
        fault = [item for item in existing.evidence if item.get("demo_fault_injection")]
        existing.priority = priority
        existing.evidence = evidence + fault
        return existing
    candidate = DecisionCandidate(
        id=candidate_id,
        trigger=trigger,
        priority=priority,
        medicine_id=medicine.id,
        location_id=location.id,
        status="DETECTED",
        detected_at=datetime.combine(today, datetime.min.time(), tzinfo=UTC),
        evidence=evidence,
    )
    session.add(candidate)
    return candidate


def _decision_id(candidate_id: str) -> str:
    token = hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:10].upper()
    return f"DEC-{datetime.now(UTC).year}-{token}"