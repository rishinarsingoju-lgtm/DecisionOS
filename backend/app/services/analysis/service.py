from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    CDSCOAlert,
    DemandHistory,
    DiseaseSignal,
    InventoryBatch,
    InventoryPolicy,
    Location,
    SeasonalFactor,
    SupplierOffer,
    WeatherObservation,
)
from app.services.analysis.metrics import ZERO, demand_profile, exact_batch_alerts


def build_analysis(session: Session, candidate: Any, today: date) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    medicine = candidate.medicine
    location = candidate.location
    batches = list(session.scalars(select(InventoryBatch).where(
        InventoryBatch.medicine_id == medicine.id,
        InventoryBatch.location_id == location.id,
    ).order_by(InventoryBatch.expiry_date)))
    demand_rows = list(session.scalars(select(DemandHistory).where(
        DemandHistory.medicine_id == medicine.id,
        DemandHistory.location_id == location.id,
    ).order_by(DemandHistory.period_date)))
    profile = demand_profile(demand_rows)
    raw_daily = profile["daily_demand"]
    signals_missing: list[str] = []
    if raw_daily is None:
        signals_missing.append("historical demand")
    if profile["std_daily_demand"] is None:
        signals_missing.append("demand variability")

    disease_signal = session.scalar(select(DiseaseSignal).where(
        DiseaseSignal.region == location.region,
        DiseaseSignal.disease.ilike(f"%{medicine.disease_category or ''}%"),
    ).order_by(DiseaseSignal.period_date.desc())) if medicine.disease_category else None
    season = session.scalar(select(SeasonalFactor).where(
        SeasonalFactor.disease_category == medicine.disease_category,
        SeasonalFactor.month == today.month,
        (SeasonalFactor.region == location.region) | (SeasonalFactor.region.is_(None)),
    ).order_by(SeasonalFactor.region.is_(None))) if medicine.disease_category else None
    seasonal_multiplier = Decimal(season.multiplier) if season else None
    disease_multiplier = Decimal(disease_signal.concentration) if disease_signal and disease_signal.concentration is not None else None
    forecast = raw_daily
    if forecast is not None and disease_multiplier is not None:
        forecast *= min(Decimal("1.5"), max(Decimal("0.75"), disease_multiplier))
    elif medicine.disease_category:
        signals_missing.append("disease concentration")
    if forecast is not None and seasonal_multiplier is not None:
        forecast *= min(Decimal("1.5"), max(Decimal("0.75"), seasonal_multiplier))
    elif medicine.disease_category:
        signals_missing.append("seasonality")

    weather = session.scalar(select(WeatherObservation).where(
        WeatherObservation.location_id == location.id,
    ).order_by(WeatherObservation.fetched_at.desc()))
    weather_recent = bool(weather and weather.fetched_at and weather.fetched_at >= datetime.now(weather.fetched_at.tzinfo) - timedelta(hours=3))
    weather_relevant = (medicine.disease_category or "").lower() == "respiratory"
    weather_value = weather.precipitation_mm if weather and weather_recent and weather_relevant else None
    if weather_relevant and weather_value is None:
        signals_missing.append("weather (no fresh relevant observation)")

    alert_matches: dict[int, list[CDSCOAlert]] = {
        batch.id: exact_batch_alerts(session, medicine.normalized_name, batch.batch_number)
        for batch in batches
    }
    usable_batches = [batch for batch in batches if not alert_matches[batch.id]]
    all_stock = sum((Decimal(batch.quantity) for batch in batches), ZERO)
    usable_stock = sum((Decimal(batch.quantity) for batch in usable_batches), ZERO)
    usable_lots = [{
        "batch_id": batch.id,
        "batch_number": batch.batch_number,
        "quantity": str(batch.quantity),
        "unit_cost": str(batch.unit_cost),
        "expiry_date": batch.expiry_date,
    } for batch in usable_batches]
    matched_alert_batches = [{
        "batch_id": batch.id,
        "batch_number": batch.batch_number,
        "quantity": str(batch.quantity),
        "unit_cost": str(batch.unit_cost),
    } for batch in batches if alert_matches[batch.id]]
    days_cover = usable_stock / forecast if forecast is not None and forecast > ZERO else None

    offers = list(session.scalars(select(SupplierOffer).where(SupplierOffer.medicine_id == medicine.id)))
    offer_views = []
    lead_times = [offer.lead_time_days for offer in offers if offer.lead_time_days is not None]
    for offer in offers:
        supplier = offer.supplier
        transactions = list(supplier.transactions)
        delivered = [tx for tx in transactions if tx.medicine_id == medicine.id and tx.actual_delivery_date]
        ontime = [tx for tx in delivered if tx.actual_delivery_date <= tx.expected_delivery_date]
        quality_rows = [event for event in supplier.quality_events if event.medicine_id == medicine.id]
        received_qty = sum((Decimal(tx.quantity) for tx in delivered), ZERO)
        rejected_qty = sum((Decimal(event.rejected_quantity) for event in quality_rows), ZERO)
        metrics = {
            "on_time_rate": float(Decimal(len(ontime)) / Decimal(len(delivered))) if delivered else None,
            "quality_acceptance": float(max(ZERO, Decimal("1") - rejected_qty / received_qty)) if received_qty > ZERO and quality_rows else None,
            "n_orders": len([tx for tx in transactions if tx.medicine_id == medicine.id]),
            "n_quality_records": len(quality_rows),
        }
        offer_views.append({
            "supplier_id": supplier.id,
            "supplier_name": supplier.name,
            "quoted_price": str(offer.quoted_price),
            "available_quantity": str(offer.available_quantity) if offer.available_quantity is not None else None,
            "lead_time_days": offer.lead_time_days,
            "supplier_metrics": metrics,
        })
    lead_time = min(lead_times) if lead_times else None
    if lead_time is None:
        signals_missing.append("supplier lead time")

    policy = session.scalar(select(InventoryPolicy).where(
        InventoryPolicy.medicine_id == medicine.id,
        InventoryPolicy.location_id == location.id,
    ))
    receiver_deficit = ZERO
    if forecast is not None and lead_time is not None:
        other_locations = list(session.scalars(select(Location).where(Location.id != location.id)))
        for other in other_locations:
            other_batches = list(session.scalars(select(InventoryBatch).where(
                InventoryBatch.medicine_id == medicine.id,
                InventoryBatch.location_id == other.id,
            )))
            other_demand = list(session.scalars(select(DemandHistory).where(
                DemandHistory.medicine_id == medicine.id,
                DemandHistory.location_id == other.id,
            ).order_by(DemandHistory.period_date)))
            other_profile = demand_profile(other_demand)
            other_rate = other_profile["daily_demand"]
            if other_rate is None:
                continue
            other_stock = sum((Decimal(batch.quantity) for batch in other_batches), ZERO)
            receiver_deficit += max(ZERO, other_rate * Decimal(lead_time) - other_stock)

    inventory_evidence = [{
        "type": "inventory_batch",
        "source_ref": f"inventory_batches#{batch.id}",
        "data_origin": batch.data_origin,
        "freshness": "database snapshot",
        "summary": f"{batch.batch_number}: {batch.quantity} units; expires {batch.expiry_date.isoformat()}",
        "matched_alert": bool(alert_matches[batch.id]),
    } for batch in batches]
    evidence = inventory_evidence
    if demand_rows:
        evidence.append({
            "type": "demand_history",
            "source_ref": f"demand_history#{demand_rows[0].id}..{demand_rows[-1].id}",
            "data_origin": demand_rows[-1].data_origin,
            "freshness": demand_rows[-1].period_date.isoformat(),
            "summary": f"{len(demand_rows)} daily demand records used",
        })
    if disease_signal:
        evidence.append({"type": "disease_signal", "source_ref": f"disease_signals#{disease_signal.id}", "data_origin": disease_signal.data_origin, "freshness": disease_signal.period_date.isoformat(), "summary": f"{disease_signal.disease}: concentration {disease_signal.concentration}"})
    if season:
        evidence.append({"type": "seasonality", "source_ref": f"seasonal_factors#{season.id}", "data_origin": season.data_origin, "freshness": "configured factor", "summary": f"Multiplier {season.multiplier} for month {season.month}"})
    for batch_id, alerts in alert_matches.items():
        for alert in alerts:
            evidence.append({"type": "cdsco_batch_match", "source_ref": f"cdsco_alerts#{alert.id}", "data_origin": alert.data_origin, "freshness": alert.ingested_at.isoformat(), "summary": f"Exact batch {alert.batch_number}: {alert.nsq_result}", "source_url": alert.source_url})

    analysis = {
        "what_was_detected": candidate.trigger.replace("_", " ").title(),
        "why_it_matters": _why(candidate.trigger, medicine.name, location.name),
        "signals": {
            "current_inventory": float(all_stock),
            "usable_inventory": float(usable_stock),
            "historical_daily_demand": float(raw_daily) if raw_daily is not None else None,
            "estimated_daily_demand": float(forecast) if forecast is not None else None,
            "demand_std_daily": float(profile["std_daily_demand"]) if profile["std_daily_demand"] is not None else None,
            "demand_growth": float(profile["growth_ratio"]) if profile["growth_ratio"] is not None else None,
            "days_of_cover": float(days_cover) if days_cover is not None else None,
            "disease_concentration": float(disease_signal.concentration) if disease_signal and disease_signal.concentration is not None else None,
            "seasonality_multiplier": float(seasonal_multiplier) if seasonal_multiplier is not None else None,
            "weather_precipitation_mm": float(weather_value) if weather_value is not None else None,
            "supplier_lead_time_days": lead_time,
            "expiry_loss_estimate": None,
        },
        "signals_missing": sorted(set(signals_missing)),
        "assumptions": [
            "Recent 7-day mean is the demand estimate; historical data is synthetic demo data.",
            "Disease and seasonal multipliers are bounded between 0.75× and 1.50× and are explicitly labeled assumptions.",
            "Weather is applied only to respiratory-category medicines and only when a fresh observation exists; no weather-to-demand coefficient is assumed.",
        ],
        "constraints": {
            "safety_stock_days": policy.safety_stock_days if policy else None,
            "redistribution_cost_per_unit": float(policy.redistribution_cost_per_unit) if policy and policy.redistribution_cost_per_unit is not None else None,
            "stockout_penalty_per_unit": float(policy.stockout_penalty_per_unit) if policy and policy.stockout_penalty_per_unit is not None else None,
            "unknown_inputs_are_not_zero": True,
        },
        "data_origin": "SYNTHETIC_CLIENT",
    }
    snapshot = {
        "as_of": today,
        "daily_demand": str(forecast) if forecast is not None else None,
        "baseline_demand": str(raw_daily) if raw_daily is not None else None,
        "std_daily_demand": str(profile["std_daily_demand"]) if profile["std_daily_demand"] is not None else None,
        "growth_ratio": str(profile["growth_ratio"]) if profile["growth_ratio"] is not None else None,
        "usable_stock": str(usable_stock),
        "all_stock": str(all_stock),
        "usable_batches": usable_lots,
        "matched_alert_batches": matched_alert_batches,
        "lead_time_days": lead_time,
        "safety_stock_days": policy.safety_stock_days if policy else 0,
        "redistribution_cost_per_unit": str(policy.redistribution_cost_per_unit) if policy and policy.redistribution_cost_per_unit is not None else None,
        "stockout_penalty_per_unit": str(policy.stockout_penalty_per_unit) if policy and policy.stockout_penalty_per_unit is not None else None,
        "receiver_deficit": str(receiver_deficit),
        "current_supplier_id": batches[0].supplier_id if batches else None,
        "offers": offer_views,
    }
    return analysis, evidence, snapshot


def _why(trigger: str, medicine: str, location: str) -> str:
    explanations = {
        "EXPIRY_RISK": f"Usable {medicine} stock at {location} is projected to exceed local consumption before one or more batches expire.",
        "STOCKOUT_RISK": f"Current {medicine} coverage at {location} is below supplier lead time and the configured safety buffer.",
        "CDSCO_EXACT_BATCH": f"A batch-level regulatory alert exactly matches {medicine} inventory at {location}; unrelated batches are not included.",
        "EXCESS_INVENTORY": f"Projected {medicine} coverage at {location} exceeds the configured excess-stock horizon.",
        "DEMAND_SURGE": f"Recent recorded {medicine} demand at {location} is materially above its preceding period.",
        "SUPPLIER_RELIABILITY": f"Observed delivery performance for a supplier serving {medicine} has deteriorated; sample size is shown.",
        "PROCUREMENT_OPPORTUNITY": f"Current supplier offers for {medicine} differ in price and available capacity; trade-offs require review.",
        "INVENTORY_IMBALANCE": f"{medicine} coverage differs across locations; transfer feasibility must be simulated before action.",
    }
    return explanations.get(trigger, f"A deterministic rule detected a supply-chain condition for {medicine} at {location}.")