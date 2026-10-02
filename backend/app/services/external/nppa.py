from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NPPAReferencePrice


def latest_reference_price(session: Session, medicine_id: int, as_of: date | None = None) -> NPPAReferencePrice | None:
    query = select(NPPAReferencePrice).where(NPPAReferencePrice.medicine_id == medicine_id)
    if as_of is not None:
        query = query.where(NPPAReferencePrice.effective_date <= as_of)
    return session.scalar(query.order_by(NPPAReferencePrice.effective_date.desc()))