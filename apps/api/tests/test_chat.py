"""Milestone 4 gate: two users exchange messages; pagination and permissions."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register


def setup_group(client: TestClient, owner_email: str, owner_username: str, joiner_email: str, joiner_username: str):
    owner = register(client, owner_email, owner_username, owner_username.title())
    joiner = register(client, joiner_email, joiner_username, joiner_username.title())
    group = client.post(
        "/api/v1/groups", headers=auth_headers(owner["tokens"]), json={"name": "Chat Group"}
    ).json()
    client.post("/api/v1/groups/join", headers=auth_headers(joiner["tokens"]), json={"code": group["join_code"]})
    conversation = client.get(
        f"/api/v1/groups/{group['id']}/conversations", headers=auth_headers(owner["tokens"])
    ).json()[0]
    return owner, joiner, group, conversation


def test_two_members_can_exchange_messages(client: TestClient) -> None:
    owner, joiner, _group, conversation = setup_group(
        client, "chat-owner@example.com", "chatowner", "chat-joiner@example.com", "chatjoiner"
    )

    first = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=auth_headers(owner["tokens"]),
        json={"body": "Morning! Sharing last night's notes."},
    )
    assert first.status_code == 201
    assert first.json()["author"]["username"] == "chatowner"

    reply = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=auth_headers(joiner["tokens"]),
        json={"body": "Got them, thanks!"},
    )
    assert reply.status_code == 201

    listed = client.get(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=auth_headers(owner["tokens"]),
    )
    assert listed.status_code == 200
    page = listed.json()
    assert page["total"] == 2
    # Oldest first so the transcript reads like a conversation.
    assert [m["body"] for m in page["items"]] == [
        "Morning! Sharing last night's notes.",
        "Got them, thanks!",
    ]


def test_messages_are_paginated_newest_page_last(client: TestClient) -> None:
    owner, _joiner, _group, conversation = setup_group(
        client, "page-owner@example.com", "pageowner", "page-joiner@example.com", "pagejoiner"
    )
    headers = auth_headers(owner["tokens"])
    for index in range(5):
        client.post(
            f"/api/v1/conversations/{conversation['id']}/messages",
            headers=headers,
            json={"body": f"message {index}"},
        )

    first_page = client.get(
        f"/api/v1/conversations/{conversation['id']}/messages?limit=2&offset=0", headers=headers
    ).json()
    assert first_page["total"] == 5
    assert [m["body"] for m in first_page["items"]] == ["message 3", "message 4"]

    last_page = client.get(
        f"/api/v1/conversations/{conversation['id']}/messages?limit=2&offset=3", headers=headers
    ).json()
    assert [m["body"] for m in last_page["items"]] == ["message 0", "message 1"]


def test_non_member_cannot_read_or_post(client: TestClient) -> None:
    owner, _joiner, _group, conversation = setup_group(
        client, "iso-owner@example.com", "isoowner", "iso-joiner@example.com", "isojoiner"
    )
    outsider = register(client, "iso-outsider@example.com", "isooutsider", "Iso Outsider")
    outsider_headers = auth_headers(outsider["tokens"])

    assert (
        client.get(
            f"/api/v1/conversations/{conversation['id']}/messages", headers=outsider_headers
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/conversations/{conversation['id']}/messages",
            headers=outsider_headers,
            json={"body": "let me in"},
        ).status_code
        == 403
    )
    del owner


def test_blank_message_is_rejected(client: TestClient) -> None:
    owner, _joiner, _group, conversation = setup_group(
        client, "blank-owner@example.com", "blankowner", "blank-joiner@example.com", "blankjoiner"
    )
    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=auth_headers(owner["tokens"]),
        json={"body": "    "},
    )
    assert response.status_code == 422


def test_author_can_edit_and_delete_only_own_message(client: TestClient) -> None:
    owner, joiner, _group, conversation = setup_group(
        client, "edit-owner@example.com", "editowner", "edit-joiner@example.com", "editjoiner"
    )
    owner_headers = auth_headers(owner["tokens"])
    joiner_headers = auth_headers(joiner["tokens"])

    message = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=owner_headers,
        json={"body": "original text"},
    ).json()

    assert (
        client.patch(
            f"/api/v1/messages/{message['id']}", headers=joiner_headers, json={"body": "hijacked"}
        ).status_code
        == 403
    )

    edited = client.patch(
        f"/api/v1/messages/{message['id']}", headers=owner_headers, json={"body": "corrected text"}
    )
    assert edited.status_code == 200
    assert edited.json()["body"] == "corrected text"
    assert edited.json()["edited_at"] is not None

    assert client.delete(f"/api/v1/messages/{message['id']}", headers=joiner_headers).status_code == 403
    assert client.delete(f"/api/v1/messages/{message['id']}", headers=owner_headers).status_code == 204


def test_unread_watermark_advances_when_conversation_is_read(client: TestClient) -> None:
    owner, joiner, group, conversation = setup_group(
        client, "unread-owner@example.com", "unreadowner", "unread-joiner@example.com", "unreadjoiner"
    )
    owner_headers = auth_headers(owner["tokens"])
    joiner_headers = auth_headers(joiner["tokens"])

    # The joiner writes two messages; the owner has read nothing yet.
    for body in ("first", "second"):
        client.post(
            f"/api/v1/conversations/{conversation['id']}/messages",
            headers=joiner_headers,
            json={"body": body},
        )

    assert client.get(f"/api/v1/groups/{group['id']}", headers=owner_headers).json()["unread_count"] == 2
    # An author never counts their own messages as unread.
    assert client.get(f"/api/v1/groups/{group['id']}", headers=joiner_headers).json()["unread_count"] == 0

    assert (
        client.post(f"/api/v1/conversations/{conversation['id']}/read", headers=owner_headers).status_code
        == 204
    )
    assert client.get(f"/api/v1/groups/{group['id']}", headers=owner_headers).json()["unread_count"] == 0
