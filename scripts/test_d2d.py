import asyncio
import sys
from pathlib import Path

from fastapi.testclient import TestClient

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.db.models import User, FlightWatch

def test_endpoint():
    db = SessionLocal()
    # Get a test user and watch
    user = db.query(User).first()
    if not user:
        print("No users in DB")
        return
    
    watch = db.query(FlightWatch).filter(FlightWatch.user_id == user.id).first()
    if not watch:
        print("No watch in DB")
        return

    # Use a test client, bypass auth
    client = TestClient(app)
    # Patch get_current_user
    app.dependency_overrides[app.dependency_overrides.get("get_current_user", next(iter([d for d in app.dependency_overrides if "get_current_user" in str(d)])) if app.dependency_overrides else "app.api.deps.get_current_user")] = lambda: user

    # Or just use the token? Easier to just override the dep manually, or hit it with a real token.
    # Let's just override app.dependency_overrides
    from app.api.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: user

    payload = {
        "flight_watch_id": watch.id,
        "origin": {
            "type": "city",
            "label": "Almería",
            "lat": 36.834,
            "lng": -2.463
        },
        "final_destination": {
            "type": "city",
            "label": "Treviso centro"
        },
        "preferences": {
            "min_airport_buffer_minutes": 120,
            "sort_by": "best_balance"
        }
    }

    print(f"Testing with watch_id: {watch.id}")
    response = client.post("/api/v1/door-to-door/search", json=payload)
    print(f"Status: {response.status_code}")
    print(response.json())
    
if __name__ == "__main__":
    test_endpoint()
