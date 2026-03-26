from fastapi.testclient import TestClient


def register_and_token(client: TestClient, email: str = "qa@viru.dev", password: str = "password123") -> str:
    register = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    if register.status_code == 409:
        login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        return login.json()["access_token"]
    return register.json()["access_token"]
