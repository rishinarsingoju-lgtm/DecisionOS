from datetime import date
from decimal import Decimal
from typing import Any

from app.services.analysis.metrics import ZERO, as_decimal, expiry_loss_segments, stockout_probability


def _numeric(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _stock(snapshot: dict[str, Any]) -> Decimal | None:
    if snapshot.get("usable_stock") is None:
        return None
    return as_decimal(snapshot["usable_stock"])


def run_simulations(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    daily = as_decimal(snapshot.get("daily_demand"))
    std = as_decimal(snapshot.get("std_daily_demand"))
    usable_stock = _stock(snapshot)
    lead = snapshot.get("lead_time_days")
    as_of: date = snapshot["as_of"]
    lots = snapshot["usable_batches"]
    if daily is None or std is None or usable_stock is None or lead is None:
        return []

    baseline_loss = expiry_loss_segments(lots, daily, as_of)
    if baseline_loss is None:
        return []
    results: list[dict[str, Any]] = []
    safety_days = int(snapshot.get("safety_stock_days", 0))
    base_action = {"quantity": 0, "supplier_id": None, "lead_time_days": int(lead) + safety_days}
    action_names = ["DO_NOTHING", "PRIORITIZE_FEFO", "REDISTRIBUTE", "REORDER", "CHANGE_SUPPLIER", "SPLIT_PROCUREMENT"]
    if snapshot.get("matched_alert_batches"):
        action_names.append("QUARANTINE_MATCHED_BATCH")

    for action in action_names:
        params = dict(base_action)
        assumptions: list[str] = ["Demand estimate uses the recent 7-day mean; stockout probability uses a normal approximation."]
        action_lots = [dict(lot) for lot in lots]
        action_stock = usable_stock
        procurement_cost = ZERO
        redistribution_cost = ZERO
        order_quantity = 0
        transfer_quantity = 0
        chosen_supplier: int | None = None
        exposure = int(lead)
        quarantine_quantity = 0
        quality_risk_cost = ZERO

        if action == "QUARANTINE_MATCHED_BATCH":
            matched = snapshot.get("matched_alert_batches", [])
            quarantine_quantity = int(sum((as_decimal(lot.get("quantity")) or ZERO for lot in matched), ZERO))
            quality_risk_cost = sum((as_decimal(lot.get("quantity")) or ZERO) * (as_decimal(lot.get("unit_cost")) or ZERO) for lot in matched)
            params.update({"quantity": quarantine_quantity, "quarantine_quantity": quarantine_quantity})
            assumptions.append("Only inventory whose batch number and normalized product exactly match a regulatory alert is quarantined.")
        elif action == "PRIORITIZE_FEFO":
            assumptions.append("FEFO consumption is applied across batches by expiry date.")
        elif action == "REDISTRIBUTE":
            deficit = as_decimal(snapshot.get("receiver_deficit"))
            unit_transfer_cost = as_decimal(snapshot.get("redistribution_cost_per_unit"))
            expiring_quantity = sum((as_decimal(lot["quantity"]) or ZERO for lot in lots if (lot["expiry_date"] - as_of).days <= 90), ZERO)
            donor_reserve = daily * Decimal(int(lead) + int(snapshot.get("safety_stock_days", 0)))
            surplus = max(ZERO, usable_stock - donor_reserve)
            if deficit is None or unit_transfer_cost is None:
                assumptions.append("Redistribution skipped because receiver deficit or transfer cost is unknown.")
            else:
                transfer_quantity = int(min(deficit, expiring_quantity, surplus))
                remaining_transfer = Decimal(transfer_quantity)
                for lot in sorted(action_lots, key=lambda item: item["expiry_date"]):
                    moved = min(as_decimal(lot["quantity"]) or ZERO, remaining_transfer)
                    lot["quantity"] = str((as_decimal(lot["quantity"]) or ZERO) - moved)
                    remaining_transfer -= moved
                    if remaining_transfer <= ZERO:
                        break
                action_stock -= Decimal(transfer_quantity)
                redistribution_cost = Decimal(transfer_quantity) * unit_transfer_cost
                params.update({"quantity": transfer_quantity, "transfer_quantity": transfer_quantity})
                assumptions.append("Transfer quantity is capped by donor surplus, expiring units, and recorded receiver deficit.")
        elif action in {"REORDER", "CHANGE_SUPPLIER", "SPLIT_PROCUREMENT"}:
            offers = snapshot.get("offers", [])
            eligible = [offer for offer in offers if offer.get("available_quantity") is not None and offer.get("lead_time_days") is not None]
            eligible.sort(key=lambda offer: (int(offer["lead_time_days"]), as_decimal(offer["quoted_price"]) or Decimal("Infinity")))
            if action == "REORDER":
                supplier = next((offer for offer in eligible if offer.get("supplier_id") == snapshot.get("current_supplier_id")), None)
            elif action == "CHANGE_SUPPLIER":
                supplier = next((offer for offer in eligible if offer.get("supplier_metrics", {}).get("on_time_rate") is not None and offer.get("supplier_metrics", {}).get("quality_acceptance") is not None), None)
            else:
                supplier = eligible[0] if len(eligible) >= 2 else None
            if supplier is None:
                assumptions.append("Procurement action unavailable because a qualifying quote with known capacity/history is missing.")
                exposure = int(lead)
            else:
                target_days = max(14, int(lead) + int(snapshot.get("safety_stock_days", 0)))
                need = max(ZERO, daily * target_days - usable_stock)
                available = as_decimal(supplier.get("available_quantity"))
                order_quantity = int(min(need, available)) if available is not None else 0
                chosen_supplier = int(supplier["supplier_id"])
                exposure = int(supplier["lead_time_days"])
                price = as_decimal(supplier.get("quoted_price"))
                if price is None:
                    order_quantity = 0
                    assumptions.append("Quote price is unknown; procurement cost is not estimated.")
                else:
                    procurement_cost = Decimal(order_quantity) * price
                params.update({"quantity": order_quantity, "order_quantity": order_quantity, "supplier_id": chosen_supplier, "lead_time_days": exposure})
                assumptions.append("Procurement cost uses the supplier quote, not NPPA reference pricing.")
                if supplier.get("supplier_metrics", {}).get("on_time_rate") is None or supplier.get("supplier_metrics", {}).get("quality_acceptance") is None:
                    assumptions.append("Supplier history is UNKNOWN; this quote is not eligible as sole-source for a critical decision.")

        action_loss = expiry_loss_segments(action_lots, daily, as_of)
        if action_loss is None:
            continue
        risk = stockout_probability(action_stock, daily, std, exposure)
        expected_shortage = max(ZERO, daily * Decimal(exposure) - action_stock)
        penalty = as_decimal(snapshot.get("stockout_penalty_per_unit"))
        if penalty is None:
            total_cost = None
            assumptions.append("Total expected cost is unavailable because the stockout penalty policy is missing.")
        else:
            total_cost = action_loss + procurement_cost + redistribution_cost + expected_shortage * penalty + quality_risk_cost
        benefit = baseline_loss - action_loss - procurement_cost - redistribution_cost if total_cost is not None else None
        results.append({
            "action": action,
            "label": action.replace("_", " ").title(),
            "expiry_loss": _numeric(action_loss),
            "stockout_risk": _numeric(risk),
            "procurement_cost": _numeric(procurement_cost),
            "redistribution_cost": _numeric(redistribution_cost),
            "expected_stockout_units": _numeric(expected_shortage),
            "total_expected_cost": _numeric(total_cost),
            "expected_impact": {"net_benefit_vs_baseline": _numeric(benefit)},
            "quantity": params["quantity"],
            "transfer_quantity": transfer_quantity,
            "order_quantity": order_quantity,
            "quarantine_quantity": quarantine_quantity,
            "supplier_id": chosen_supplier,
            "lead_time_days": exposure,
            "assumptions": assumptions,
        })
    return results