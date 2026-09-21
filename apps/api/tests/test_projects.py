"""Milestone 6: projects, tasks and the four-column board."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register


def setup_project(client: TestClient, suffix: str) -> tuple[dict, dict, dict, dict, dict]:
    owner = register(client, f"pj-owner-{suffix}@example.com", f"pjowner{suffix}", "Project Owner")
    member = register(client, f"pj-member-{suffix}@example.com", f"pjmember{suffix}", "Project Member")
    owner_headers = auth_headers(owner["tokens"])
    member_headers = auth_headers(member["tokens"])

    group = client.post(
        "/api/v1/groups", headers=owner_headers, json={"name": f"Project Group {suffix}"}
    ).json()
    client.post("/api/v1/groups/join", headers=member_headers, json={"code": group["join_code"]})
    project = client.post(
        f"/api/v1/groups/{group['id']}/projects",
        headers=owner_headers,
        json={"name": "ML Research", "description": "Semester project", "status": "ACTIVE"},
    ).json()
    return owner, member, group, project, {"owner": owner_headers, "member": member_headers}


def test_group_can_create_a_project_with_members(client: TestClient) -> None:
    _owner, _member, group, project, headers = setup_project(client, "a")

    assert project["status"] == "ACTIVE"
    assert project["group_id"] == group["id"]

    listed = client.get(f"/api/v1/groups/{group['id']}/projects", headers=headers["member"]).json()
    assert [p["name"] for p in listed["items"]] == ["ML Research"]
    assert listed["total"] == 1


def test_task_can_be_created_assigned_and_moved_across_the_board(client: TestClient) -> None:
    owner, member, _group, project, headers = setup_project(client, "b")

    task = client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        headers=headers["owner"],
        json={
            "title": "Collect dataset",
            "description": "Scrape and clean the corpus.",
            "priority": "HIGH",
            "assignee_id": member["user"]["id"],
        },
    )
    assert task.status_code == 201, task.text
    created = task.json()
    assert created["status"] == "TODO"
    assert created["priority"] == "HIGH"
    assert created["assignee"]["username"] == member["user"]["username"]

    moved = client.post(
        f"/api/v1/tasks/{created['id']}/move",
        headers=headers["member"],
        json={"status": "IN_PROGRESS", "position": 0},
    )
    assert moved.status_code == 200
    assert moved.json()["status"] == "IN_PROGRESS"

    done = client.post(
        f"/api/v1/tasks/{created['id']}/move", headers=headers["member"], json={"status": "DONE", "position": 0}
    ).json()
    assert done["completed_at"] is not None

    board = client.get(f"/api/v1/projects/{project['id']}/board", headers=headers["owner"]).json()
    assert sorted(board.keys()) == ["DONE", "IN_PROGRESS", "REVIEW", "TODO"]
    assert [t["title"] for t in board["DONE"]] == ["Collect dataset"]
    assert board["TODO"] == []

    counts = client.get(f"/api/v1/projects/{project['id']}", headers=headers["owner"]).json()["task_counts"]
    assert counts == {"DONE": 1}
    del owner


def test_task_assignment_is_limited_to_group_members(client: TestClient) -> None:
    _owner, member, _group, project, headers = setup_project(client, "c")
    outsider = register(client, "pj-outsider-c@example.com", "pjoutsiderc", "Outsider")

    response = client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        headers=headers["owner"],
        json={"title": "Assign to stranger", "assignee_id": outsider["user"]["id"]},
    )
    assert response.status_code == 404
    del member


def test_outside_user_cannot_read_project_or_tasks(client: TestClient) -> None:
    _owner, _member, _group, project, headers = setup_project(client, "d")
    outsider = register(client, "pj-outsider-d@example.com", "pjoutsiderd", "Outsider")
    outsider_headers = auth_headers(outsider["tokens"])

    assert client.get(f"/api/v1/projects/{project['id']}", headers=outsider_headers).status_code == 403
    assert (
        client.get(f"/api/v1/projects/{project['id']}/board", headers=outsider_headers).status_code == 403
    )
    assert (
        client.post(
            f"/api/v1/projects/{project['id']}/tasks",
            headers=outsider_headers,
            json={"title": "Sneaky task"},
        ).status_code
        == 403
    )
    del headers


def test_only_managers_can_update_or_delete_a_project(client: TestClient) -> None:
    _owner, member, _group, project, headers = setup_project(client, "e")

    assert (
        client.patch(
            f"/api/v1/projects/{project['id']}", headers=headers["member"], json={"name": "Renamed"}
        ).status_code
        == 403
    )
    assert client.delete(f"/api/v1/projects/{project['id']}", headers=headers["member"]).status_code == 403

    renamed = client.patch(
        f"/api/v1/projects/{project['id']}", headers=headers["owner"], json={"name": "Renamed by owner"}
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Renamed by owner"

    assert client.delete(f"/api/v1/projects/{project['id']}", headers=headers["owner"]).status_code == 204
    assert client.get(f"/api/v1/projects/{project['id']}", headers=headers["owner"]).status_code == 404


def test_deleting_a_project_removes_its_tasks(client: TestClient) -> None:
    _owner, _member, _group, project, headers = setup_project(client, "f")
    task = client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        headers=headers["owner"],
        json={"title": "Temporary task"},
    ).json()

    assert client.delete(f"/api/v1/projects/{project['id']}", headers=headers["owner"]).status_code == 204
    assert client.delete(f"/api/v1/tasks/{task['id']}", headers=headers["owner"]).status_code == 404
