from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_session
from app.main import app
from app.models import CDSCOAlert, Decision, DecisionCandidate
from app.services.analysis.metrics import exact_batch_alerts, expiry_loss_segments, normalize_product, normalize_batch, supplier_metrics
from app.services.detection.pipeline import detect_candidates, run_pipeline
from app.services.simulation.service import run_simulations
from scripts.seed_synthetic_data import _create_seed


@pytest.fixture
def demo_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    current_day = datetime.now(UTC).date()
    seed = _create_seed(session, current_day)
    candidates = detect_candidates(session, current_day)
    mismatch = next(candidate for candidate in candidates if candidate.trigger == "STOCKOUT_RISK" and candidate.medicine_id == seed["medicines"][1].id)
    mismatch.evidence = [*mismatch.evidence, {"data_origin": "SYNTHETIC_CLIENT", "demo_fault_injection": {"enabled": True, "claim": "expiry_loss", "delta": 500}}]
    decisions = [run_pipeline(session, candidate, current_day) for candidate in candidates]
    session.commit()

    def override_session():
        request_session = factory()
        try:
            yield request_session
        finally:
            request_session.close()

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as client:
        yield session, client, seed, candidates, decisions
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def test_expiry_fefo_loss_uses_batch_order():
    today = date(2025, 1, 1)
    loss = expiry_loss_segments([
        {"batch_number": "LATE", "quantity": "10", "unit_cost": "2", "expiry_date": date(2025, 1, 5)},
        {"batch_number": "EARLY", "quantity": "10", "unit_cost": "3", "expiry_date": date(2025, 1, 3)},
    ], Decimal("2"), today, horizon_days=10)
    assert loss == Decimal("30")


def test_simulations_are_deterministic_and_compare_all_core_actions():
    today = datetime.now(UTC).date()
    snapshot = {
        "as_of": today,
        "daily_demand": "5",
        "std_daily_demand": "1",
        "usable_stock": "40",
        "lead_time_days": 3,
        "safety_stock_days": 2,
        "usable_batches": [
            {"batch_number": "EXP", "quantity": "30", "unit_cost": "2", "expiry_date": today + timedelta(days=2)},
            {"batch_number": "LONG", "quantity": "10", "unit_cost": "2", "expiry_date": today + timedelta(days=90)},
        ],
        "matched_alert_batches": [{"batch_number": "NSQ", "quantity": "3", "unit_cost": "4"}],
        "receiver_deficit": "20",
        "redistribution_cost_per_unit": "1.5",
        "stockout_penalty_per_unit": "3",
        "current_supplier_id": 1,
        "offers": [
            {"supplier_id": 1, "quoted_price": "5", "available_quantity": "100", "lead_time_days": 4, "supplier_metrics": {"on_time_rate": 0.95, "quality_acceptance": 0.99}},
            {"supplier_id": 2, "quoted_price": "4", "available_quantity": "80", "lead_time_days": 3, "supplier_metrics": {"on_time_rate": 0.98, "quality_acceptance": 0.995}},
        ],
    }
    first = run_simulations(snapshot)
    second = run_simulations(snapshot)
    expected = {"DO_NOTHING", "PRIORITIZE_FEFO", "REDISTRIBUTE", "REORDER", "CHANGE_SUPPLIER", "SPLIT_PROCUREMENT", "QUARANTINE_MATCHED_BATCH"}
    assert {row["action"] for row in first} == expected
    assert first == second
    assert next(row for row in first if row["action"] == "QUARANTINE_MATCHED_BATCH")["quarantine_quantity"] == 3
    assert next(row for row in first if row["action"] == "REDISTRIBUTE")["transfer_quantity"] == 15


def test_cdsco_match_requires_normalized_product_and_exact_batch(demo_db):
    session, _, seed, _, _ = demo_db
    medicine = seed["medicines"][0]
    assert normalize_product("Azithromycin Tablets IP 500 mg") == normalize_product(medicine.normalized_name)
    assert normalize_batch(" az- 9021 ") == "AZ-9021"
    assert len(exact_batch_alerts(session, medicine.normalized_name, "AZ-9021")) == 1
    assert exact_batch_alerts(session, medicine.normalized_name, "AZ-8801") == []
    assert exact_batch_alerts(session, "amoxicillin 500mg", "AZ-9021") == []


