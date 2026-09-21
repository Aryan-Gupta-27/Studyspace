"""Milestone 2 gate: health, registration, login, protected access, refresh."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register


def test_health_endpoint_reports_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_registration_creates_account_profile_and_session(client: TestClient) -> None:
    body = register(client, "arya@example.com", "arya", "Aryan Gupta")

    assert body["user"]["email"] == "arya@example.com"
    assert body["user"]["username"] == "arya"
    assert body["user"]["profile"]["bio"] == ""
    assert body["tokens"]["token_type"] == "bearer"
    assert body["tokens"]["expires_in"] > 0

    me = client.get("/api/v1/users/me", headers=auth_headers(body["tokens"]))
    assert me.status_code == 200
    assert me.json()["id"] == body["user"]["id"]


def test_duplicate_email_is_rejected_with_conflict(client: TestClient) -> None:
    register(client, "dupe@example.com", "first_user", "First User")
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "dupe@example.com",
            "username": "second_user",
            "full_name": "Second User",
            "password": "password123",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RESOURCE_CONFLICT"


def test_duplicate_username_is_rejected(client: TestClient) -> None:
    register(client, "one@example.com", "sharedname", "One User")
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "two@example.com",
            "username": "sharedname",
            "full_name": "Two User",
            "password": "password123",
        },
    )
    assert response.status_code == 409


def test_weak_password_is_rejected_by_validation(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "weak@example.com",
            "username": "weakuser",
            "full_name": "Weak User",
            "password": "short",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_login_with_wrong_password_fails_without_leaking_account_state(client: TestClient) -> None:
    register(client, "login@example.com", "loginuser", "Login User")

    wrong_password = client.post(
        "/api/v1/auth/login", json={"email": "login@example.com", "password": "not-the-password"}
    )
    unknown_account = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "password123"}
    )

    # Identical response for both cases: no account enumeration.
    assert wrong_password.status_code == 401
    assert unknown_account.status_code == 401
    assert wrong_password.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert unknown_account.json()["error"] == wrong_password.json()["error"]


def test_protected_endpoint_requires_a_valid_token(client: TestClient) -> None:
    assert client.get("/api/v1/users/me").status_code == 401

    forged = client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer not.a.real.token"}
    )
    assert forged.status_code == 401


def test_refresh_rotates_token_and_rejects_replay(client: TestClient) -> None:
    body = register(client, "refresh@example.com", "refreshuser", "Refresh User")
    refresh_token = body["tokens"]["refresh_token"]

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    new_access = refreshed.json()["access_token"]
    new_refresh = refreshed.json()["refresh_token"]
    assert new_access != body["tokens"]["access_token"]

    # The rotated token is single use: replaying it must fail.
    replay = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert replay.status_code == 401

    # The new token works, and logout revokes it.
    assert client.get("/api/v1/users/me", headers=auth_headers(refreshed.json())).status_code == 200
    logout = client.post("/api/v1/auth/logout", json={"refresh_token": new_refresh})
    assert logout.status_code == 200
    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert reused.status_code == 401


def test_profile_can_be_updated_and_read_back(client: TestClient) -> None:
    body = register(client, "profile@example.com", "profileuser", "Profile User")
    headers = auth_headers(body["tokens"])

    updated = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={
            "bio": "Studying machine learning.",
            "institution": "IIT BHU",
            "program": "B.Tech CSE",
            "academic_year": "3rd year",
            "skills": ["Python", "Python", "  PyTorch  "],
            "interests": ["ML"],
        },
    )
    assert updated.status_code == 200
    profile = updated.json()["profile"]
    assert profile["institution"] == "IIT BHU"
    # Duplicate and untrimmed tags are normalised on the way in.
    assert profile["skills"] == ["Python", "PyTorch"]

    persisted = client.get("/api/v1/users/me", headers=headers).json()
    assert persisted["profile"] == profile
