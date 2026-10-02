import math
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import CDSCOAlert, DemandHistory, DecisionCandidate, DiseaseSignal, InventoryBatch, InventoryPolicy, SeasonalFactor, SupplierOffer


def _independent_expiry_ledger(lots: list[dict[str, Any]], demand_per_day: Decimal, today: date) -> Decimal:
    stock = [dict(lot, balance=Decimal(lot["quantity"])) for lot in sorted(lots, key=lambda row: (row["expiry_date"], row["batch_number"]))]
    limit = max(((lot["expiry_date"] - today).days for lot in stock), default=0)
    loss = Decimal("0")
    for offset in range(max(0, min(limit, 180)) + 2):
        current_date = today + timedelta(days=offset)
        for lot in stock:
            if lot["expiry_date"] <= current_date and lot["balance"] > 0:
                loss += lot["balance"] * Decimal(lot["unit_cost"])
                lot["balance"] = Decimal("0")
        remaining_demand = demand_per_day
        for lot in stock:
            if lot["expiry_date"] >= current_date and lot["balance"] > 0:
                consumed = min(lot["balance"], remaining_demand)
                lot["balance"] -= consumed
                remaining_demand -= consumed
                if remaining_demand <= 0:
                    break
    return loss


def _independent_stockout_probability(stock: Decimal, daily: Decimal, deviation: Decimal, days: int) -> Decimal:
    mean = float(daily * days)
    sigma = float(deviation) * math.sqrt(days)
    if sigma == 0:
        return Decimal("1") if Decimal(str(mean)) > stock else Decimal("0")
    z = (float(stock) - mean) / sigma
    probability = 0.5 * math.erfc(z / math.sqrt(2.0))
    return Decimal(str(min(1.0, max(0.0, probability))))


