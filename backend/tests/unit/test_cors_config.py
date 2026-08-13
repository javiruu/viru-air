from app.main import _parse_cors_origins


def test_parse_cors_origins_defaults_include_localhost_and_loopback(monkeypatch) -> None:
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)

    origins = _parse_cors_origins()

    assert "http://localhost:3000" in origins
    assert "http://127.0.0.1:3000" in origins


def test_parse_cors_origins_uses_only_explicit_origins_when_env_is_set(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://example.com,http://localhost:3000")

    origins = _parse_cors_origins()

    assert "https://example.com" in origins
    assert "http://localhost:3000" in origins
    assert "http://127.0.0.1:3000" not in origins


def test_auth_login_preflight_allows_local_frontend_origin(client) -> None:
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
    assert "POST" in response.headers["access-control-allow-methods"]
