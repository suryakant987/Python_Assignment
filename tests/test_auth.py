from tests.conftest import ADMIN_PASSWORD, SURVEYOR_PASSWORD, auth_header, login


def test_successful_sign_in(client):
    response = client.post(
        "/auth/login", json={"username": "admin", "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["role"] == "admin"
    assert "password" not in body
    assert ADMIN_PASSWORD not in str(body)


def test_bad_password_is_unauthenticated(client):
    response = client.post(
        "/auth/login", json={"username": "admin", "password": "wrong-password"}
    )
    assert response.status_code == 401
    assert response.json()["error"] == "not_authenticated"


def test_unsigned_request_is_unauthenticated(client):
    response = client.get("/assets")
    assert response.status_code == 401
    assert response.json()["error"] == "not_authenticated"


def test_surveyor_is_refused_a_deletion(client):
    token = login(client, "surveyor1", SURVEYOR_PASSWORD)
    created = client.post(
        "/assets",
        headers=auth_header(token),
        json=_asset("PL-7001"),
    )
    assert created.status_code == 201
    response = client.delete("/assets/PL-7001", headers=auth_header(token))
    assert response.status_code == 403
    assert response.json()["error"] == "forbidden"


def test_admin_can_create_a_user(client):
    token = login(client, "admin", ADMIN_PASSWORD)
    response = client.post(
        "/auth/users",
        headers=auth_header(token),
        json={"username": "surveyor2", "password": "another-pass", "role": "surveyor"},
    )
    assert response.status_code == 201
    assert response.json()["username"] == "surveyor2"
    assert "password" not in response.json()


def _asset(code: str) -> dict:
    return {
        "asset_id": code,
        "name": "Test feeder pole",
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
