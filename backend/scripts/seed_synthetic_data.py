from __future__ import annotations

import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    CDSCOAlert,
    DemandHistory,
    DiseaseSignal,
    ExternalSourceStatus,
    InventoryBatch,
    InventoryPolicy,
    Location,
    Medicine,
    NPPAReferencePrice,
    SeasonalFactor,
    Supplier,
    SupplierOffer,
    SupplierQualityEvent,
    SupplierTransaction,
    WeatherObservation,
)
from app.services.detection.pipeline import detect_candidates, run_pipeline

DEMO_ORIGIN = "SYNTHETIC_CLIENT"


def main() -> None:
    if SessionLocal is None:
        raise SystemExit("Set DATABASE_URL in backend/.env before seeding PostgreSQL.")
    today = datetime.now(UTC).date()
    with SessionLocal() as session:
        if session.scalar(select(Medicine.id).limit(1)) is not None:
            print("Database already has medicine records; seed is idempotent and made no changes.")
            return
        data = _create_seed(session, today)
        session.flush()
        candidates = detect_candidates(session, today)
        amoxicillin_candidate = next((candidate for candidate in candidates if candidate.trigger == "STOCKOUT_RISK" and candidate.medicine_id == data["medicines"][1].id), None)
        if amoxicillin_candidate:
            amoxicillin_candidate.evidence = [
                *amoxicillin_candidate.evidence,
                {"data_origin": DEMO_ORIGIN, "demo_fault_injection": {"enabled": True, "claim": "expiry_loss", "delta": 500, "note": "Synthetic mismatch demonstration only"}},
            ]
        decisions = [run_pipeline(session, candidate, today) for candidate in candidates]
        session.commit()
        print(f"Seeded {len(data['medicines'])} medicines, {len(data['locations'])} locations, {len(candidates)} candidates and {len(decisions)} decisions.")
        print("All client business records are SYNTHETIC_CLIENT. The CDSCO-shaped alert is a planted synthetic demonstration record, not a real regulatory finding.")


