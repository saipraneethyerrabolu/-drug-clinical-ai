import pytest
from fastapi.testclient import TestClient

from app.api.ddi import get_ddi_service
from app.main import app
from app.services.ddi_service import DDIService


KNOWN_MODERATE_A = "A Bec 300mg Tablet 30'S"
KNOWN_MODERATE_B = "ADDTREX 50 Tablet 10's"


@pytest.fixture(scope="module")
def service():
    # Build the 160k-row DDI index once for this test module.
    return DDIService()


def test_known_ddi_service_pair_is_found(service):
    result = service.check([KNOWN_MODERATE_A, KNOWN_MODERATE_B])

    assert result["pairs_checked"] == 1
    assert result["known_interaction_count"] == 1
    assert result["highest_severity"] == "Moderate"

    interaction = result["interactions"][0]
    assert interaction["status"] == "KNOWN_INTERACTION"
    assert interaction["severity"] == "Moderate"
    assert interaction["ddi_id"] == "DDI0000001"
    assert {interaction["drug_a"], interaction["drug_b"]} == {"Abacavir", "Naltrexone"}


def test_known_interaction_does_not_use_model(service):
    result = service.check([KNOWN_MODERATE_A, KNOWN_MODERATE_B])
    assert result["interactions"][0]["model_status"] == "NOT_USED_KNOWN_INTERACTION"


def test_unknown_medicine_is_reported_safely(service):
    result = service.check([KNOWN_MODERATE_A, "Definitely Not A Real Medicine XYZ123"])
    assert result["unresolved_medicines"]
    assert result["unresolved_medicines"][0]["mapping_status"] == "PRODUCT_NOT_FOUND"
    assert result["pairs_checked"] == 0


def test_ddi_api_endpoint(service):
    # Reuse the already-built service through FastAPI dependency's cached getter.
    get_ddi_service.cache_clear()
    get_ddi_service.cache_parameters()
    # Prime the cache by temporarily overriding the function at route dependency level
    # is unnecessary here because the route calls the getter directly. Calling it once
    # still creates a separate service, so API coverage is kept to one request.
    client = TestClient(app)
    response = client.post(
        "/api/ddi/check",
        json={"medicines": [KNOWN_MODERATE_A, KNOWN_MODERATE_B]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["known_interaction_count"] == 1
    assert payload["interactions"][0]["severity"] == "Moderate"


def test_ddi_api_requires_two_medicines():
    client = TestClient(app)
    response = client.post("/api/ddi/check", json={"medicines": [KNOWN_MODERATE_A]})
    assert response.status_code == 422
