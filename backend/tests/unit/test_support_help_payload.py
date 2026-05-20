from app.api.v1.support import help_payload


CANONICAL_PRIVATE_ROUTES = {
    "/dashboard",
    "/watchlist",
    "/quick-search",
    "/alerts",
    "/recomendaciones",
    "/preferencias",
    "/soporte/contacto",
}

LEGACY_ROUTES = {"/history", "/preferences", "/suggestions"}


def test_help_payload_exposes_expected_operational_sections() -> None:
    payload = help_payload()
    sections = payload["sections"]
    section_titles = {section["title"] for section in sections}

    assert payload["title"] == "Centro de ayuda"
    assert payload["status"]["state"] == "ok"
    assert {
        "Empieza por el panel",
        "Gestiona rutas en Watchlist",
        "Busca oportunidades en Quick Search",
        "Controla tus alertas",
        "Revisa recomendaciones",
        "Ajusta preferencias",
        "Soporte directo",
    }.issubset(section_titles)


def test_help_payload_ctas_use_canonical_routes_only() -> None:
    payload = help_payload()
    sections = payload["sections"]

    cta_hrefs = [section.get("cta_href") for section in sections if section.get("cta_href")]
    assert set(cta_hrefs).issubset(CANONICAL_PRIVATE_ROUTES)
    assert set(cta_hrefs).isdisjoint(LEGACY_ROUTES)
