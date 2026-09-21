"use client";

/**
 * Personal dashboard: the command centre described in design spec section 26.
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  Avatar,
  Badge,
  Button,
  Card,
  EmptyState,
  Modal,
  PageHeader,
  SkeletonList,
} from "@/components/ui";
import { apiRequest, type Group, type GroupSummary, type Note, type Project } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { relativeTime } from "@/lib/format";

interface DashboardData {
  groups: Group[];
  notes: Note[];
  projects: Project[];
  discover: GroupSummary[];
}

export default function DashboardPage() {
  const { user, withAuth, ready } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [joinOpen, setJoinOpen] = useState(false);
  const [joinCode, setJoinCode] = useState("");
  const [joining, setJoining] = useState(false);
  const [joinError, setJoinError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [groups, notes, discover] = await Promise.all([
        withAuth((token) => apiRequest<{ items: Group[] }>("/groups", { accessToken: token, query: { limit: 20 } })),
        withAuth((token) => apiRequest<{ items: Note[] }>("/notes", { accessToken: token, query: { limit: 6 } })),
        withAuth((token) =>
          apiRequest<{ items: GroupSummary[] }>("/groups/discover", { accessToken: token, query: { limit: 3 } }),
        ),
      ]);

      // Projects live inside groups, so the dashboard collects them from each
      // group the user belongs to.
      const projectLists = await Promise.all(
        groups.items.map((group) =>
          withAuth((token) =>
            apiRequest<{ items: Project[] }>(`/groups/${group.id}/projects`, {
              accessToken: token,
              query: { limit: 5 },
            }),
          ).catch(() => ({ items: [] as Project[], total: 0, limit: 5, offset: 0 })),
        ),
      );

      setData({
        groups: groups.items,
        notes: notes.items,
        projects: projectLists.flatMap((page) => page.items),
        discover: discover.items,
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We couldn't load your dashboard.");
    } finally {
      setLoading(false);
    }
    // `withAuth` changes identity each render; depending on it would loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);

  useEffect(() => {
    if (ready) void load();
  }, [ready, load]);

  async function joinGroup(event: React.FormEvent) {
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
      setJoinError(caught instanceof Error ? caught.message : "We couldn't join that group.");
    } finally {
      setJoining(false);
    }
  }

  const firstName = user?.full_name.split(" ")[0] ?? "there";
  const unread = data?.groups.reduce((total, group) => total + group.unread_count, 0) ?? 0;

  return (
    <div className="page">
      <PageHeader
        title={`Good to see you, ${firstName}`}
        subtitle="Your groups, recent notes and active projects in one place."
        actions={
          <>
            <Button variant="secondary" onClick={() => setJoinOpen(true)}>
              Join with code
            </Button>
            <Link href="/groups" className="btn btn-primary">
              New group
            </Link>
          </>
        }
      />

      {error && (
        <div className="alert alert-error" role="alert">
          {error} <Button variant="ghost" size="sm" onClick={load}>Try again</Button>
        </div>
      )}

      <section className="stat-grid" aria-label="Summary">
        <div className="stat">
          <div className="stat-value">{loading ? "—" : (data?.groups.length ?? 0)}</div>
          <div className="stat-label">Groups</div>
        </div>
        <div className="stat">
          <div className="stat-value">{loading ? "—" : (data?.projects.length ?? 0)}</div>
          <div className="stat-label">Projects</div>
        </div>
        <div className="stat">
          <div className="stat-value">{loading ? "—" : (data?.notes.length ?? 0)}</div>
          <div className="stat-label">Recent notes</div>
        </div>
        <div className="stat">
          <div className="stat-value">{loading ? "—" : unread}</div>
          <div className="stat-label">Unread</div>
        </div>
      </section>

      <div className="grid grid-2">
        <Card>
          <div className="row row-between" style={{ marginBottom: "var(--space-4)" }}>
            <h2 className="card-title" style={{ margin: 0 }}>
              Your groups
            </h2>
            <Link href="/groups" className="small">
              View all
            </Link>
          </div>

          {loading && <SkeletonList rows={3} />}

          {!loading && data && data.groups.length === 0 && (
            <EmptyState
              icon="◍"
              title="No groups yet"
              description="Create a study group for your class or join one with an invite code."
              action={
                <Link href="/groups" className="btn btn-primary btn-sm">
                  Create a group
                </Link>
              }
            />
          )}

          {!loading &&
            data?.groups.map((group) => (
              <div key={group.id} className="list-item">
                <Avatar name={group.name} />
                <div className="list-item-main">
                  <Link href={`/groups/${group.id}`} className="list-item-title">
                    {group.name}
                  </Link>
                  <div className="list-item-sub">
                    {group.member_count} {group.member_count === 1 ? "member" : "members"} · {group.role}
                  </div>
                </div>
                {group.unread_count > 0 && <Badge tone="primary">{group.unread_count} new</Badge>}
              </div>
            ))}
        </Card>

        <div className="stack">
          <Card>
            <div className="row row-between" style={{ marginBottom: "var(--space-4)" }}>
              <h2 className="card-title" style={{ margin: 0 }}>
                Recent notes
              </h2>
              <Link href="/notes" className="small">
                View all
              </Link>
            </div>

            {loading && <SkeletonList rows={3} />}

            {!loading && data && data.notes.length === 0 && (
              <p className="small muted" style={{ margin: 0 }}>
                No notes yet. <Link href="/notes">Write your first note</Link>.
              </p>
            )}

            {!loading &&
              data?.notes.map((note) => (
                <div key={note.id} className="list-item">
                  <div className="list-item-main">
                    <Link href={`/notes?note=${note.id}`} className="list-item-title">
                      {note.title}
                    </Link>
                    <div className="list-item-sub">
                      {note.group_id ? "Group note" : "Private"} · updated {relativeTime(note.updated_at)}
                    </div>
                  </div>
                </div>
              ))}
          </Card>

          <Card>
            <h2 className="card-title">Discover groups</h2>
            {loading && <SkeletonList rows={2} />}
            {!loading && data && data.discover.length === 0 && (
              <p className="small muted" style={{ margin: 0 }}>
                No public groups to suggest right now.
              </p>
            )}
            {!loading &&
              data?.discover.map((group) => (
                <div key={group.id} className="list-item">
                  <Avatar name={group.name} />
                  <div className="list-item-main">
                    <div className="list-item-title">{group.name}</div>
                    <div className="list-item-sub">
                      {group.member_count} members · code <span className="mono">{group.join_code}</span>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
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
                      } catch {
                        setError("We couldn't join that group.");
                      }
                    }}
                  >
                    Join
                  </Button>
                </div>
              ))}
          </Card>
        </div>
      </div>

      {joinOpen && (
        <Modal title="Join a group" onClose={() => setJoinOpen(false)}>
          <form onSubmit={joinGroup}>
            {joinError && (
              <div className="alert alert-error" role="alert">
                {joinError}
              </div>
            )}
            <label className="field">
              <span className="field-label">Invite code</span>
              <input
                className="input mono"
                value={joinCode}
                onChange={(event) => setJoinCode(event.target.value.toUpperCase())}
                placeholder="ABC12345"
                maxLength={10}
                required
                autoFocus
              />
              <span className="field-hint">Ask a group member for their invite code.</span>
            </label>
            <div className="modal-footer">
              <Button variant="secondary" onClick={() => setJoinOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" loading={joining} disabled={joinCode.trim().length < 4}>
                Join group
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
