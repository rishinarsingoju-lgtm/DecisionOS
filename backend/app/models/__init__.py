from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class Medicine(Base):
    __tablename__ = "medicines"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    normalized_name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    disease_category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    therapeutic_category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    data_origin: Mapped[str] = mapped_column(String(40), default="SYNTHETIC_CLIENT")

    batches: Mapped[list["InventoryBatch"]] = relationship(back_populates="medicine")
    demand_history: Mapped[list["DemandHistory"]] = relationship(back_populates="medicine")


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    region: Mapped[str] = mapped_column(String(120))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    data_origin: Mapped[str] = mapped_column(String(40), default="SYNTHETIC_CLIENT")

    batches: Mapped[list["InventoryBatch"]] = relationship(back_populates="location")
    demand_history: Mapped[list["DemandHistory"]] = relationship(back_populates="location")


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="ACTIVE")
    data_origin: Mapped[str] = mapped_column(String(40), default="SYNTHETIC_CLIENT")

    transactions: Mapped[list["SupplierTransaction"]] = relationship(back_populates="supplier")
    quality_events: Mapped[list["SupplierQualityEvent"]] = relationship(back_populates="supplier")
    offers: Mapped[list["SupplierOffer"]] = relationship(back_populates="supplier")


class InventoryBatch(Base):
    __tablename__ = "inventory_batches"
    __table_args__ = (
        UniqueConstraint("medicine_id", "location_id", "batch_number", name="uq_batch_medicine_location"),
        Index("ix_inventory_location_expiry", "location_id", "expiry_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.id"))
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    batch_number: Mapped[str] = mapped_column(String(80))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    expiry_date: Mapped[date] = mapped_column(Date)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    data_origin: Mapped[str] = mapped_column(String(40), default="SYNTHETIC_CLIENT")

    medicine: Mapped[Medicine] = relationship(back_populates="batches")
    location: Mapped[Location] = relationship(back_populates="batches")
    supplier: Mapped[Supplier | None] = relationship()


class DemandHistory(Base):
    __tablename__ = "demand_history"
    __table_args__ = (Index("ix_demand_medicine_location_date", "medicine_id", "location_id", "period_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.id"))
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    period_date: Mapped[date] = mapped_column(Date)
    demand: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    data_origin: Mapped[str] = mapped_column(String(40), default="SYNTHETIC_CLIENT")

    medicine: Mapped[Medicine] = relationship(back_populates="demand_history")
    location: Mapped[Location] = relationship(back_populates="demand_history")


class DiseaseSignal(Base):
    __tablename__ = "disease_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    region: Mapped[str] = mapped_column(String(120), index=True)
    disease: Mapped[str] = mapped_column(String(160))
    concentration: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    period_date: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(100))
    data_origin: Mapped[str] = mapped_column(String(40), default="SYNTHETIC_CLIENT")


class SeasonalFactor(Base):
    __tablename__ = "seasonal_factors"
    __table_args__ = (UniqueConstraint("disease_category", "region", "month", name="uq_seasonal_factor_scope"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    disease_category: Mapped[str] = mapped_column(String(120))
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    month: Mapped[int] = mapped_column(Integer)
    multiplier: Mapped[Decimal] = mapped_column(Numeric(6, 3))
    source: Mapped[str] = mapped_column(String(100))
    data_origin: Mapped[str] = mapped_column(String(40), default="SYNTHETIC_CLIENT")


class SupplierTransaction(Base):
    __tablename__ = "supplier_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    order_date: Mapped[date] = mapped_column(Date)
    expected_delivery_date: Mapped[date] = mapped_column(Date)
    actual_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_origin: Mapped[str] = mapped_column(String(40), default="SYNTHETIC_CLIENT")

    supplier: Mapped[Supplier] = relationship(back_populates="transactions")
    medicine: Mapped[Medicine] = relationship()


class SupplierQualityEvent(Base):
    __tablename__ = "supplier_quality_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.id"))
    batch_number: Mapped[str] = mapped_column(String(80))
    issue: Mapped[str] = mapped_column(Text)
    rejected_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    event_date: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(100))
    data_origin: Mapped[str] = mapped_column(String(40), default="SYNTHETIC_CLIENT")

    supplier: Mapped[Supplier] = relationship(back_populates="quality_events")
    medicine: Mapped[Medicine] = relationship()


