from typing import Any


def select_action(simulations: list[dict[str, Any]], trigger: str) -> dict[str, Any] | None:
    if trigger == "CDSCO_EXACT_BATCH":
        quarantine = next((row for row in simulations if row["action"] == "QUARANTINE_MATCHED_BATCH"), None)
        if quarantine is not None:
            return quarantine
    feasible = [
        result for result in simulations
        if result["total_expected_cost"] is not None
        and result["stockout_risk"] is not None
        and result["stockout_risk"] <= 0.35
        and not any("UNKNOWN; this quote is not eligible" in note for note in result["assumptions"])
    ]
    return min(feasible, key=lambda result: (result["total_expected_cost"], result["action"])) if feasible else None