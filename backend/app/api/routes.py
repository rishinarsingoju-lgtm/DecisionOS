from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal, ROUND_CEILING
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import SessionLocal, engine, get_session
from app.models import (
    AuditEvent,
    CDSCOAlert,
    Decision,
    DecisionCandidate,
    DemandHistory,
    ExternalSourceStatus,
    InventoryBatch,
    InventoryPolicy,
    Location,
    Medicine,
    NPPAReferencePrice,
    Supplier,
    SupplierOffer,
)
from app.api.presenters import currency, present_decision
from app.schemas import (
    AnalysisRunResponse,
    DecisionView,
    EvidenceResponse,
    HealthResponse,
    InventoryResponse,
    OverviewResponse,
    ProcurementResponse,
    ReviewRequest,
    ReviewResponse,
    SystemStatusResponse,
)
from app.services.analysis.metrics import ZERO, demand_profile, exact_batch_alerts, supplier_metrics
from app.services.detection.pipeline import detect_candidates, run_pipeline


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    if engine is not None:
        engine.dispose()


app = FastAPI(title="DecisionOS API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health", response_model=HealthResponse)
def health(session: Session = Depends(get_session)) -> HealthResponse:
    session.execute(text("SELECT 1"))
    return HealthResponse(status="ok", database="connected", version=app.version)


@app.get("/api/overview", response_model=OverviewResponse)
def overview(session: Session = Depends(get_session)) -> OverviewResponse:
    decisions = _all_decisions(session)
    views = [present_decision(decision) for decision in decisions]
    attention = [view for view in views if view.approvalStatus == "PENDING"]
    critical = [view for view in attention if view.priority == "CRITICAL"]
    verified = [view for view in views if view.status == "VERIFIED"]
    benefits = [
        Decimal(str(view.expectedImpact.get("net_benefit_vs_baseline")))
        for view in verified
        if view.expectedImpact.get("net_benefit_vs_baseline") is not None
    ]
    source_rows = _source_views(session)
    alerts = _alert_views(session)
    last = max((decision.created_at for decision in decisions), default=None)
    return OverviewResponse(
        summary={
            "decisionsRequiringAttention": len(attention),
            "criticalDecisions": len(critical),
            "emergingRisks": sum(1 for view in attention if view.priority in {"HIGH", "MEDIUM"}),
            "verifiedDecisions": len(verified),
            "potentialImpact": currency(sum(benefits, ZERO)),
        },
        decisions=views,
        recentDecisions=views[:8],
        alerts=alerts,
        sources=source_rows,
        systemStatus={"status": "ACTIVE" if decisions else "AWAITING_SCAN", "lastAnalysis": last.isoformat() if last else None, "dataOrigin": "SYNTHETIC_CLIENT"},
    )


@app.get("/api/decisions", response_model=list[DecisionView])
def list_decisions(session: Session = Depends(get_session)) -> list[DecisionView]:
    return [present_decision(decision) for decision in _all_decisions(session)]