def _create_seed(session, today: date) -> dict[str, object]:
    medicines = [
        Medicine(name="Azithromycin 500mg", normalized_name="azithromycin 500mg", disease_category="Respiratory", therapeutic_category="Antibiotic", data_origin=DEMO_ORIGIN),
        Medicine(name="Amoxicillin 500mg", normalized_name="amoxicillin 500mg", disease_category="Respiratory", therapeutic_category="Antibiotic", data_origin=DEMO_ORIGIN),
        Medicine(name="Cefixime 200mg", normalized_name="cefixime 200mg", disease_category="Respiratory", therapeutic_category="Antibiotic", data_origin=DEMO_ORIGIN),
        Medicine(name="Metformin 500mg", normalized_name="metformin 500mg", disease_category="Diabetes", therapeutic_category="Antidiabetic", data_origin=DEMO_ORIGIN),
        Medicine(name="ORS Sachet", normalized_name="ors sachet", disease_category="Gastrointestinal", therapeutic_category="Rehydration", data_origin=DEMO_ORIGIN),
        Medicine(name="Paracetamol 650mg", normalized_name="paracetamol 650mg", disease_category="Pain and fever", therapeutic_category="Analgesic", data_origin=DEMO_ORIGIN),
    ]
    locations = [
        Location(name="Hyderabad Central Depot", region="Telangana", latitude=Decimal("17.3850"), longitude=Decimal("78.4867"), data_origin=DEMO_ORIGIN),
        Location(name="Warangal Feeder", region="Telangana", latitude=Decimal("17.9689"), longitude=Decimal("79.5941"), data_origin=DEMO_ORIGIN),
        Location(name="Nizamabad Feeder", region="Telangana", latitude=Decimal("18.6725"), longitude=Decimal("78.0941"), data_origin=DEMO_ORIGIN),
        Location(name="Bengaluru Regional Hub", region="Karnataka", latitude=Decimal("12.9716"), longitude=Decimal("77.5946"), data_origin=DEMO_ORIGIN),
        Location(name="Vijayawada Distribution Centre", region="Andhra Pradesh", latitude=Decimal("16.5062"), longitude=Decimal("80.6480"), data_origin=DEMO_ORIGIN),
        Location(name="Chennai Central", region="Tamil Nadu", latitude=Decimal("13.0827"), longitude=Decimal("80.2707"), data_origin=DEMO_ORIGIN),
        Location(name="Guntur Depot", region="Andhra Pradesh", latitude=Decimal("16.3067"), longitude=Decimal("80.4365"), data_origin=DEMO_ORIGIN),
    ]
    suppliers = [
        Supplier(name="Asterion Pharma Ltd.", location="Pune", status="ACTIVE", data_origin=DEMO_ORIGIN),
        Supplier(name="Medline Therapeutics", location="Hyderabad", status="ACTIVE", data_origin=DEMO_ORIGIN),
        Supplier(name="Northstar Remedies", location="Ahmedabad", status="ACTIVE", data_origin=DEMO_ORIGIN),
    ]
    session.add_all([*medicines, *locations, *suppliers])
    session.flush()
    azithro, amoxicillin, cefixime, metformin, ors, paracetamol = medicines
    hyd, warangal, nizamabad, bengaluru, vijayawada, chennai, guntur = locations
    asterion, medline, northstar = suppliers

    batches = [
        InventoryBatch(medicine_id=azithro.id, location_id=hyd.id, batch_number="AZ-9021", quantity=Decimal("3100"), expiry_date=today + timedelta(days=30), unit_cost=Decimal("155.00"), supplier_id=asterion.id, data_origin=DEMO_ORIGIN),
        InventoryBatch(medicine_id=azithro.id, location_id=hyd.id, batch_number="AZ-9019", quantity=Decimal("3300"), expiry_date=today + timedelta(days=30), unit_cost=Decimal("155.00"), supplier_id=asterion.id, data_origin=DEMO_ORIGIN),
        InventoryBatch(medicine_id=azithro.id, location_id=hyd.id, batch_number="AZ-8801", quantity=Decimal("9300"), expiry_date=today + timedelta(days=240), unit_cost=Decimal("155.00"), supplier_id=asterion.id, data_origin=DEMO_ORIGIN),
        InventoryBatch(medicine_id=azithro.id, location_id=warangal.id, batch_number="AZ-7710", quantity=Decimal("300"), expiry_date=today + timedelta(days=210), unit_cost=Decimal("155.00"), supplier_id=asterion.id, data_origin=DEMO_ORIGIN),
        InventoryBatch(medicine_id=azithro.id, location_id=nizamabad.id, batch_number="AZ-7711", quantity=Decimal("250"), expiry_date=today + timedelta(days=220), unit_cost=Decimal("155.00"), supplier_id=asterion.id, data_origin=DEMO_ORIGIN),
        InventoryBatch(medicine_id=amoxicillin.id, location_id=bengaluru.id, batch_number="AMX-4482", quantity=Decimal("8600"), expiry_date=today + timedelta(days=71), unit_cost=Decimal("2.80"), supplier_id=medline.id, data_origin=DEMO_ORIGIN),
        InventoryBatch(medicine_id=amoxicillin.id, location_id=bengaluru.id, batch_number="AMX-4510", quantity=Decimal("620"), expiry_date=today + timedelta(days=150), unit_cost=Decimal("2.80"), supplier_id=medline.id, data_origin=DEMO_ORIGIN),
        InventoryBatch(medicine_id=cefixime.id, location_id=vijayawada.id, batch_number="CFX-1820", quantity=Decimal("5240"), expiry_date=today + timedelta(days=88), unit_cost=Decimal("8.50"), supplier_id=asterion.id, data_origin=DEMO_ORIGIN),
        InventoryBatch(medicine_id=cefixime.id, location_id=guntur.id, batch_number="CFX-1811", quantity=Decimal("4600"), expiry_date=today + timedelta(days=190), unit_cost=Decimal("8.50"), supplier_id=asterion.id, data_origin=DEMO_ORIGIN),
        InventoryBatch(medicine_id=metformin.id, location_id=chennai.id, batch_number="MET-7093", quantity=Decimal("21800"), expiry_date=today + timedelta(days=290), unit_cost=Decimal("4.10"), supplier_id=medline.id, data_origin=DEMO_ORIGIN),
        InventoryBatch(medicine_id=ors.id, location_id=warangal.id, batch_number="ORS-3116", quantity=Decimal("3980"), expiry_date=today + timedelta(days=82), unit_cost=Decimal("7.20"), supplier_id=asterion.id, data_origin=DEMO_ORIGIN),
        InventoryBatch(medicine_id=paracetamol.id, location_id=hyd.id, batch_number="PCM-8814", quantity=Decimal("18200"), expiry_date=today + timedelta(days=240), unit_cost=Decimal("3.30"), supplier_id=medline.id, data_origin=DEMO_ORIGIN),
    ]
    session.add_all(batches)

    location_by_medicine = {
        azithro.id: [(hyd, 75, 1.20), (warangal, 150, 1.0), (nizamabad, 125, 1.0)],
        amoxicillin.id: [(bengaluru, 1350, 1.0)],
        cefixime.id: [(vijayawada, 318, 1.0), (guntur, 100, 1.0)],
        metformin.id: [(chennai, 760, 1.0)],
        ors.id: [(warangal, 244, 1.0)],
        paracetamol.id: [(hyd, 920, 1.0)],
    }
    for medicine_id, positions in location_by_medicine.items():
        for location, mean, recent_factor in positions:
            _add_demand(session, medicine_id, location.id, today, mean, recent_factor)

    policies = [
        InventoryPolicy(medicine_id=azithro.id, location_id=hyd.id, safety_stock_days=3, max_cover_days=90, redistribution_cost_per_unit=Decimal("13.67"), stockout_penalty_per_unit=Decimal("230.00"), data_origin=DEMO_ORIGIN),
        InventoryPolicy(medicine_id=azithro.id, location_id=warangal.id, safety_stock_days=3, max_cover_days=90, redistribution_cost_per_unit=Decimal("13.67"), stockout_penalty_per_unit=Decimal("230.00"), data_origin=DEMO_ORIGIN),
        InventoryPolicy(medicine_id=azithro.id, location_id=nizamabad.id, safety_stock_days=3, max_cover_days=90, redistribution_cost_per_unit=Decimal("13.67"), stockout_penalty_per_unit=Decimal("230.00"), data_origin=DEMO_ORIGIN),
        InventoryPolicy(medicine_id=amoxicillin.id, location_id=bengaluru.id, safety_stock_days=3, max_cover_days=60, redistribution_cost_per_unit=Decimal("8.00"), stockout_penalty_per_unit=Decimal("12.00"), data_origin=DEMO_ORIGIN),
        InventoryPolicy(medicine_id=cefixime.id, location_id=vijayawada.id, safety_stock_days=3, max_cover_days=90, redistribution_cost_per_unit=Decimal("4.50"), stockout_penalty_per_unit=Decimal("35.00"), data_origin=DEMO_ORIGIN),
        InventoryPolicy(medicine_id=cefixime.id, location_id=guntur.id, safety_stock_days=3, max_cover_days=90, redistribution_cost_per_unit=Decimal("4.50"), stockout_penalty_per_unit=Decimal("35.00"), data_origin=DEMO_ORIGIN),
        InventoryPolicy(medicine_id=metformin.id, location_id=chennai.id, safety_stock_days=5, max_cover_days=120, redistribution_cost_per_unit=Decimal("2.00"), stockout_penalty_per_unit=Decimal("15.00"), data_origin=DEMO_ORIGIN),
        InventoryPolicy(medicine_id=ors.id, location_id=warangal.id, safety_stock_days=3, max_cover_days=90, redistribution_cost_per_unit=Decimal("2.50"), stockout_penalty_per_unit=Decimal("22.00"), data_origin=DEMO_ORIGIN),
        InventoryPolicy(medicine_id=paracetamol.id, location_id=hyd.id, safety_stock_days=4, max_cover_days=100, redistribution_cost_per_unit=Decimal("1.20"), stockout_penalty_per_unit=Decimal("10.00"), data_origin=DEMO_ORIGIN),
    ]
    session.add_all(policies)

    for disease, region, concentration in [
        ("Respiratory infection", "Telangana", Decimal("1.20")),
        ("Respiratory infection", "Karnataka", Decimal("1.16")),
        ("Respiratory infection", "Andhra Pradesh", Decimal("1.08")),
        ("Diabetes", "Tamil Nadu", Decimal("1.00")),
    ]:
        session.add(DiseaseSignal(region=region, disease=disease, concentration=concentration, period_date=today, source="SYNTHETIC_CLIENT_DEMO_SIGNAL", data_origin=DEMO_ORIGIN))
    for disease, region, multiplier in [
        ("Respiratory", "Telangana", Decimal("1.12")),
        ("Respiratory", "Karnataka", Decimal("1.08")),
        ("Respiratory", "Andhra Pradesh", Decimal("1.05")),
    ]:
        session.add(SeasonalFactor(disease_category=disease, region=region, month=today.month, multiplier=multiplier, source="SYNTHETIC_CONFIGURED_ASSUMPTION", data_origin=DEMO_ORIGIN))

    session.add(CDSCOAlert(
        product_name="Azithromycin Tablets IP 500 mg",
        normalized_product_name="azithromycin 500mg",
        batch_number="AZ-9021",
        manufactured_by="Synthetic demonstration manufacturer",
        manufacturing_date=today - timedelta(days=300),
        expiry_date=today + timedelta(days=30),
        nsq_result="PLANTED DEMO ALERT — NOT A REAL CDSCO FINDING",
        reporting_source="SYNTHETIC DEMO RECORD; NOT CDSCO",
        reporting_lab_state="Synthetic fixture",
        reporting_month=today.strftime("%Y-%m"),
        source_url=None,
        ingested_at=datetime.now(UTC),
        data_origin="SYNTHETIC_PLANTED_CDSCO_EXAMPLE",
    ))

    session.add_all([
        SupplierOffer(supplier_id=asterion.id, medicine_id=amoxicillin.id, quoted_price=Decimal("2.84"), available_quantity=Decimal("6000"), lead_time_days=7, regulatory_notes="Synthetic demo quote", data_origin=DEMO_ORIGIN),
        SupplierOffer(supplier_id=medline.id, medicine_id=amoxicillin.id, quoted_price=Decimal("2.96"), available_quantity=Decimal("4500"), lead_time_days=5, regulatory_notes="Synthetic demo quote", data_origin=DEMO_ORIGIN),
        SupplierOffer(supplier_id=northstar.id, medicine_id=amoxicillin.id, quoted_price=Decimal("2.71"), available_quantity=Decimal("2000"), lead_time_days=11, regulatory_notes="Synthetic indicative offer; no client history", data_origin=DEMO_ORIGIN),
        SupplierOffer(supplier_id=asterion.id, medicine_id=azithro.id, quoted_price=Decimal("155.00"), available_quantity=Decimal("5000"), lead_time_days=9, data_origin=DEMO_ORIGIN),
        SupplierOffer(supplier_id=medline.id, medicine_id=azithro.id, quoted_price=Decimal("162.00"), available_quantity=Decimal("4000"), lead_time_days=6, data_origin=DEMO_ORIGIN),
        SupplierOffer(supplier_id=asterion.id, medicine_id=cefixime.id, quoted_price=Decimal("8.50"), available_quantity=Decimal("3000"), lead_time_days=7, data_origin=DEMO_ORIGIN),
        SupplierOffer(supplier_id=medline.id, medicine_id=cefixime.id, quoted_price=Decimal("8.90"), available_quantity=Decimal("2200"), lead_time_days=5, data_origin=DEMO_ORIGIN),
    ])
    _supplier_history(session, asterion, amoxicillin, today, [(6, 7, 60), (7, 7, 50), (8, 9, 100)])
    _supplier_history(session, medline, amoxicillin, today, [(4, 5, 0), (5, 5, 0), (5, 5, 0), (6, 5, 0), (7, 6, 0)])
    _supplier_history(session, asterion, azithro, today, [(7, 8, 15), (9, 8, 0), (8, 9, 0)])
    _supplier_history(session, medline, azithro, today, [(7, 6, 0), (8, 6, 0), (10, 7, 0)])
    session.add(SupplierQualityEvent(supplier_id=asterion.id, medicine_id=amoxicillin.id, batch_number="AMX-HIST-3", issue="Synthetic packaging deviation record", rejected_quantity=Decimal("15"), event_date=today - timedelta(days=10), source="SYNTHETIC_CLIENT_DEMO", data_origin=DEMO_ORIGIN))
    session.add(SupplierQualityEvent(supplier_id=asterion.id, medicine_id=azithro.id, batch_number="AZ-HIST-1", issue="Synthetic label rework record", rejected_quantity=Decimal("15"), event_date=today - timedelta(days=45), source="SYNTHETIC_CLIENT_DEMO", data_origin=DEMO_ORIGIN))
    session.add(NPPAReferencePrice(medicine_id=amoxicillin.id, reference_price=Decimal("2.90"), effective_date=today - timedelta(days=15), source_url=None, ingested_at=datetime.now(UTC), data_origin="SYNTHETIC_NPPA_REFERENCE_EXAMPLE"))

    session.add_all([
        ExternalSourceStatus(source="WHO ICD", status="Unavailable", detail="No WHO credentials or live sync configured; disease category values in this demo are synthetic.", record_count=None),
        ExternalSourceStatus(source="Open-Meteo", status="Unavailable", detail="No weather observation seeded; weather factor omitted from calculations.", record_count=0),
        ExternalSourceStatus(source="CDSCO", status="Available", detail="One planted synthetic batch-match fixture; not an official CDSCO snapshot.", fetched_at=datetime.now(UTC), record_count=1),
        ExternalSourceStatus(source="NPPA", status="Unavailable", detail="Reference price example is synthetic; no official NPPA snapshot is connected.", record_count=None),
    ])
    return {"medicines": medicines, "locations": locations, "suppliers": suppliers}


