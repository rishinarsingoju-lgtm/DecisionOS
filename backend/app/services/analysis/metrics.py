import re
from datetime import date, timedelta
from decimal import Decimal
from statistics import NormalDist, pstdev
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CDSCOAlert, DemandHistory, SupplierQualityEvent, SupplierTransaction

ZERO = Decimal("0")
ONE = Decimal("1")


def as_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def normalize_product(value: str) -> str:
    normalized = value.lower().replace("milligrams", "mg").replace("milligram", "mg")
    normalized = re.sub(r"\b(tablets?|capsules?|ip|usp)\b", " ", normalized)
    normalized = re.sub(r"(\d+(?:\.\d+)?)\s+mg\b", r"\1mg", normalized)
    return " ".join(re.findall(r"[a-z0-9.]+", normalized))


def normalize_batch(value: str) -> str:
    return re.sub(r"\s+", "", value).upper()


def demand_profile(rows: list[DemandHistory]) -> dict[str, Decimal | None]:
    values = [Decimal(row.demand) for row in rows]
    if not values:
        return {"daily_demand": None, "baseline_demand": None, "std_daily_demand": None, "growth_ratio": None}
    recent = values[-7:]
    baseline_window = values[-28:]
    daily = sum(recent, ZERO) / Decimal(len(recent))
    baseline = sum(baseline_window, ZERO) / Decimal(len(baseline_window))
    std = Decimal(str(pstdev(float(value) for value in baseline_window))) if len(baseline_window) >= 2 else None
    growth: Decimal | None = None
    if len(values) >= 14:
        previous = values[-14:-7]
        previous_avg = sum(previous, ZERO) / Decimal(len(previous))
        if previous_avg > ZERO:
            growth = daily / previous_avg - ONE
    return {"daily_demand": daily, "baseline_demand": baseline, "std_daily_demand": std, "growth_ratio": growth}


def stockout_probability(stock: Decimal | None, daily_demand: Decimal | None, std_daily_demand: Decimal | None, exposure_days: int | None) -> Decimal | None:
    if stock is None or daily_demand is None or std_daily_demand is None or exposure_days is None:
        return None
    if exposure_days < 0:
        return None
    mean = float(daily_demand * exposure_days)
    deviation = float(std_daily_demand) * exposure_days**0.5
    if deviation == 0:
        return ONE if Decimal(str(mean)) > stock else ZERO
    probability = 1.0 - NormalDist(mu=mean, sigma=deviation).cdf(float(stock))
    return Decimal(str(min(1.0, max(0.0, probability))))


def expiry_loss_segments(lots: list[dict[str, Any]], daily_demand: Decimal, as_of: date, horizon_days: int = 180) -> Decimal | None:
    if any(as_decimal(lot.get("unit_cost")) is None for lot in lots):
        return None
    active = [
        {**lot, "remaining": as_decimal(lot.get("quantity")) or ZERO, "expiry_date": lot["expiry_date"]}
        for lot in lots
        if as_decimal(lot.get("quantity")) is not None and as_decimal(lot.get("quantity")) > ZERO
    ]
    active.sort(key=lambda lot: (lot["expiry_date"], str(lot.get("batch_number", ""))))
    total_loss = ZERO
    current = as_of
    end = as_of + timedelta(days=horizon_days)
    expiry_days = sorted({lot["expiry_date"] for lot in active if as_of < lot["expiry_date"] <= end})
    for expiry_day in expiry_days:
        days = (expiry_day - current).days
        consumption = daily_demand * days
        for lot in active:
            if lot["expiry_date"] < current or lot["remaining"] <= ZERO:
                continue
            used = min(lot["remaining"], consumption)
            lot["remaining"] -= used
            consumption -= used
            if consumption <= ZERO:
                break
        current = expiry_day
        for lot in active:
            if lot["expiry_date"] == expiry_day:
                total_loss += lot["remaining"] * as_decimal(lot["unit_cost"])
                lot["remaining"] = ZERO
    return total_loss


def supplier_metrics(session: Session, supplier_id: int, medicine_id: int) -> dict[str, Any]:
    transactions = list(session.scalars(select(SupplierTransaction).where(
        SupplierTransaction.supplier_id == supplier_id,
        SupplierTransaction.medicine_id == medicine_id,
    ).order_by(SupplierTransaction.order_date)))
    delivered = [row for row in transactions if row.actual_delivery_date is not None]
    on_time = [row for row in delivered if row.actual_delivery_date <= row.expected_delivery_date]
    lead_times = [(row.actual_delivery_date - row.order_date).days for row in delivered]
    quality_events = list(session.scalars(select(SupplierQualityEvent).where(
        SupplierQualityEvent.supplier_id == supplier_id,
        SupplierQualityEvent.medicine_id == medicine_id,
    )))
    received = sum((Decimal(row.quantity) for row in delivered), ZERO)
    rejected = sum((Decimal(row.rejected_quantity) for row in quality_events), ZERO)
    reliability = Decimal(len(on_time)) / Decimal(len(delivered)) if delivered else None
    quality = max(ZERO, ONE - rejected / received) if received > ZERO and quality_events else None
    return {
        "on_time_rate": reliability,
        "average_lead_days": Decimal(str(sum(lead_times) / len(lead_times))) if lead_times else None,
        "quality_acceptance": quality,
        "n_orders": len(transactions),
        "n_delivered": len(delivered),
        "n_quality_records": len(quality_events),
    }


def exact_batch_alerts(session: Session, normalized_medicine: str, batch_number: str) -> list[CDSCOAlert]:
    canonical_name = normalize_product(normalized_medicine)
    canonical_batch = normalize_batch(batch_number)
    return [
        alert for alert in session.scalars(select(CDSCOAlert))
        if normalize_product(alert.normalized_product_name) == canonical_name
        and normalize_batch(alert.batch_number) == canonical_batch
    ]