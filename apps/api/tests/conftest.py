"""Shared pytest fixtures.

Tests run against a real SQLite database and a real storage directory, then
throw both away. Nothing is mocked at the boundary that matters (RULEBOOK
rule 69: test real behaviour).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

# Configuration is pinned before the app is imported so no test can depend on
# the developer's local .env.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-not-used-in-production-0123456789")

import pytest
from app.core import rate_limit
from app.core.config import Settings
from app.core.database import configure_database, get_session_factory, init_database
from app.core.dependencies import get_settings_dependency
from app.core.security import hash_password
from app.main import create_app
from app.models.identity import Profile, User
from app.services import storage as storage_module
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def storage_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("storage")
    return directory


@pytest.fixture
def settings(tmp_path: Path, storage_dir: Path) -> Settings:
    return Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        storage_dir=storage_dir,
        jwt_secret="test-secret-key-not-used-in-production-0123456789",
        cors_origins=["http://localhost:3000"],
    )


@pytest.fixture
def db(settings: Settings):
    """A fresh, migrated-empty database for every test."""
    import app.models  # noqa: F401  ensure models are registered

    engine = configure_database(settings.database_url)
    init_database(engine)
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(settings: Settings, storage_dir: Path) -> Iterator[TestClient]:
    # Point the process-wide engine at this test's throwaway database *before*
    # the lifespan startup hook creates the schema, otherwise the app would
    # silently bootstrap against the developer's database.
    import app.models  # noqa: F401

    configure_database(settings.database_url)
    app = create_app(settings)
    app.dependency_overrides[get_settings_dependency] = lambda: settings
    storage_module.configure_storage(storage_module.LocalStorageBackend(settings.storage_dir))
    rate_limit.reset()
    with TestClient(app) as test_client:
        yield test_client
    storage_module.configure_storage(storage_module.LocalStorageBackend(storage_dir))


def make_user(db, email: str, username: str, password: str = "password123", name: str | None = None) -> User:
    """Create a user directly, bypassing the HTTP layer."""
    user = User(
        email=email,
        username=username,
        full_name=name or username.title(),
        password_hash=hash_password(password),
    )
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id))
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def alice(db):
    return make_user(db, "alice@example.com", "alice", name="Alice Sharma")


@pytest.fixture
def bob(db):
    return make_user(db, "bob@example.com", "bob", name="Bob Verma")


def register(client: TestClient, email: str, username: str, name: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "full_name": name,
            "password": "password123",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}