class SupplierOffer(Base):
    __tablename__ = "supplier_offers"
    __table_args__ = (UniqueConstraint("supplier_id", "medicine_id", name="uq_supplier_offer_medicine"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.id"))
    quoted_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    available_quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quoted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    regulatory_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_origin: Mapped[str] = mapped_column(String(40), default="SYNTHETIC_CLIENT")

    supplier: Mapped[Supplier] = relationship(back_populates="offers")
    medicine: Mapped[Medicine] = relationship()


class InventoryPolicy(Base):
    __tablename__ = "inventory_policies"
    __table_args__ = (UniqueConstraint("medicine_id", "location_id", name="uq_policy_medicine_location"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.id"))
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    safety_stock_days: Mapped[int] = mapped_column(Integer, default=3)
    max_cover_days: Mapped[int] = mapped_column(Integer, default=90)
    redistribution_cost_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    stockout_penalty_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    data_origin: Mapped[str] = mapped_column(String(40), default="SYNTHETIC_CLIENT")


class CDSCOAlert(Base):
    __tablename__ = "cdsco_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(String(200))
    normalized_product_name: Mapped[str] = mapped_column(String(200), index=True)
    batch_number: Mapped[str] = mapped_column(String(80), index=True)
    manufactured_by: Mapped[str | None] = mapped_column(String(180), nullable=True)
    manufacturing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    nsq_result: Mapped[str] = mapped_column(Text)
    reporting_source: Mapped[str] = mapped_column(String(160))
    reporting_lab_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reporting_month: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    data_origin: Mapped[str] = mapped_column(String(40), default="EXTERNAL_CDSCO")


class WeatherObservation(Base):
    __tablename__ = "weather_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    observed_on: Mapped[date] = mapped_column(Date)
    precipitation_mm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    source: Mapped[str] = mapped_column(String(80), default="Open-Meteo")
    data_origin: Mapped[str] = mapped_column(String(40), default="EXTERNAL_OPEN_METEO")


class NPPAReferencePrice(Base):
    __tablename__ = "nppa_reference_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.id"))
    reference_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    effective_date: Mapped[date] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    data_origin: Mapped[str] = mapped_column(String(40), default="EXTERNAL_NPPA")


class ExternalSourceStatus(Base):
    __tablename__ = "external_source_status"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(80), unique=True)
    status: Mapped[str] = mapped_column(String(30))
    detail: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    record_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class DecisionCandidate(Base):
    __tablename__ = "decision_candidates"
    __table_args__ = (Index("ix_candidate_state_priority", "status", "priority"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    trigger: Mapped[str] = mapped_column(String(80), index=True)
    priority: Mapped[str] = mapped_column(String(20))
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.id"))
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    status: Mapped[str] = mapped_column(String(30), default="DETECTED")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    evidence: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)

    medicine: Mapped[Medicine] = relationship()
    location: Mapped[Location] = relationship()
    decision: Mapped["Decision | None"] = relationship(back_populates="candidate", uselist=False)


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("decision_candidates.id"), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    approval_status: Mapped[str] = mapped_column(String(30), default="PENDING")
    selected_action: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    analysis: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    simulation_results: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    expected_impact: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    verification_status: Mapped[str] = mapped_column(String(30), default="PENDING")
    verification_details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    evidence: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    audit: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    candidate: Mapped[DecisionCandidate] = relationship(back_populates="decision")
    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="decision", order_by="AuditEvent.created_at")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id"), index=True)
    stage: Mapped[str] = mapped_column(String(40))
    event_type: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    actor: Mapped[str] = mapped_column(String(120), default="SYSTEM")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    decision: Mapped[Decision] = relationship(back_populates="audit_events")