def test_supplier_metrics_keep_unknown_history_unknown(demo_db):
    session, _, seed, _, _ = demo_db
    amoxicillin = seed["medicines"][1]
    northstar = seed["suppliers"][2]
    metrics = supplier_metrics(session, northstar.id, amoxicillin.id)
    assert metrics["n_orders"] == 0
    assert metrics["on_time_rate"] is None
    assert metrics["quality_acceptance"] is None


def test_autonomous_pipeline_produces_verified_and_withheld_packages(demo_db):
    session, _, seed, candidates, decisions = demo_db
    azithromycin = seed["medicines"][0]
    expiry = next(candidate for candidate in candidates if candidate.trigger == "EXPIRY_RISK" and candidate.medicine_id == azithromycin.id)
    regulatory = next(candidate for candidate in candidates if candidate.trigger == "CDSCO_EXACT_BATCH" and candidate.medicine_id == azithromycin.id)
    amoxicillin = seed["medicines"][1]
    withheld = next(decision for decision in decisions if decision.candidate.medicine_id == amoxicillin.id)
    assert expiry.decision is not None and expiry.decision.verification_status == "VERIFIED"
    assert regulatory.decision is not None and regulatory.decision.verification_status == "VERIFIED"
    assert regulatory.decision.selected_action["action"] == "QUARANTINE_MATCHED_BATCH"
    assert regulatory.decision.selected_action["quantity"] == 3100
    assert withheld.verification_status == "WITHHELD"
    assert withheld.selected_action is None
    assert withheld.verification_details["match"] is False


def test_withheld_decision_cannot_be_approved(demo_db):
    _, client, seed, _, decisions = demo_db
    withheld = next(decision for decision in decisions if decision.verification_status == "WITHHELD")
    response = client.post(f"/api/decisions/{withheld.id}/approve", json={"comment": "test"})
    assert response.status_code == 409


def test_verified_decision_can_be_approved_and_audited(demo_db):
    _, client, _, _, decisions = demo_db
    verified = next(decision for decision in decisions if decision.verification_status == "VERIFIED")
    response = client.post(f"/api/decisions/{verified.id}/approve", json={"comment": "demo approval"})
    assert response.status_code == 200
    assert response.json()["approvalStatus"] == "APPROVED"
    assert "No purchase" in response.json()["message"]
    detail = client.get(f"/api/decisions/{verified.id}").json()
    assert detail["approvalStatus"] == "APPROVED"
    assert any(event["event"] == "APPROVED" for event in detail["audit"])
    approval_events = [event for event in detail["auditEvents"] if "approved" in event["event"].lower()]
    assert len(approval_events) == 1
    assert approval_events[0]["id"] is not None


def test_reject_decision_updates_review_state_and_audit_events(demo_db):
    _, client, _, _, decisions = demo_db
    verified = next(decision for decision in decisions if decision.verification_status == "VERIFIED")
    response = client.post(f"/api/decisions/{verified.id}/reject", json={"comment": "reviewed"})
    assert response.status_code == 200
    assert response.json()["approvalStatus"] == "REJECTED"
    detail = client.get(f"/api/decisions/{verified.id}").json()
    assert detail["approvalStatus"] == "REJECTED"
    rejection_events = [event for event in detail["auditEvents"] if "rejected" in event["event"].lower()]
    assert len(rejection_events) == 1
    assert rejection_events[0]["id"] is not None


def test_api_payloads_are_database_backed_and_scan_is_idempotent(demo_db):
    _, client, _, _, _ = demo_db
    assert client.get("/api/health").json()["database"] == "connected"
    overview = client.get("/api/overview")
    assert overview.status_code == 200
    assert overview.json()["decisions"]
    assert client.get("/api/inventory").json()["rows"]
    procurement = client.get("/api/procurement").json()
    assert procurement["suppliers"]
    assert procurement["requiredQuantity"] != 5200
    assert any("2.84" in supplier["price"] for supplier in procurement["suppliers"])
    assert client.get("/api/evidence").json()["alerts"]
    assert client.get("/api/system-status").json()["deterministicOnly"] is True
    scan = client.post("/api/analysis/run")
    assert scan.status_code == 200
    scan_result = scan.json()
    assert scan_result["decisionsProcessed"] > 0
    assert len(scan_result["decisions"]) == scan_result["decisionsProcessed"]
    refreshed_ids = {decision["id"] for decision in client.get("/api/decisions").json()}
    assert all(decision["id"] in refreshed_ids for decision in scan_result["decisions"])