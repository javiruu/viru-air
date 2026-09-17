import json
from pathlib import Path
from app.main import app

def test_openapi_spec_is_valid_and_generates_paths():
    spec = app.openapi()
    assert spec is not None
    assert spec.get("openapi", "").startswith("3.")
    assert "paths" in spec
    assert len(spec["paths"]) > 50
    assert "/api/v1/auth/login" in spec["paths"]
    assert "/api/v1/search/quick" in spec["paths"]
    assert "/api/v1/watchlist" in spec["paths"]

def test_openapi_snapshot_exists():
    snapshot_path = Path(__file__).resolve().parents[3] / "docs" / "architecture" / "openapi.json"
    assert snapshot_path.exists(), "docs/architecture/openapi.json snapshot must exist"
    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert data["info"]["title"] == app.title

