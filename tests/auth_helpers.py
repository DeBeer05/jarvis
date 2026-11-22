"""Existing feature regressions now run through real owner login and CSRF."""
from functools import lru_cache
from argon2 import PasswordHasher, Type
from fastapi.testclient import TestClient

TEST_PASSWORD = "synthetic-owner-passphrase"


@lru_cache
def fast_hasher():
    # Faster fixtures; separate security tests verify the production Argon2id cost.
    return PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1, type=Type.ID)


@lru_cache
def owner_hash():
    return fast_hasher().hash(TEST_PASSWORD)


def login(client, username="owner", password=TEST_PASSWORD):
    client.get("/api/v1/auth/csrf")
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password}, headers={"X-Jarvis-CSRF": client.cookies.get("jarvis_csrf", "")})
    if response.status_code == 200:
        client.headers["X-Jarvis-CSRF"] = client.cookies.get("jarvis_csrf", "")
    return response


class AuthenticatedTestClient(TestClient):
    def __enter__(self):
        self.app.state.security.hasher = fast_hasher()
        result = super().__enter__()
        if not self.app.state.security.store.owner():
            self.app.state.security.store.create_owner("owner", owner_hash())
        assert login(self).status_code == 200
        return result
