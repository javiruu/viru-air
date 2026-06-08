from fastapi.testclient import TestClient

from tests.helpers import register_and_token


def test_support_help_returns_guided_action_hierarchy(client: TestClient) -> None:
    token = register_and_token(client, email="support@viru.dev", password="Pass1234")

    response = client.get("/api/v1/support/help", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200

    payload = response.json()
    assert payload["title"] == "Centro de ayuda"
    assert payload["status"]["state"] == "ok"
    assert "flujo principal" in payload["status"]["message"]

    sections = payload["sections"]
    assert len(sections) >= 6

    hrefs = [section["cta_href"] for section in sections]
    assert hrefs[0] == "/dashboard"
    assert hrefs[1] == "/quick-search"
    assert hrefs[-1] == "/soporte/contacto"
    assert len(hrefs) == len(set(hrefs))

    for section in sections:
        assert section["title"]
        assert section["body"]
        assert section["cta_label"]
        assert section["cta_href"].startswith("/")

    support_section = sections[-1]
    assert support_section["title"] == "Soporte directo"
    assert "solo cuando necesites ayuda concreta" in support_section["body"]
    assert support_section["cta_label"] == "Abrir contacto de soporte"