def _add_demand(session, medicine_id: int, location_id: int, today: date, mean: int, recent_factor: float) -> None:
    for offset in range(42, 0, -1):
        day = today - timedelta(days=offset)
        if offset <= 7:
            value = Decimal(str(round(mean * recent_factor * (1 + ((offset % 3) - 1) * 0.02))))
        else:
            value = Decimal(str(round(mean * (1 + ((offset % 5) - 2) * 0.015))))
        session.add(DemandHistory(medicine_id=medicine_id, location_id=location_id, period_date=day, demand=value, data_origin=DEMO_ORIGIN))


def _supplier_history(session, supplier: Supplier, medicine: Medicine, today: date, rows: list[tuple[int, int, int]]) -> None:
    for index, (lead_days, expected_days, rejected_quantity) in enumerate(rows):
        order_date = today - timedelta(days=100 - index * 17)
        expected = order_date + timedelta(days=expected_days)
        actual = order_date + timedelta(days=lead_days)
        quantity = Decimal("1000")
        session.add(SupplierTransaction(
            supplier_id=supplier.id,
            medicine_id=medicine.id,
            quantity=quantity,
            purchase_price=Decimal("2.80") if medicine.normalized_name.startswith("amoxicillin") else Decimal("155.00"),
            order_date=order_date,
            expected_delivery_date=expected,
            actual_delivery_date=actual,
            data_origin=DEMO_ORIGIN,
        ))
        if rejected_quantity:
            session.add(SupplierQualityEvent(
                supplier_id=supplier.id,
                medicine_id=medicine.id,
                batch_number=f"{medicine.normalized_name[:3].upper()}-HIST-{index + 1}",
                issue="Synthetic historical rejection quantity",
                rejected_quantity=Decimal(rejected_quantity),
                event_date=actual,
                source="SYNTHETIC_CLIENT_DEMO",
                data_origin=DEMO_ORIGIN,
            ))


if __name__ == "__main__":
    main()