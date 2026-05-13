from app.main import _parse_cors_origins


def test_parse_cors_origins_defaults_include_localhost_and_loopback(monkeypatch) -> None:
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)

    origins = _parse_cors_origins()

    assert "http://localhost:3000" in origins
    assert "http://127.0.0.1:3000" in origins


def test_parse_cors_origins_keeps_defaults_when_env_is_set(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://example.com,http://localhost:3000")

    origins = _parse_cors_origins()

    assert "https://example.com" in origins
    assert "http://localhost:3000" in origins
    assert "http://127.0.0.1:3000" in origins
