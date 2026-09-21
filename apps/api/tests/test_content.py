"""Milestone 5: notes and real file upload/download with ownership checks."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register


def test_personal_note_lifecycle(client: TestClient) -> None:
    owner = register(client, "note-owner@example.com", "noteowner", "Note Owner")
    headers = auth_headers(owner["tokens"])

    created = client.post(
        "/api/v1/notes", headers=headers, json={"title": "Linear Algebra", "body": "Rank-nullity theorem."}
    )
    assert created.status_code == 201
    note = created.json()
    assert note["group_id"] is None

    updated = client.patch(
        f"/api/v1/notes/{note['id']}", headers=headers, json={"body": "Rank-nullity + examples."}
    )
    assert updated.status_code == 200
    assert "examples" in updated.json()["body"]

    listed = client.get("/api/v1/notes", headers=headers).json()
    assert listed["total"] == 1

    assert client.get("/api/v1/notes?search=Rank", headers=headers).json()["total"] == 1
    assert client.get("/api/v1/notes?search=quantum", headers=headers).json()["total"] == 0

    assert client.delete(f"/api/v1/notes/{note['id']}", headers=headers).status_code == 204
    assert client.get("/api/v1/notes", headers=headers).json()["total"] == 0


def test_group_note_is_shared_but_private_note_is_not(client: TestClient) -> None:
    owner = register(client, "gn-owner@example.com", "gnowner", "Group Note Owner")
    member = register(client, "gn-member@example.com", "gnmember", "Group Note Member")
    outsider = register(client, "gn-out@example.com", "gnout", "Group Outsider")
    owner_headers = auth_headers(owner["tokens"])
    member_headers = auth_headers(member["tokens"])
    outsider_headers = auth_headers(outsider["tokens"])

    group = client.post("/api/v1/groups", headers=owner_headers, json={"name": "Notes Group"}).json()
    client.post("/api/v1/groups/join", headers=member_headers, json={"code": group["join_code"]})

    shared = client.post(
        "/api/v1/notes",
        headers=owner_headers,
        json={"title": "Week 3 revision", "body": "Shared with the group.", "group_id": group["id"]},
    ).json()
    private = client.post(
        "/api/v1/notes", headers=owner_headers, json={"title": "Private", "body": "Mine only."}
    ).json()

    # Members can read, edit and list shared notes.
    assert client.get(f"/api/v1/notes/{shared['id']}", headers=member_headers).status_code == 200
    assert (
        client.patch(
            f"/api/v1/notes/{shared['id']}", headers=member_headers, json={"body": "Added a link."}
        ).status_code
        == 200
    )
    group_notes = client.get(f"/api/v1/groups/{group['id']}/notes", headers=member_headers).json()
    assert [n["title"] for n in group_notes["items"]] == ["Week 3 revision"]

    # The owner's private note never appears in a member's listing.
    member_notes = client.get("/api/v1/notes", headers=member_headers).json()
    assert [n["title"] for n in member_notes["items"]] == ["Week 3 revision"]

    # Outsiders are refused both notes.
    assert client.get(f"/api/v1/notes/{shared['id']}", headers=outsider_headers).status_code == 403
    assert client.get(f"/api/v1/notes/{private['id']}", headers=outsider_headers).status_code == 403

    # Deleting is destructive, so it is limited to the author or a manager.
    assert client.delete(f"/api/v1/notes/{shared['id']}", headers=member_headers).status_code == 403
    assert client.delete(f"/api/v1/notes/{shared['id']}", headers=owner_headers).status_code == 204
    assert client.get(f"/api/v1/notes/{shared['id']}", headers=owner_headers).status_code == 404


def test_upload_download_and_delete_a_real_file(client: TestClient, settings) -> None:
    owner = register(client, "file-owner@example.com", "fileowner", "File Owner")
    headers = auth_headers(owner["tokens"])
    payload = b"%PDF-1.4 study notes binary payload"

    uploaded = client.post(
        "/api/v1/files",
        headers=headers,
        files={"file": ("week3.pdf", payload, "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    record = uploaded.json()
    assert record["filename"] == "week3.pdf"
    assert record["size"] == len(payload)

    downloaded = client.get(f"/api/v1/files/{record['id']}", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.content == payload
    # Always served as an attachment so uploads can never execute in the browser.
    assert "attachment" in downloaded.headers["content-disposition"]

    stored = list(settings.storage_dir.rglob("*"))
    assert any(path.is_file() for path in stored), "bytes were not written to storage"

    assert client.delete(f"/api/v1/files/{record['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/files/{record['id']}", headers=headers).status_code == 404


def test_other_users_cannot_download_a_private_file(client: TestClient) -> None:
    owner = register(client, "priv-owner@example.com", "privowner", "Private Owner")
    stranger = register(client, "priv-stranger@example.com", "privstranger", "Stranger")
    headers = auth_headers(owner["tokens"])

    record = client.post(
        "/api/v1/files",
        headers=headers,
        files={"file": ("secret.pdf", b"private bytes", "application/pdf")},
    ).json()

    stranger_headers = auth_headers(stranger["tokens"])
    assert client.get(f"/api/v1/files/{record['id']}", headers=stranger_headers).status_code == 403
    assert client.delete(f"/api/v1/files/{record['id']}", headers=stranger_headers).status_code == 403


def test_group_file_is_visible_to_members_only(client: TestClient) -> None:
    owner = register(client, "gf-owner@example.com", "gfowner", "Group File Owner")
    member = register(client, "gf-member@example.com", "gfmember", "Group File Member")
    outsider = register(client, "gf-out@example.com", "gfout", "Group File Outsider")
    owner_headers = auth_headers(owner["tokens"])
    member_headers = auth_headers(member["tokens"])

    group = client.post("/api/v1/groups", headers=owner_headers, json={"name": "Files Group"}).json()
    client.post("/api/v1/groups/join", headers=member_headers, json={"code": group["join_code"]})

    record = client.post(
        "/api/v1/files",
        headers=owner_headers,
        files={"file": ("slides.pdf", b"slides", "application/pdf")},
        data={"group_id": group["id"]},
    ).json()
    assert record["group_id"] == group["id"]

    assert client.get(f"/api/v1/files/{record['id']}", headers=member_headers).status_code == 200
    assert (
        client.get(f"/api/v1/files/{record['id']}", headers=auth_headers(outsider["tokens"])).status_code
        == 403
    )

    files = client.get(f"/api/v1/groups/{group['id']}/files", headers=member_headers).json()
    assert [f["filename"] for f in files["items"]] == ["slides.pdf"]


def test_dangerous_file_types_are_refused(client: TestClient) -> None:
    owner = register(client, "bad-owner@example.com", "badowner", "Bad Upload Owner")
    response = client.post(
        "/api/v1/files",
        headers=auth_headers(owner["tokens"]),
        files={"file": ("payload.html", b"<script>alert(1)</script>", "text/html")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_upload_into_a_group_requires_membership(client: TestClient) -> None:
    owner = register(client, "mem-owner@example.com", "memowner", "Member Owner")
    outsider = register(client, "mem-out@example.com", "memout", "Outsider Uploader")
    group = client.post(
        "/api/v1/groups", headers=auth_headers(owner["tokens"]), json={"name": "Upload Group"}
    ).json()

    response = client.post(
        "/api/v1/files",
        headers=auth_headers(outsider["tokens"]),
        files={"file": ("notes.pdf", b"nope", "application/pdf")},
        data={"group_id": group["id"]},
    )
    assert response.status_code == 403
