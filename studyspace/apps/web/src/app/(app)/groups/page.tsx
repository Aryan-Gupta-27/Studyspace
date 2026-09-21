"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import {
  Avatar,
  Badge,
  Button,
  Card,
  EmptyState,
  Modal,
  PageHeader,
  SkeletonList,
  Tabs,
  Textarea,
} from "@/components/ui";
import { ApiError, apiRequest, type Group, type GroupSummary } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type TabId = "mine" | "discover";

export default function GroupsPage() {
  const { withAuth, ready } = useAuth();
  const [tab, setTab] = useState<TabId>("mine");
  const [groups, setGroups] = useState<Group[] | null>(null);
  const [discover, setDiscover] = useState<GroupSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [joinOpen, setJoinOpen] = useState(false);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isPublic, setIsPublic] = useState(true);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const [joinCode, setJoinCode] = useState("");
  const [joining, setJoining] = useState(false);
  const [joinError, setJoinError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [mine, found] = await Promise.all([
        withAuth((token) => apiRequest<{ items: Group[] }>("/groups", { accessToken: token, query: { limit: 50 } })),
        withAuth((token) =>
          apiRequest<{ items: GroupSummary[] }>("/groups/discover", { accessToken: token, query: { limit: 50 } }),
        ),
      ]);
      setGroups(mine.items);
      setDiscover(found.items);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We couldn't load your groups.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);

  useEffect(() => {
    if (ready) void load();
  }, [ready, load]);

  async function createGroup(event: FormEvent) {
    event.preventDefault();
    setCreating(true);
    setCreateError(null);
    try {
      await withAuth((token) =>
        apiRequest<Group>("/groups", {
          method: "POST",
          body: { name: name.trim(), description: description.trim(), is_public: isPublic },
          accessToken: token,
        }),
      );
      setCreateOpen(false);
      setName("");
      setDescription("");
      await load();
    } catch (caught) {
      setCreateError(
        caught instanceof ApiError ? caught.message : "We couldn't create that group. Please try again.",
      );
    } finally {
      setCreating(false);
    }
  }

  async function joinGroup(event: FormEvent) {
    event.preventDefault();
    setJoining(true);
    setJoinError(null);
    try {
      await withAuth((token) =>
        apiRequest<Group>("/groups/join", {
          method: "POST",
          body: { code: joinCode.trim().toUpperCase() },
          accessToken: token,
        }),
      );
      setJoinOpen(false);
      setJoinCode("");
      await load();
    } catch (caught) {
      setJoinError(caught instanceof ApiError ? caught.message : "We couldn't join that group.");
    } finally {
      setJoining(false);
    }
  }

  return (
    <div className="page">
      <PageHeader
        title="Groups"
        subtitle="Study groups become mini-workspaces with chat, files, notes and projects."
        actions={
          <>
            <Button variant="secondary" onClick={() => setJoinOpen(true)}>
              Join with code
            </Button>
            <Button onClick={() => setCreateOpen(true)}>+ Create group</Button>
          </>
        }
      />

      {error && (
        <div className="alert alert-error" role="alert">
          {error} <Button variant="ghost" size="sm" onClick={load}>Try again</Button>
        </div>
      )}

      <Tabs<TabId>
        tabs={[
          { id: "mine", label: "My groups", badge: groups?.length },
          { id: "discover", label: "Discover", badge: discover?.length },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === "mine" && (
        <>
          {groups === null && <SkeletonList rows={4} height={18} />}
          {groups && groups.length === 0 && (
            <EmptyState
              icon="◍"
              title="You haven't joined any groups"
              description="Create a group for your class or project team, or join one with an invite code from a classmate."
              action={<Button onClick={() => setCreateOpen(true)}>Create your first group</Button>}
            />
          )}
          {groups && groups.length > 0 && (
            <div className="grid grid-2">
              {groups.map((group) => (
                <Card key={group.id} hover>
                  <div className="row" style={{ marginBottom: "var(--space-3)" }}>
                    <Avatar name={group.name} />
                    <div className="list-item-main">
                      <Link href={`/groups/${group.id}`} className="list-item-title">
                        {group.name}
                      </Link>
                      <div className="list-item-sub">
                        {group.member_count} {group.member_count === 1 ? "member" : "members"}
                      </div>
                    </div>
                    {group.unread_count > 0 && <Badge tone="primary">{group.unread_count} new</Badge>}
                  </div>
                  <p className="small muted">{group.description || "No description yet."}</p>
                  <div className="row" style={{ justifyContent: "space-between" }}>
                    <Badge tone={group.role === "MEMBER" ? "default" : "primary"}>{group.role}</Badge>
                    <span className="caption">
                      Invite code <span className="mono">{group.join_code}</span>
                    </span>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {tab === "discover" && (
        <>
          {discover === null && <SkeletonList rows={3} height={18} />}
          {discover && discover.length === 0 && (
            <EmptyState
              icon="◎"
              title="No new public groups"
              description="Public groups you are not a member of will appear here so you can join them."
            />
          )}
          {discover && discover.length > 0 && (
            <div className="grid grid-2">
              {discover.map((group) => (
                <Card key={group.id} hover>
                  <div className="row" style={{ marginBottom: "var(--space-3)" }}>
                    <Avatar name={group.name} />
                    <div className="list-item-main">
                      <div className="list-item-title">{group.name}</div>
                      <div className="list-item-sub">{group.member_count} members</div>
                    </div>
                  </div>
                  <p className="small muted">{group.description || "No description yet."}</p>
                  <div className="row row-between">
                    <span className="caption">
                      Code <span className="mono">{group.join_code}</span>
                    </span>
                    <Button
                      size="sm"
                      onClick={async () => {
                        try {
                          await withAuth((token) =>
                            apiRequest<Group>("/groups/join", {
                              method: "POST",
                              body: { code: group.join_code },
                              accessToken: token,
                            }),
                          );
                          await load();
                        } catch (caught) {
                          setError(caught instanceof Error ? caught.message : "We couldn't join that group.");
                        }
                      }}
                    >
                      Join group
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {createOpen && (
        <Modal
          title="Create a group"
          onClose={() => setCreateOpen(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setCreateOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" form="create-group-form" loading={creating} disabled={name.trim().length < 3}>
                Create group
              </Button>
            </>
          }
        >
          <form id="create-group-form" onSubmit={createGroup}>
            {createError && (
              <div className="alert alert-error" role="alert">
                {createError}
              </div>
            )}
            <label className="field">
              <span className="field-label">Group name *</span>
              <input
                className="input"
                value={name}
                onChange={(event) => setName(event.target.value)}
                minLength={3}
                maxLength={120}
                required
                autoFocus
                placeholder="Machine Learning Study Group"
              />
            </label>
            <Textarea
              label="Description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              maxLength={2000}
              placeholder="What is this group working on?"
            />
            <label className="row small" style={{ gap: "var(--space-2)" }}>
              <input
                type="checkbox"
                checked={isPublic}
                onChange={(event) => setIsPublic(event.target.checked)}
              />
              Public — anyone with the code can find and join this group
            </label>
          </form>
        </Modal>
      )}

      {joinOpen && (
        <Modal
          title="Join a group"
          onClose={() => setJoinOpen(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setJoinOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" form="join-group-form" loading={joining} disabled={joinCode.trim().length < 4}>
                Join group
              </Button>
            </>
          }
        >
          <form id="join-group-form" onSubmit={joinGroup}>
            {joinError && (
              <div className="alert alert-error" role="alert">
                {joinError}
              </div>
            )}
            <label className="field">
              <span className="field-label">Invite code *</span>
              <input
                className="input mono"
                value={joinCode}
                onChange={(event) => setJoinCode(event.target.value.toUpperCase())}
                maxLength={10}
                required
                autoFocus
                placeholder="ABC12345"
              />
              <span className="field-hint">Group admins can find the code on their group card.</span>
            </label>
          </form>
        </Modal>
      )}
    </div>
  );
}
