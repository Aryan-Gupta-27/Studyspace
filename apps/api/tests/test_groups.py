"""Milestone 4: groups, memberships, roles and join/leave flows."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register


def create_group(client: TestClient, headers: dict[str, str], name: str = "ML Study Group") -> dict:
    response = client.post(
        "/api/v1/groups", headers=headers, json={"name": name, "description": "Exam prep"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_creator_becomes_owner_and_group_opens_a_conversation(client: TestClient) -> None:
    owner = register(client, "owner@example.com", "owner", "Owner User")
    headers = auth_headers(owner["tokens"])

    group = create_group(client, headers)
    assert group["role"] == "OWNER"
    assert group["member_count"] == 1

    members = client.get(f"/api/v1/groups/{group['id']}/members", headers=headers)
    assert members.status_code == 200
    assert members.json()[0]["role"] == "OWNER"

    conversations = client.get(f"/api/v1/groups/{group['id']}/conversations", headers=headers)
    assert conversations.status_code == 200
    assert [c["name"] for c in conversations.json()] == ["General"]


def test_non_member_cannot_read_or_mutate_a_private_group(client: TestClient) -> None:
    owner = register(client, "owner2@example.com", "owner2", "Owner Two")
    outsider = register(client, "outsider@example.com", "outsider", "Outsider User")
    group = create_group(client, auth_headers(owner["tokens"]), name="Private Group")

    outsider_headers = auth_headers(outsider["tokens"])
    assert client.get(f"/api/v1/groups/{group['id']}", headers=outsider_headers).status_code == 403
    assert (
        client.patch(
            f"/api/v1/groups/{group['id']}",
            headers=outsider_headers,
            json={"name": "Hijacked"},
        ).status_code
        == 403
    )
    assert client.delete(f"/api/v1/groups/{group['id']}", headers=outsider_headers).status_code == 403


def test_second_user_can_join_with_the_invite_code(client: TestClient) -> None:
    owner = register(client, "owner3@example.com", "owner3", "Owner Three")
    joiner = register(client, "joiner@example.com", "joiner", "Joiner User")
    group = create_group(client, auth_headers(owner["tokens"]))

    joiner_headers = auth_headers(joiner["tokens"])
    joined = client.post(
        "/api/v1/groups/join", headers=joiner_headers, json={"code": group["join_code"]}
    )
    assert joined.status_code == 200
    assert joined.json()["role"] == "MEMBER"
    assert joined.json()["member_count"] == 2

    # Joining twice is a conflict rather than a silent duplicate membership.
    again = client.post(
        "/api/v1/groups/join", headers=joiner_headers, json={"code": group["join_code"]}
    )
    assert again.status_code == 409

    bad_code = client.post("/api/v1/groups/join", headers=joiner_headers, json={"code": "NOPE12"})
    assert bad_code.status_code == 422


def test_public_groups_appear_in_discovery_for_non_members_only(client: TestClient) -> None:
    owner = register(client, "owner4@example.com", "owner4", "Owner Four")
    other = register(client, "other4@example.com", "other4", "Other User")
    create_group(client, auth_headers(owner["tokens"]), name="Open Algorithms Group")

    discovered = client.get("/api/v1/groups/discover", headers=auth_headers(other["tokens"]))
    assert discovered.status_code == 200
    assert [g["name"] for g in discovered.json()["items"]] == ["Open Algorithms Group"]

    # The owner is a member, so their own group is not suggested back to them.
    own = client.get("/api/v1/groups/discover", headers=auth_headers(owner["tokens"]))
    assert own.json()["items"] == []


def test_member_cannot_change_settings_but_owner_can(client: TestClient) -> None:
    owner = register(client, "owner5@example.com", "owner5", "Owner Five")
    member = register(client, "member5@example.com", "member5", "Member Five")
    group = create_group(client, auth_headers(owner["tokens"]))
    member_headers = auth_headers(member["tokens"])
    client.post("/api/v1/groups/join", headers=member_headers, json={"code": group["join_code"]})

    forbidden = client.patch(
        f"/api/v1/groups/{group['id']}", headers=member_headers, json={"description": "Changed"}
    )
    assert forbidden.status_code == 403

    allowed = client.patch(
        f"/api/v1/groups/{group['id']}",
        headers=auth_headers(owner["tokens"]),
        json={"description": "Owner changed this."},
    )
    assert allowed.status_code == 200
    assert allowed.json()["description"] == "Owner changed this."


def test_leaving_transfers_ownership_and_last_member_closes_the_group(client: TestClient) -> None:
    owner = register(client, "owner6@example.com", "owner6", "Owner Six")
    member = register(client, "member6@example.com", "member6", "Member Six")
    group = create_group(client, auth_headers(owner["tokens"]))
    member_headers = auth_headers(member["tokens"])
    client.post("/api/v1/groups/join", headers=member_headers, json={"code": group["join_code"]})

    owner_headers = auth_headers(owner["tokens"])
    assert client.post(f"/api/v1/groups/{group['id']}/leave", headers=owner_headers).status_code == 204

    # The remaining member is promoted rather than leaving the group ownerless.
    after_transfer = client.get(f"/api/v1/groups/{group['id']}", headers=member_headers)
    assert after_transfer.status_code == 200
    assert after_transfer.json()["role"] == "OWNER"
    assert after_transfer.json()["owner_id"] == member["user"]["id"]

    # The last member leaving removes the group entirely.
    assert client.post(f"/api/v1/groups/{group['id']}/leave", headers=member_headers).status_code == 204
    assert client.get(f"/api/v1/groups/{group['id']}", headers=member_headers).status_code == 404