@app.get("/api/decisions/{decision_id}", response_model=DecisionView)
def decision_detail(decision_id: str, session: Session = Depends(get_session)) -> DecisionView:
    decision = _find_decision(session, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return present_decision(decision)


@app.post("/api/decisions/{decision_id}/approve", response_model=ReviewResponse)
def approve_decision(decision_id: str, payload: ReviewRequest, session: Session = Depends(get_session)) -> ReviewResponse:
    decision = _find_decision(session, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    if decision.verification_status != "VERIFIED":
        raise HTTPException(status_code=409, detail=f"Cannot approve a {decision.verification_status} decision")
    if decision.approval_status != "PENDING":
        raise HTTPException(status_code=409, detail=f"Decision is already {decision.approval_status}")
    _record_review(decision, session, "APPROVED", payload.comment)
    session.commit()
    return ReviewResponse(id=decision.id, verificationStatus=decision.verification_status, approvalStatus=decision.approval_status, message="Approval recorded. No purchase, transfer, or other external action was executed.")


@app.post("/api/decisions/{decision_id}/reject", response_model=ReviewResponse)
def reject_decision(decision_id: str, payload: ReviewRequest, session: Session = Depends(get_session)) -> ReviewResponse:
    decision = _find_decision(session, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    if decision.approval_status != "PENDING":
        raise HTTPException(status_code=409, detail=f"Decision is already {decision.approval_status}")
    _record_review(decision, session, "REJECTED", payload.comment)
    session.commit()
    return ReviewResponse(id=decision.id, verificationStatus=decision.verification_status, approvalStatus=decision.approval_status, message="Rejection recorded. No external action was executed.")


@app.get("/api/inventory", response_model=InventoryResponse)
def inventory(session: Session = Depends(get_session)) -> InventoryResponse:
    batches = list(session.scalars(select(InventoryBatch).options(
        selectinload(InventoryBatch.medicine),
        selectinload(InventoryBatch.location),
    ).order_by(InventoryBatch.expiry_date)))
    rows = []
    today = datetime.now(UTC).date()
    for batch in batches:
        demand_rows = list(session.scalars(select(DemandHistory).where(
            DemandHistory.medicine_id == batch.medicine_id,
            DemandHistory.location_id == batch.location_id,
        ).order_by(DemandHistory.period_date)))
        profile = demand_profile(demand_rows)
        daily = profile["daily_demand"]
        stock_rows = list(session.scalars(select(InventoryBatch).where(
            InventoryBatch.medicine_id == batch.medicine_id,
            InventoryBatch.location_id == batch.location_id,
        )))
        usable = sum((Decimal(row.quantity) for row in stock_rows if not exact_batch_alerts(session, batch.medicine.normalized_name, row.batch_number)), ZERO)
        cover = usable / daily if daily is not None and daily > ZERO else None
        days_to_expiry = (batch.expiry_date - today).days
        exposed = daily is not None and days_to_expiry >= 0 and Decimal(batch.quantity) > daily * days_to_expiry
        policy = session.scalar(select(InventoryPolicy).where(InventoryPolicy.medicine_id == batch.medicine_id, InventoryPolicy.location_id == batch.location_id))
        if any(exact_batch_alerts(session, batch.medicine.normalized_name, row.batch_number) for row in stock_rows if row.id == batch.id):
            state = "Quarantined"
            expiry_text = f"Regulatory alert · {batch.quantity:g} units"
        elif exposed:
            state = "Action required"
            expiry_text = f"High · {batch.quantity:g} units, {days_to_expiry} days"
        elif cover is not None and policy and cover < Decimal((policy.safety_stock_days or 0) + settings.stockout_buffer_days):
            state = "Stockout risk"
            expiry_text = "Low expiry risk"
        elif cover is not None and cover > Decimal(settings.excess_cover_days):
            state = "Monitor"
            expiry_text = "Excess inventory"
        elif days_to_expiry <= settings.expiry_threshold_days:
            state = "Monitor"
            expiry_text = f"Watch · {days_to_expiry} days"
        else:
            state = "Within range"
            expiry_text = "No near-term exposure"
        rows.append({
            "medicine": batch.medicine.name,
            "batch": batch.batch_number,
            "location": batch.location.name,
            "available": f"{batch.quantity:,.0f}",
            "demand": f"{daily:,.0f} / day" if daily is not None else "Unknown",
            "cover": f"{cover:.0f} days" if cover is not None else "Unknown",
            "expiry": expiry_text,
            "status": state,
            "medicineId": batch.medicine_id,
            "locationId": batch.location_id,
            "dataOrigin": batch.data_origin,
        })
    return InventoryResponse(rows=rows, dataOrigin="SYNTHETIC_CLIENT")


@app.get("/api/procurement", response_model=ProcurementResponse)
def procurement(session: Session = Depends(get_session)) -> ProcurementResponse:
    medicine = session.scalar(select(Medicine).where(Medicine.normalized_name == "amoxicillin 500mg"))
    if medicine is None:
        medicine = session.scalar(select(Medicine).order_by(Medicine.id))
    if medicine is None:
        return ProcurementResponse(medicine="No seeded medicine", medicineId=0, requiredQuantity=0, referencePrice="Unavailable", suppliers=[], dataOrigin="SYNTHETIC_CLIENT")
    suppliers = list(session.scalars(select(Supplier).join(SupplierOffer).where(SupplierOffer.medicine_id == medicine.id).order_by(Supplier.name)))
    offers = {offer.supplier_id: offer for offer in session.scalars(select(SupplierOffer).where(SupplierOffer.medicine_id == medicine.id))}
    result = []
    for supplier in suppliers:
        offer = offers[supplier.id]
        metrics = supplier_metrics(session, supplier.id, medicine.id)
        quality = float(metrics["quality_acceptance"]) if metrics["quality_acceptance"] is not None else None
        reliability = float(metrics["on_time_rate"]) if metrics["on_time_rate"] is not None else None
        lead = offer.lead_time_days if offer.lead_time_days is not None else (int(metrics["average_lead_days"]) if metrics["average_lead_days"] is not None else None)
        tradeoffs = []
        if reliability is None:
            tradeoffs.append("delivery reliability UNKNOWN")
        elif reliability < 0.9:
            tradeoffs.append("observed delivery reliability below 90%")
        if quality is None:
            tradeoffs.append("quality history UNKNOWN")
        elif quality < 0.98:
            tradeoffs.append("quality acceptance below 98%")
        if lead is not None:
            tradeoffs.append(f"quoted lead time {lead} days")
        result.append({
            "id": supplier.id,
            "name": supplier.name,
            "price": f"₹{Decimal(offer.quoted_price):,.2f} / unit",
            "priceValue": float(offer.quoted_price),
            "quality": f"{quality * 100:.1f}% · {metrics['n_quality_records']} records" if quality is not None else "Unknown",
            "qualityValue": quality,
            "reliability": f"{reliability * 100:.1f}% · {metrics['n_delivered']} deliveries" if reliability is not None else "Unknown",
            "reliabilityValue": reliability,
            "lead": f"{lead} days" if lead is not None else "Unknown",
            "leadDays": lead,
            "availability": f"{offer.available_quantity:,.0f} units" if offer.available_quantity is not None else "Unknown",
            "availabilityValue": float(offer.available_quantity) if offer.available_quantity is not None else None,
            "evidence": f"{metrics['n_orders']} orders · {metrics['n_quality_records']} quality records" if metrics["n_orders"] else "No completed orders",
            "tradeoff": "; ".join(tradeoffs) if tradeoffs else "No adverse observed history; sample size remains visible.",
            "status": "Known" if metrics["n_orders"] else "Limited evidence",
            "sampleSize": metrics["n_orders"],
        })
    reference = session.scalar(select(NPPAReferencePrice).where(NPPAReferencePrice.medicine_id == medicine.id).order_by(NPPAReferencePrice.effective_date.desc()))
    stockout_candidate = session.scalar(select(DecisionCandidate).where(
        DecisionCandidate.medicine_id == medicine.id,
        DecisionCandidate.trigger == "STOCKOUT_RISK",
    ).order_by(DecisionCandidate.detected_at.desc()).limit(1))
    required: int | None = None
    if stockout_candidate is not None:
        demand_rows = list(session.scalars(select(DemandHistory).where(
            DemandHistory.medicine_id == medicine.id,
            DemandHistory.location_id == stockout_candidate.location_id,
        ).order_by(DemandHistory.period_date)))
        profile = demand_profile(demand_rows)
        lead_times = [offer.lead_time_days for offer in offers.values() if offer.lead_time_days is not None]
        policy = session.scalar(select(InventoryPolicy).where(
            InventoryPolicy.medicine_id == medicine.id,
            InventoryPolicy.location_id == stockout_candidate.location_id,
        ))
        if profile["daily_demand"] is not None and lead_times and policy is not None:
            batches = list(session.scalars(select(InventoryBatch).where(
                InventoryBatch.medicine_id == medicine.id,
                InventoryBatch.location_id == stockout_candidate.location_id,
            )))
            usable_stock = sum((Decimal(batch.quantity) for batch in batches if not exact_batch_alerts(session, medicine.normalized_name, batch.batch_number)), ZERO)
            demand_window = Decimal(int(min(lead_times) + policy.safety_stock_days))
            shortfall = max(ZERO, profile["daily_demand"] * demand_window - usable_stock)
            required = int(shortfall.to_integral_value(rounding=ROUND_CEILING))
    reference_label = f"₹{Decimal(reference.reference_price):,.2f} · synthetic example" if reference and reference.data_origin.startswith("SYNTHETIC") else f"₹{Decimal(reference.reference_price):,.2f}" if reference else "Unavailable"
    return ProcurementResponse(medicine=medicine.name, medicineId=medicine.id, requiredQuantity=required, referencePrice=reference_label, suppliers=result, dataOrigin="SYNTHETIC_CLIENT")


@app.get("/api/evidence", response_model=EvidenceResponse)
def evidence(session: Session = Depends(get_session)) -> EvidenceResponse:
    alerts = _alert_views(session)
    return EvidenceResponse(sources=_source_views(session), alerts=alerts)


@app.get("/api/system-status", response_model=SystemStatusResponse)
def system_status(session: Session = Depends(get_session)) -> SystemStatusResponse:
    latest = session.scalar(select(func.max(Decision.created_at)))
    decisions_count = session.scalar(select(func.count(Decision.id))) or 0
    return SystemStatusResponse(
        status="ACTIVE" if decisions_count else "AWAITING_SCAN",
        monitoring="DATABASE_BACKED · AUTONOMOUS SCAN MANUAL",
        lastAnalysis=latest.isoformat() if latest else None,
        deterministicOnly=True,
        pipeline=[
            {"name": "Detection", "status": "READY"},
            {"name": "Analyze", "status": "DETERMINISTIC"},
            {"name": "Simulate", "status": "DETERMINISTIC"},
            {"name": "Decide", "status": "RULE_BASED"},
            {"name": "Verify", "status": "INDEPENDENT"},
            {"name": "Human review", "status": "REQUIRED · NO EXECUTION"},
        ],
        sources=_source_views(session),
    )


@app.post("/api/analysis/run", response_model=AnalysisRunResponse)
def run_analysis(session: Session = Depends(get_session)) -> AnalysisRunResponse:
    candidates = detect_candidates(session)
    session.flush()
    results = []
    for candidate in candidates:
        results.append(run_pipeline(session, candidate))
    session.commit()
    return AnalysisRunResponse(
        candidatesDetected=len(candidates),
        decisionsProcessed=len(results),
        decisions=[present_decision(decision) for decision in results],
    )


def _all_decisions(session: Session) -> list[Decision]:
    return list(session.scalars(select(Decision).options(
        selectinload(Decision.candidate).selectinload(DecisionCandidate.medicine),
        selectinload(Decision.candidate).selectinload(DecisionCandidate.location),
        selectinload(Decision.audit_events),
    ).order_by(Decision.created_at.desc())))


def _find_decision(session: Session, key: str) -> Decision | None:
    return session.scalar(select(Decision).options(
        selectinload(Decision.candidate).selectinload(DecisionCandidate.medicine),
        selectinload(Decision.candidate).selectinload(DecisionCandidate.location),
        selectinload(Decision.audit_events),
    ).where((Decision.id == key) | (Decision.candidate_id == key)))


def _record_review(decision: Decision, session: Session, state: str, comment: str | None) -> None:
    decision.approval_status = state
    payload = {"comment": comment} if comment else {}
    session.add(AuditEvent(decision_id=decision.id, stage="HUMAN_REVIEW", event_type=state, payload=payload, actor="HUMAN · DEMO USER"))
    audit = list(decision.audit or [])
    audit.append({"time": datetime.now(UTC).isoformat(), "actor": "HUMAN · DEMO USER", "stage": "HUMAN_REVIEW", "event": state, **payload})
    decision.audit = audit


def _source_views(session: Session) -> list[dict[str, Any]]:
    rows = {row.source: row for row in session.scalars(select(ExternalSourceStatus))}
    sources = []
    for key, purpose in [
        ("WHO ICD", "Disease terminology normalization"),
        ("Open-Meteo", "Weather context for demand signals"),
        ("CDSCO", "NSQ batch alerts"),
        ("NPPA", "Reference price context"),
    ]:
        row = rows.get(key)
        if row is None:
            status_value, detail, kind = "Unavailable", "No successful source snapshot recorded", "unavailable"
        else:
            status_value = row.status
            detail = row.detail
            kind = "matched" if status_value in {"Available", "Matched"} else "stale" if status_value == "Stale" else "unavailable"
        sources.append({"name": key, "purpose": purpose, "status": status_value, "detail": detail, "kind": kind, "sourceType": "EXTERNAL"})
    return sources


def _alert_views(session: Session) -> list[dict[str, Any]]:
    result = []
    for alert in session.scalars(select(CDSCOAlert).order_by(CDSCOAlert.ingested_at.desc())):
        result.append({
            "id": alert.id,
            "source": "CDSCO",
            "productName": alert.product_name,
            "normalizedProductName": alert.normalized_product_name,
            "batchNumber": alert.batch_number,
            "result": alert.nsq_result,
            "manufacturer": alert.manufactured_by,
            "reportingSource": alert.reporting_source,
            "ingestedAt": alert.ingested_at.isoformat(),
            "dataOrigin": alert.data_origin,
            "status": "Matched evidence",
        })
    return result