from asset_registry.config import get_settings
from tests.conftest import ADMIN_PASSWORD, auth_header, login


def test_caller_is_refused_after_request_limit(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_per_minute", 3)
    token = login(client, "admin", ADMIN_PASSWORD)
    headers = auth_header(token)

    statuses = [client.get("/assets", headers=headers).status_code for _ in range(4)]
    assert 429 in statuses

    last = client.get("/assets", headers=headers)
    assert last.status_code == 429
    assert last.json()["error"] == "rate_limited"
    assert "Retry-After" in last.headers
    assert last.headers["Retry-After"].isdigit()