def recompute_raw_claims(
    session: Session,
    candidate: DecisionCandidate,
    selected_action: dict[str, Any],
    today: date,
) -> dict[str, Decimal | int | None]:
    batches = list(session.scalars(select(InventoryBatch).where(
        InventoryBatch.medicine_id == candidate.medicine_id,
        InventoryBatch.location_id == candidate.location_id,
    )))
    alerts = list(session.scalars(select(CDSCOAlert)))
    alert_pairs = {
        (" ".join(alert.normalized_product_name.lower().split()), "".join(alert.batch_number.upper().split()))
        for alert in alerts
    }
    medicine = candidate.medicine
    normalized_name = " ".join(medicine.normalized_name.lower().split())
    usable = [
        batch for batch in batches
        if (normalized_name, "".join(batch.batch_number.upper().split())) not in alert_pairs
    ]
    matched_quantity = sum((Decimal(batch.quantity) for batch in batches if (
        " ".join(candidate.medicine.normalized_name.lower().split()),
        "".join(batch.batch_number.upper().split()),
    ) in alert_pairs), Decimal("0"))
    quarantine_quantity = matched_quantity if selected_action.get("action") == "QUARANTINE_MATCHED_BATCH" else Decimal("0")
    quantities = [{
        "batch_number": batch.batch_number,
        "quantity": str(batch.quantity),
        "unit_cost": str(batch.unit_cost),
        "expiry_date": batch.expiry_date,
    } for batch in usable]
    movement = Decimal(str(selected_action.get("transfer_quantity", 0)))
    unallocated_move = movement
    for lot in sorted(quantities, key=lambda row: (row["expiry_date"], row["batch_number"])):
        available = Decimal(lot["quantity"])
        moved = min(available, unallocated_move)
        lot["quantity"] = str(available - moved)
        unallocated_move -= moved
    demand_rows = list(session.scalars(select(DemandHistory).where(
        DemandHistory.medicine_id == candidate.medicine_id,
        DemandHistory.location_id == candidate.location_id,
    ).order_by(DemandHistory.period_date)))
    if not demand_rows:
        return {"expiry_loss": None, "stockout_risk": None, "procurement_cost": None, "redistribution_cost": None, "transfer_quantity": int(movement), "order_quantity": None, "quarantine_quantity": int(quarantine_quantity)}
    recent = [Decimal(row.demand) for row in demand_rows[-7:]]
    daily = sum(recent, Decimal("0")) / Decimal(len(recent))
    medicine = candidate.medicine
    disease = session.scalar(select(DiseaseSignal).where(
        DiseaseSignal.region == candidate.location.region,
        DiseaseSignal.disease.ilike(f"%{medicine.disease_category or ''}%"),
    ).order_by(DiseaseSignal.period_date.desc())) if medicine.disease_category else None
    seasonal = session.scalar(select(SeasonalFactor).where(
        SeasonalFactor.disease_category == medicine.disease_category,
        SeasonalFactor.month == today.month,
        (SeasonalFactor.region == candidate.location.region) | (SeasonalFactor.region.is_(None)),
    ).order_by(SeasonalFactor.region.is_(None))) if medicine.disease_category else None
    if disease and disease.concentration is not None:
        daily *= min(Decimal("1.5"), max(Decimal("0.75"), Decimal(disease.concentration)))
    if seasonal:
        daily *= min(Decimal("1.5"), max(Decimal("0.75"), Decimal(seasonal.multiplier)))
    prior_window = [Decimal(row.demand) for row in demand_rows[-28:]]
    if len(prior_window) < 2:
        return {"expiry_loss": None, "stockout_risk": None, "procurement_cost": None, "redistribution_cost": None, "transfer_quantity": int(movement), "order_quantity": None, "quarantine_quantity": int(quarantine_quantity)}
    mean = sum(prior_window, Decimal("0")) / Decimal(len(prior_window))
    variance = sum((value - mean) ** 2 for value in prior_window) / Decimal(len(prior_window))
    deviation = Decimal(str(math.sqrt(float(variance))))
    stock = sum((Decimal(lot["quantity"]) for lot in quantities), Decimal("0"))
    expiry_loss = _independent_expiry_ledger(quantities, daily, today)
    exposure = int(selected_action.get("lead_time_days") or 0)
    risk = _independent_stockout_probability(stock, daily, deviation, exposure)

    order_quantity = int(selected_action.get("order_quantity") or 0)
    supplier_id = selected_action.get("supplier_id")
    procurement_cost: Decimal | None = Decimal("0")
    if order_quantity:
        offer = session.scalar(select(SupplierOffer).where(
            SupplierOffer.supplier_id == supplier_id,
            SupplierOffer.medicine_id == candidate.medicine_id,
        )) if supplier_id is not None else None
        procurement_cost = Decimal(order_quantity) * Decimal(offer.quoted_price) if offer is not None else None
    policy = session.scalar(select(InventoryPolicy).where(
        InventoryPolicy.medicine_id == candidate.medicine_id,
        InventoryPolicy.location_id == candidate.location_id,
    ))
    per_unit_cost = Decimal(policy.redistribution_cost_per_unit) if policy and policy.redistribution_cost_per_unit is not None else None
    redistribution_cost = movement * per_unit_cost if per_unit_cost is not None else (Decimal("0") if movement == 0 else None)
    return {
        "expiry_loss": expiry_loss,
        "stockout_risk": risk,
        "procurement_cost": procurement_cost,
        "redistribution_cost": redistribution_cost,
        "transfer_quantity": int(movement),
        "order_quantity": order_quantity,
        "quarantine_quantity": int(quarantine_quantity),
    }


def verify_claims(
    session: Session,
    candidate: DecisionCandidate,
    selected_action: dict[str, Any],
    ai_claims: dict[str, Any],
    today: date,
) -> dict[str, Any]:
    recomputed = recompute_raw_claims(session, candidate, selected_action, today)
    tolerances = {
        "expiry_loss": Decimal(str(settings.currency_tolerance)),
        "procurement_cost": Decimal(str(settings.currency_tolerance)),
        "redistribution_cost": Decimal(str(settings.currency_tolerance)),
        "stockout_risk": Decimal(str(settings.probability_tolerance)),
        "transfer_quantity": Decimal("0"),
        "order_quantity": Decimal("0"),
        "quarantine_quantity": Decimal("0"),
    }
    claims = []
    for name, independent in recomputed.items():
        proposed = ai_claims.get(name)
        if proposed is None or independent is None:
            matched = proposed is None and independent is None
        else:
            matched = abs(Decimal(str(proposed)) - Decimal(str(independent))) <= tolerances[name]
        claims.append({
            "claim": name,
            "ai_calculation": proposed,
            "independent_recomputation": float(independent) if isinstance(independent, Decimal) else independent,
            "status": "MATCH" if matched else "MISMATCH",
        })
    matched = all(claim["status"] == "MATCH" for claim in claims)
    return {
        "status": "VERIFIED" if matched else "WITHHELD",
        "match": matched,
        "ai_calculation": ai_claims,
        "independent_recomputation": {key: float(value) if isinstance(value, Decimal) else value for key, value in recomputed.items()},
        "claims": claims,
        "tolerances": {key: float(value) for key, value in tolerances.items()},
        "method": "Raw-table reread with independent day-by-day FEFO ledger and erfc stockout calculation.",
    }