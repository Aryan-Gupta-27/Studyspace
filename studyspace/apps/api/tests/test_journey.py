"""Milestone 7 regression: the complete MVP journey end to end.

register -> group -> chat -> note -> file -> project -> task
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_complete_user_journey(client: TestClient, settings) -> None:
    # 1. Register two students.
    aryan = client.post(
        "/api/v1/auth/register",
        json={
            "email": "aryan@example.com",
            "username": "aryan",
            "full_name": "Aryan Gupta",
            "password": "password123",
        },
    )
    assert aryan.status_code == 201
    aryan_headers = {"Authorization": f"Bearer {aryan.json()['tokens']['access_token']}"}

    rahul = client.post(
        "/api/v1/auth/register",
        json={
            "email": "rahul@example.com",
            "username": "rahul",
            "full_name": "Rahul Sharma",
            "password": "password123",
        },
    )
    rahul_headers = {"Authorization": f"Bearer {rahul.json()['tokens']['access_token']}"}

    # 2. Complete a profile.
    profile = client.patch(
        "/api/v1/users/me",
        headers=aryan_headers,
        json={"institution": "IIT BHU", "program": "B.Tech", "skills": ["Python"]},
    )
    assert profile.status_code == 200
    assert profile.json()["profile"]["institution"] == "IIT BHU"

    # 3. Create a group and let the second student join.
    group = client.post(
        "/api/v1/groups",
        headers=aryan_headers,
        json={"name": "Machine Learning Study Group", "description": "Semester 5 prep"},
    ).json()
    joined = client.post(
        "/api/v1/groups/join", headers=rahul_headers, json={"code": group["join_code"]}
    )
    assert joined.status_code == 200

    # 4. Chat inside the group.
    conversation = client.get(
        f"/api/v1/groups/{group['id']}/conversations", headers=aryan_headers
    ).json()[0]
    message = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=aryan_headers,
        json={"body": "I uploaded the dataset notes."},
    )
    assert message.status_code == 201

    # 5. Share a note.
    note = client.post(
        "/api/v1/notes",
        headers=aryan_headers,
        json={
            "title": "Gradient Descent",
            "body": "Update rule and convergence notes.",
            "group_id": group["id"],
        },
    ).json()
    assert client.get(f"/api/v1/notes/{note['id']}", headers=rahul_headers).status_code == 200

    # 6. Upload and download a real file.
    payload = b"%PDF-1.4 real bytes for the regression test"
    uploaded = client.post(
        "/api/v1/files",
        headers=aryan_headers,
        files={"file": ("gradient_descent.pdf", payload, "application/pdf")},
        data={"group_id": group["id"]},
    ).json()
    assert client.get(f"/api/v1/files/{uploaded['id']}", headers=rahul_headers).content == payload

    # 7. Create a project and move a task to done.
    project = client.post(
        f"/api/v1/groups/{group['id']}/projects",
        headers=aryan_headers,
        json={"name": "ML Research Project", "status": "ACTIVE"},
    ).json()
    task = client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        headers=aryan_headers,
        json={"title": "Preprocess dataset", "priority": "HIGH", "assignee_id": rahul.json()["user"]["id"]},
    ).json()
    completed = client.post(
        f"/api/v1/tasks/{task['id']}/move", headers=rahul_headers, json={"status": "DONE", "position": 0}
    ).json()
    assert completed["status"] == "DONE"

    # 8. The dashboard reflects the whole journey in one place.
    dashboard = client.get("/api/v1/groups", headers=aryan_headers).json()
    assert dashboard["total"] == 1
    assert dashboard["items"][0]["member_count"] == 2

    board = client.get(f"/api/v1/projects/{project['id']}/board", headers=aryan_headers).json()
    assert [t["title"] for t in board["DONE"]] == ["Preprocess dataset"]


def test_unauthenticated_requests_never_reach_data(client: TestClient) -> None:
    for path in (
        "/api/v1/users/me",
        "/api/v1/groups",
        "/api/v1/notes",
        "/api/v1/files",
        "/api/v1/groups/discover",
    ):
        assert client.get(path).status_code == 401, path


def test_unexpected_errors_are_returned_as_safe_envelopes(client: TestClient) -> None:
    # A random, well-formed id on a protected route must produce the standard
    # error envelope rather than a stack trace or a 500.
    aryan = client.post(
        "/api/v1/auth/register",
        json={
            "email": "errors@example.com",
            "username": "errorsuser",
            "full_name": "Errors User",
            "password": "password123",
        },
    ).json()
    headers = {"Authorization": f"Bearer {aryan['tokens']['access_token']}"}

    response = client.get("/api/v1/groups/does-not-exist", headers=headers)
    assert response.status_code == 404
    body = response.json()
    assert set(body["error"]) == {"code", "message"}
    assert "Traceback" not in response.text
