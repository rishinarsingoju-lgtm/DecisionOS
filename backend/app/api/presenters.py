from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.models import Decision
from app.schemas import DecisionView


def currency(value: Any) -> str:
    if value is None:
        return "Unknown"
    amount = Decimal(str(value))
    return f"₹{amount:,.0f}"


def percentage(value: Any) -> str:
    if value is None:
        return "Unknown"
    return f"{Decimal(str(value)) * 100:.1f}%"


def _action_text(selected: dict[str, Any] | None) -> str:
    if not selected:
        return "No released recommendation; the decision is not approved for action."
    action = selected.get("action")
    quantity = selected.get("quantity", 0)
    if action == "REDISTRIBUTE":
        return f"Redistribute {quantity:,} units to locations with recorded demand deficit."
    if action == "QUARANTINE_MATCHED_BATCH":
        return f"Quarantine {quantity:,} units from the exact batch matched to a regulatory alert; human quality review is required."
    if action in {"REORDER", "CHANGE_SUPPLIER", "SPLIT_PROCUREMENT"}:
        return f"{action.replace('_', ' ').title()} {quantity:,} units from the evaluated supplier quote."
    if action == "PRIORITIZE_FEFO":
        return "Prioritize first-expiry-first-out consumption across eligible batches."
    return "Do nothing; retain the current supply position and monitor exposure."


def present_decision(decision: Decision) -> DecisionView:
    candidate = decision.candidate
    medicine = candidate.medicine
    location = candidate.location
    analysis = decision.analysis or {}
    signals = analysis.get("signals", {})
    simulations = decision.simulation_results or []
    baseline = next((row for row in simulations if row.get("action") == "DO_NOTHING"), None)
    selected = decision.selected_action if decision.verification_status == "VERIFIED" else None
    selected_result = next((row for row in simulations if selected and row.get("action") == selected.get("action")), None)
    expiring_batches = [item for item in decision.evidence if item.get("type") == "inventory_batch" and item.get("summary")]
    expiry_loss = baseline.get("expiry_loss") if baseline else None
    before_risk = baseline.get("stockout_risk") if baseline else None
    after_risk = selected_result.get("stockout_risk") if selected_result else None
    stockout_text = f"{percentage(before_risk)} → {percentage(after_risk)}" if selected else f"{percentage(before_risk)} → withheld"
    actions = [
        {
            "action": row.get("label", row.get("action", "Unknown")),
            "loss": currency(row.get("expiry_loss")),
            "stockout": percentage(row.get("stockout_risk")),
            "cost": currency((row.get("procurement_cost") or 0) + (row.get("redistribution_cost") or 0)),
            "impact": f"Net benefit {currency((row.get('expected_impact') or {}).get('net_benefit_vs_baseline'))}",
            "recommendation": bool(selected and selected.get("action") == row.get("action")),
        }
        for row in simulations
    ]
    audit = decision.audit_events or []
    audit_rows = [
        {
            "id": event.id,
            "time": event.created_at.astimezone(UTC).strftime("%H:%M:%S"),
            "actor": event.actor,
            "event": _audit_text(event.event_type, event.payload),
        }
        for event in audit
    ]
    verification = decision.verification_details or {}
    ai = verification.get("ai_calculation") or {}
    independent = verification.get("independent_recomputation") or {}
    proof_claim = "expiry_loss"
    ai_text = f"{currency(ai.get(proof_claim))} exposure" if ai.get(proof_claim) is not None else "Not calculated"
    verifier_text = f"{currency(independent.get(proof_claim))} exposure" if independent.get(proof_claim) is not None else "Not recomputed"
    verification_note = (
        "Independent recomputation matched all critical numerical claims."
        if decision.verification_status == "VERIFIED"
        else "Mismatch detected by the independent verifier. Recommendation withheld; no approval or execution is permitted."
        if decision.verification_status == "WITHHELD"
        else "Required numeric evidence is missing; no recommendation was released."
    )
    demand_growth = signals.get("demand_growth")
    disease_value = signals.get("disease_concentration")
    seasonal_value = signals.get("seasonality_multiplier")
    lead_value = signals.get("supplier_lead_time_days")
    expiry_display = "No near-term batch expiry identified"
    if expiring_batches:
        expiry_display = expiring_batches[0]["summary"].split(":", 1)[-1].strip()
    data_origin = candidate.evidence[0].get("data_origin", "SYNTHETIC_CLIENT") if candidate.evidence else "SYNTHETIC_CLIENT"
    return DecisionView(
        id=decision.id,
        candidateId=candidate.id,
        medicine=medicine.name,
        sku=medicine.normalized_name,
        location=location.name,
        region=location.region,
        priority=candidate.priority,
        status=decision.verification_status,
        trigger=candidate.trigger,
        whyItMatters=analysis.get("why_it_matters", candidate.trigger.replace("_", " ").title()),
        recommendation=_action_text(selected),
        impact=(f"Expiry loss avoided: {currency((decision.expected_impact or {}).get('net_benefit_vs_baseline'))}; stockout risk {stockout_text}" if selected else "Expected impact withheld until verification passes."),
        expiryLoss=currency(expiry_loss),
        stockoutRisk=stockout_text,
        demand=f"{Decimal(str(demand_growth)):+.1%}" if demand_growth is not None else f"{signals.get('estimated_daily_demand')} units / day" if signals.get("estimated_daily_demand") is not None else "Unknown",
        disease=f"{medicine.disease_category or 'Disease signal'} · {Decimal(str(disease_value)):.2f}×" if disease_value is not None else "Unknown · no matched signal",
        seasonality=f"{Decimal(str(seasonal_value)):.2f}×" if seasonal_value is not None else "Unknown · no configured factor",
        inventory=f"{signals.get('current_inventory'):,.0f} units" if signals.get("current_inventory") is not None else "Unknown",
        expiry=expiry_display,
        leadTime=f"{lead_value} days" if lead_value is not None else "Unknown",
        weather=(f"{signals.get('weather_precipitation_mm')} mm precipitation" if signals.get("weather_precipitation_mm") is not None else "Unavailable · omitted from demand estimate"),
        verificationAi=ai_text,
        verificationIndependent=verifier_text,
        verificationNote=verification_note,
        updated=decision.created_at.astimezone(UTC).strftime("%H:%M UTC"),
        approvalStatus=decision.approval_status,
        dataOrigin=data_origin,
        actions=actions,
        auditEvents=audit_rows,
        evidenceItems=decision.evidence or [],
        analysis=analysis,
        simulations=simulations,
        selectedAction=selected,
        expectedImpact=decision.expected_impact or {},
        verification=verification,
        audit=decision.audit or [],
    )


def _audit_text(event_type: str, payload: dict[str, Any]) -> str:
    if event_type == "EVIDENCE_ASSEMBLED":
        return f"Evidence assembled from {payload.get('evidence_count', 0)} input records; missing signals: {', '.join(payload.get('signals_missing') or []) or 'none'}"
    if event_type == "ACTIONS_EVALUATED":
        return f"Deterministic simulation evaluated {payload.get('action_count', 0)} candidate actions."
    if event_type == "INDEPENDENT_CHECK":
        return f"Independent verification result: {payload.get('status')}."
    return f"Decision stage recorded: {event_type.lower().replace('_', ' ')}."