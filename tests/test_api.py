from tests.conftest import ADMIN_PASSWORD, SURVEYOR_PASSWORD, SAMPLE_CSV, auth_header, login

PAYLOAD = {
    "asset_id": "PL-8001",
    "name": "Network test pole",
    "asset_type": "pole",
    "latitude": 20.2961,
    "longitude": 85.8245,
    "elevation_m": 40,
    "surveyed_on": "2026-09-10",
    "surveyor": "Anita Das",
    "status": "active",
    "condition_score": 7,
    "attribute_json": {"height_m": 9},
}


def test_status_is_unprotected(client):
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_crud_and_missing_record(client):
    token = login(client, "admin", ADMIN_PASSWORD)
    headers = auth_header(token)

    created = client.post("/assets", headers=headers, json=PAYLOAD)
    assert created.status_code == 201
    assert created.json()["asset_id"] == "PL-8001"
    assert created.json()["condition_band"] == "FAIR"

    listed = client.get("/assets", headers=headers, params={"limit": 25, "offset": 0})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["limit"] == 25
    assert len(listed.json()["items"]) == 1

    fetched = client.get("/assets/PL-8001", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Network Test Pole"

    missing = client.get("/assets/PL-9999", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["error"] == "not_found"

    replaced = client.put(
        "/assets/PL-8001",
        headers=headers,
        json={**PAYLOAD, "name": "replaced pole name", "condition_score": 3},
    )
    assert replaced.status_code == 200
    assert replaced.json()["condition_score"] == 3
    assert replaced.json()["condition_band"] == "POOR"

    patched = client.patch(
        "/assets/PL-8001",
        headers=headers,
        json={"condition_score": 9},
    )
    assert patched.status_code == 200
    assert patched.json()["condition_score"] == 9

    history = client.get("/assets/PL-8001/visits", headers=headers)
    assert history.status_code == 200
    assert len(history.json()["visits"]) >= 3

    deleted = client.delete("/assets/PL-8001", headers=headers)
    assert deleted.status_code == 200
    assert "deleted" in deleted.json()["message"].lower()

    gone = client.get("/assets/PL-8001", headers=headers)
    assert gone.status_code == 404


def test_duplicate_create_is_refused(client):
    token = login(client, "admin", ADMIN_PASSWORD)
    headers = auth_header(token)
    assert client.post("/assets", headers=headers, json=PAYLOAD).status_code == 201
    again = client.post("/assets", headers=headers, json=PAYLOAD)
    assert again.status_code == 422
    assert again.json()["error"] == "validation_error"
    assert any(item["field"] == "asset_id" for item in again.json()["details"])


def test_search_filter_and_paging(client):
    headers = auth_header(login(client, "surveyor1", SURVEYOR_PASSWORD))
    admin = auth_header(login(client, "admin", ADMIN_PASSWORD))
    with SAMPLE_CSV.open("rb") as handle:
        uploaded = client.post(
            "/ingest/upload",
            headers=admin,
            files={"file": ("survey_export.csv", handle, "text/csv")},
        )
    assert uploaded.status_code == 200
    assert uploaded.json()["rows_accepted"] == 51
    assert uploaded.json()["rows_rejected"] == 11

    poles = client.get("/assets", headers=headers, params={"type": "pole", "limit": 10})
    assert poles.status_code == 200
    assert poles.json()["limit"] == 10
    assert poles.json()["total"] >= 10
    assert all(item["asset_type"] == "pole" for item in poles.json()["items"])

    search = client.get("/assets", headers=headers, params={"q": "MARKET"})
    assert search.status_code == 200
    assert search.json()["total"] >= 1

    too_big = client.get("/assets", headers=headers, params={"limit": 101})
    assert too_big.status_code == 422


def test_reports_and_cache_refresh(client):
    admin = auth_header(login(client, "admin", ADMIN_PASSWORD))
    with SAMPLE_CSV.open("rb") as handle:
        client.post("/ingest/upload", headers=admin, files={"file": ("survey_export.csv", handle, "text/csv")})

    first = client.get("/reports/summary", headers=admin)
    assert first.status_code == 200
    assert first.json()["from_cache"] is False

    second = client.get("/reports/summary", headers=admin)
    assert second.status_code == 200
    assert second.json()["from_cache"] is True

    repairs = client.get("/reports/repairs", headers=admin)
    assert repairs.status_code == 200
    assert repairs.json()["total"] >= 1
    assert all(item["condition_score"] < 5 for item in repairs.json()["items"])

    visited = client.get("/reports/most-visited", headers=admin)
    assert visited.status_code == 200

    nearest = client.get(
        "/reports/nearest",
        headers=admin,
        params={"latitude": 20.2961, "longitude": 85.8245},
    )
    assert nearest.status_code == 200
    assert nearest.json()["asset"]["asset_id"]

    created = client.post(
        "/assets",
        headers=admin,
        json={**PAYLOAD, "asset_id": "PL-8888"},
    )
    assert created.status_code == 201
    third = client.get("/reports/summary", headers=admin)
    assert third.json()["from_cache"] is False
