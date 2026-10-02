from sqlalchemy.orm import Session

from app.models import CDSCOAlert
from app.services.analysis.metrics import exact_batch_alerts


def match_inventory_batch(session: Session, normalized_medicine: str, batch_number: str) -> list[CDSCOAlert]:
    """Only return deterministic normalized-product plus exact-batch matches."""
    return exact_batch_alerts(session, normalized_medicine, batch_number)