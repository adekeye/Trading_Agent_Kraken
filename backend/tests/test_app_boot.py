"""Smoke tests covering app boot, auth flow, and a parse round-trip."""
from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_login_and_parse_roundtrip():
    with TestClient(app) as client:
        r = client.post("/auth/register", json={"email": "smoke@test.com", "password": "supersecret123"})
        assert r.status_code in (200, 409), r.text
        if r.status_code == 200:
            token = r.json()["access_token"]
        else:
            r2 = client.post("/auth/login", json={"email": "smoke@test.com", "password": "supersecret123"})
            assert r2.status_code == 200, r2.text
            token = r2.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        r = client.post(
            "/commands/parse",
            json={"text": "Buy 100 XRP at 0.50"},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["intent"] == "place_order"
        assert data["asset"] == "XRP"
        assert data["limit_price"] == 0.5

        r = client.post("/commands/parse", json={"text": "Buy Tesla stock"}, headers=headers)
        assert r.status_code == 200
        assert r.json()["intent"] == "unknown"

        r = client.get("/audit-logs", headers=headers)
        assert r.status_code == 200
        events = [it["event_type"] for it in r.json()]
        assert "command_parsed" in events


def test_preview_rejects_market_orders_via_parser():
    """End-to-end: a market-buy command should be rejected before any preview."""
    with TestClient(app) as client:
        client.post("/auth/register", json={"email": "mkt@test.com", "password": "supersecret123"})
        login = client.post("/auth/login", json={"email": "mkt@test.com", "password": "supersecret123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post("/commands/preview", json={"text": "Market buy BTC"}, headers=headers)
        assert r.status_code == 400
        assert "limit" in r.json()["detail"].lower()


def test_preview_rejects_stocks():
    with TestClient(app) as client:
        client.post("/auth/register", json={"email": "stk@test.com", "password": "supersecret123"})
        login = client.post("/auth/login", json={"email": "stk@test.com", "password": "supersecret123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post("/commands/preview", json={"text": "Buy 10 Apple shares at 200"}, headers=headers)
        assert r.status_code == 400


def test_dry_run_preview_then_confirm_returns_simulation():
    """Full happy path through preview + confirm in dry-run mode (no Kraken needed)."""
    with TestClient(app) as client:
        email = "dryrun@test.com"
        client.post("/auth/register", json={"email": email, "password": "supersecret123"})
        login = client.post("/auth/login", json={"email": email, "password": "supersecret123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Default: dry_run=True, max_order_notional_usd=1000
        # Use a small order to stay below the cap and below large-order threshold.
        r = client.post(
            "/commands/preview",
            json={"text": "Buy 10 XRP at 0.50"},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        prev = r.json()
        assert prev["dry_run"] is True
        assert prev["pair"] == "XRPUSD"
        assert prev["volume"] == 10
        assert prev["limit_price"] == 0.5

        r = client.post(
            "/commands/confirm",
            json={"confirmation_id": prev["confirmation_id"], "confirm": True},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        result = r.json()
        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["kraken_txid"] is None
