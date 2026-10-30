import pytest
from fastapi.testclient import TestClient

from backend.app.core.database import get_db
from backend.app.main import app


@pytest.fixture
def api_client(test_db):
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.parametrize(
    "payload",
    [
        {"campaign_id": "CMP_1", "provider_name": "unknown"},
        {"campaign_id": "CMP_1", "batch_size": 0},
        {"campaign_id": "CMP_1", "answer_probability": 1.1},
        {"campaign_id": "CMP_1", "talk_time_sec": 0},
    ],
)
def test_progressive_dial_rejects_invalid_input(api_client, payload):
    response = api_client.post("/api/calls/dial/progressive", json=payload)

    assert response.status_code == 422


def test_simulation_rejects_out_of_range_cycle_count(api_client):
    response = api_client.post(
        "/api/simulation/run",
        json={"cycles": 21},
    )

    assert response.status_code == 422


def test_unknown_provider_circuit_reset_is_not_found(api_client):
    response = api_client.post("/api/providers/not-a-provider/reset-circuit")

    assert response.status_code == 404
