from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.helpers import register_and_token


def test_quick_search_and_alert_rule(client: TestClient) -> None:
    token = register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    search = client.post(
        "/api/v1/search/quick",
        params={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date": str(date.today() + timedelta(days=10)),
        },
        headers=headers,
    )
    assert search.status_code == 200
    assert len(search.json()["results"]) >= 1

    create = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=12)),
            "target_price": 35,
        },
    )
    watch_id = create.json()["id"]

    rule = client.post(
        "/api/v1/alerts/rules",
        headers=headers,
        json={
            "watch_id": watch_id,
            "rule_type": "threshold_below",
            "threshold_value": 30,
            "notify_on_every_change": False,
            "cooldown_minutes": 60,
        },
    )
    assert rule.status_code == 200

    rules = client.get(f"/api/v1/alerts/rules?watch_id={watch_id}", headers=headers)
    assert rules.status_code == 200
    assert len(rules.json()) == 1
