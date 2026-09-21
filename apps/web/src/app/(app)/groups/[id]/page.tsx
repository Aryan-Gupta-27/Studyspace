"use client";

/**
 * Group workspace: one page holding chat, notes, files, projects and members
 * so members never leave the context they are working in (spec section 31).
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { ChatPanel } from "@/components/ChatPanel";
import { FilesPanel } from "@/components/FilesPanel";
import { NotesPanel } from "@/components/NotesPanel";
import {
  Avatar,
  Badge,
  Button,
  Card,
  Modal,
  SkeletonList,
  Tabs,
  ToastRegion,
  useToasts,
} from "@/components/ui";
import { apiRequest, type Group, type GroupMember, type Project } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { relativeTime } from "@/lib/format";

type TabId = "chat" | "notes" | "files" | "projects" | "members";

export default function GroupWorkspacePage() {
  const params = useParams<{ id: string }>();
  const groupId = params.id;
  const router = useRouter();
  const { user, withAuth } = useAuth();
  const { toasts, push } = useToasts();

  const [group, setGroup] = useState<Group | null>(null);
  const [members, setMembers] = useState<GroupMember[] | null>(null);
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [tab, setTab] = useState<TabId>("chat");
  const [error, setError] = useState<string | null>(null);
  const [leaveOpen, setLeaveOpen] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    try {
      const [groupData, memberData, projectData] = await Promise.all([
        withAuth((token) => apiRequest<Group>(`/groups/${groupId}`, { accessToken: token })),
        withAuth((token) => apiRequest<GroupMember[]>(`/groups/${groupId}/members`, { accessToken: token })),
        withAuth((token) =>
          apiRequest<{ items: Project[] }>(`/groups/${groupId}/projects`, { accessToken: token, query: { limit: 20 } }),
        ),
      ]);
      setGroup(groupData);
      setMembers(memberData);
      setProjects(projectData.items);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We couldn't load this group.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function leaveGroup() {
    setLeaving(true);
    try {
      await withAuth((token) =>
        apiRequest<void>(`/groups/${groupId}/leave`, { method: "POST", accessToken: token }),
      );
      push("success", "You left the group.");
      router.replace("/groups");
    } catch (caught) {
      push("error", caught instanceof Error ? caught.message : "We couldn't remove you from that group.");
    } finally {
      setLeaving(false);
      setLeaveOpen(false);
    }
  }

  async function copyCode() {
    if (!group) return;
    try {
      await navigator.clipboard.writeText(group.join_code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      push("error", "We couldn't copy the code. Select it and copy manually.");
    }
  }

  if (error) {
    return (
      <div className="page">
        <div className="alert alert-error" role="alert">
          {error}
        </div>
        <Link href="/groups" className="btn btn-secondary">
          Back to groups
        </Link>
      </div>
    );
  }

  const role = group?.role ?? "MEMBER";
  const canManage = role === "OWNER" || role === "ADMIN";

  return (
    <div className="page">
      {!group ? (
        <SkeletonList rows={3} height={22} />
      ) : (
        <>
          <header className="page-header">
            <div className="page-header-text">
              <div className="row" style={{ gap: "var(--space-3)" }}>
                <Avatar name={group.name} large />
                <div>
                  <h1 className="page-title">{group.name}</h1>
                  <p className="page-subtitle">
                    {group.member_count} {group.member_count === 1 ? "member" : "members"} ·{" "}
                    {group.is_public ? "Public" : "Private"}
                  </p>
                </div>
              </div>
              {group.description && (
                <p className="small muted" style={{ marginTop: "var(--space-3)" }}>
                  {group.description}
                </p>
              )}
            </div>
            <div className="page-actions">
              <Badge tone={canManage ? "primary" : "default"}>{group.role}</Badge>
              <Button variant="secondary" size="sm" onClick={copyCode}>
                {copied ? "Code copied" : `Invite code ${group.join_code}`}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setLeaveOpen(true)}>
                Leave group
              </Button>
            </div>
          </header>

          <Tabs<TabId>
            tabs={[
              { id: "chat", label: "Chat" },
              { id: "notes", label: "Notes" },
              { id: "files", label: "Files" },
              { id: "projects", label: "Projects", badge: projects?.length },
              { id: "members", label: "Members", badge: members?.length },
            ]}
            active={tab}
            onChange={setTab}
          />

          {tab === "chat" && <ChatPanel groupId={groupId} />}

          {tab === "notes" && <NotesPanel groupId={groupId} />}

          {tab === "files" && <FilesPanel groupId={groupId} />}

          {tab === "projects" && (
            <div>
              <div className="row row-between" style={{ marginBottom: "var(--space-4)" }}>
                <p className="small muted" style={{ margin: 0 }}>
                  Projects belong to this group and carry their own task board.
                </p>
                <Link href="/projects" className="btn btn-primary btn-sm">
                  Open projects
                </Link>
              </div>
              {projects === null && <SkeletonList rows={2} height={18} />}
              {projects && projects.length === 0 && (
                <div className="empty-state">
                  <div className="empty-icon" aria-hidden="true">
                    ▤
                  </div>
                  <h3 className="empty-title">No projects yet</h3>
                  <p className="empty-text">
                    Create a project to plan work, assign tasks and track progress on a board.
                  </p>
                  <Link href="/projects" className="btn btn-primary">
                    Create a project
                  </Link>
                </div>
              )}
              {projects && projects.length > 0 && (
                <div className="grid grid-2">
                  {projects.map((project) => (
                    <Card key={project.id} hover>
                      <div className="row row-between">
                        <h3 className="card-title" style={{ margin: 0 }}>
                          {project.name}
                        </h3>
                        <Badge tone={project.status === "COMPLETED" ? "success" : "primary"}>
                          {project.status.replace("_", " ")}
                        </Badge>
                      </div>
                      <p className="card-meta" style={{ marginTop: "var(--space-2)" }}>
                        {project.description || "No description."}
                      </p>
                      <div className="row" style={{ marginTop: "var(--space-4)" }}>
                        <Link href={`/projects/${project.id}`} className="btn btn-outline btn-sm">
                          Open board
                        </Link>
                        <span className="caption">
                          {Object.values(project.task_counts).reduce((a, b) => a + b, 0)} tasks
                        </span>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}

          {tab === "members" && (
            <Card>
              {members === null && <SkeletonList rows={3} height={18} />}
              {members?.map((member) => (
                <div key={member.user_id} className="list-item">
                  <Avatar name={member.full_name} />
                  <div className="list-item-main">
                    <div className="list-item-title">{member.full_name}</div>
                    <div className="list-item-sub">
                      @{member.username} · joined {relativeTime(member.joined_at)}
                    </div>
                  </div>
                  <Badge tone={member.role === "MEMBER" ? "default" : "primary"}>{member.role}</Badge>
                  {member.user_id === user?.id && <Badge>You</Badge>}
                </div>
              ))}
            </Card>
          )}
        </>
      )}

      {leaveOpen && (
        <Modal
          title="Leave this group?"
          onClose={() => setLeaveOpen(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setLeaveOpen(false)}>
                Cancel
              </Button>
              <Button variant="danger" loading={leaving} onClick={leaveGroup}>
                Leave group
              </Button>
            </>
          }
        >
          <p className="small muted" style={{ margin: 0 }}>
            {group?.role === "OWNER" && (group?.member_count ?? 0) > 1
              ? "You are the owner. Leaving will hand ownership to another member."
              : "You will lose access to this group's chat, notes, files and projects."}
          </p>
        </Modal>
      )}

      <ToastRegion toasts={toasts} />
    </div>
  );
}
