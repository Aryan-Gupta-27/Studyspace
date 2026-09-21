"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import {
  Badge,
  Button,
  Card,
  EmptyState,
  Modal,
  PageHeader,
  Select,
  SkeletonList,
  Textarea,
  ToastRegion,
  useToasts,
} from "@/components/ui";
import { ApiError, apiRequest, type Group, type Project, type ProjectStatus } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDay } from "@/lib/format";

export default function ProjectsPage() {
  const { withAuth, ready } = useAuth();
  const { toasts, push } = useToasts();
  const [groups, setGroups] = useState<Group[] | null>(null);
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [groupId, setGroupId] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<ProjectStatus>("PLANNING");
  const [deadline, setDeadline] = useState("");

  const load = useCallback(async () => {
    setError(null);
    try {
      const groupPage = await withAuth((token) =>
        apiRequest<{ items: Group[] }>("/groups", { accessToken: token, query: { limit: 50 } }),
      );
      setGroups(groupPage.items);
      setGroupId((current) => current || groupPage.items[0]?.id || "");

      const lists = await Promise.all(
        groupPage.items.map((group) =>
          withAuth((token) =>
            apiRequest<{ items: Project[] }>(`/groups/${group.id}/projects`, {
              accessToken: token,
              query: { limit: 50 },
            }),
          ).catch(() => ({ items: [] as Project[], total: 0, limit: 50, offset: 0 })),
        ),
      );
      setProjects(lists.flatMap((page) => page.items));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We couldn't load your projects.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);

  useEffect(() => {
    if (ready) void load();
  }, [ready, load]);

  async function createProject(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setFormError(null);
    try {
      await withAuth((token) =>
        apiRequest<Project>(`/groups/${groupId}/projects`, {
          method: "POST",
          body: {
            name: name.trim(),
            description: description.trim(),
            status,
            deadline: deadline || null,
          },
          accessToken: token,
        }),
      );
      setCreateOpen(false);
      setName("");
      setDescription("");
      setDeadline("");
      push("success", "Project created.");
      await load();
    } catch (caught) {
      setFormError(caught instanceof ApiError ? caught.message : "We couldn't create that project.");
    } finally {
      setSaving(false);
    }
  }

  const noGroups = groups !== null && groups.length === 0;

  return (
    <div className="page">
      <PageHeader
        title="Projects"
        subtitle="Plan group work with tasks, priorities and a four-column board."
        actions={
          <Button onClick={() => setCreateOpen(true)} disabled={noGroups}>
            + New project
          </Button>
        }
      />

      {error && (
        <div className="alert alert-error" role="alert">
          {error} <Button variant="ghost" size="sm" onClick={load}>Try again</Button>
        </div>
      )}

      {noGroups && (
        <EmptyState
          icon="◍"
          title="Join a group first"
          description="Projects belong to a group. Create or join a group, then add a project for the work you are doing together."
          action={
            <Link href="/groups" className="btn btn-primary">
              Go to groups
            </Link>
          }
        />
      )}

      {!noGroups && projects === null && <SkeletonList rows={3} height={20} />}

      {!noGroups && projects && projects.length === 0 && (
        <EmptyState
          icon="▤"
          title="No projects yet"
          description="Create a project to plan assignments, research or builds, then track tasks on a board."
          action={<Button onClick={() => setCreateOpen(true)}>Create your first project</Button>}
        />
      )}

      {projects && projects.length > 0 && (
        <div className="grid grid-2">
          {projects.map((project) => {
            const total = Object.values(project.task_counts).reduce((a, b) => a + b, 0);
            const done = project.task_counts.DONE ?? 0;
            const percent = total === 0 ? 0 : Math.round((done / total) * 100);
            return (
              <Card key={project.id} hover>
                <div className="row row-between" style={{ marginBottom: "var(--space-2)" }}>
                  <h2 className="card-title" style={{ margin: 0 }}>
                    {project.name}
                  </h2>
                  <Badge tone={project.status === "COMPLETED" ? "success" : "primary"}>
                    {project.status.replace("_", " ")}
                  </Badge>
                </div>
                <p className="card-meta">{project.description || "No description."}</p>

                <div
                  role="progressbar"
                  aria-valuenow={percent}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={`${project.name} progress`}
                  style={{
                    height: 6,
                    background: "var(--color-surface-2)",
                    borderRadius: "var(--radius-pill)",
                    margin: "var(--space-4) 0 var(--space-2)",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${percent}%`,
                      height: "100%",
                      background: "var(--color-primary)",
                      borderRadius: "var(--radius-pill)",
                    }}
                  />
                </div>

                <div className="row row-between">
                  <span className="caption">
                    {done}/{total} tasks done
                    {project.deadline ? ` · due ${formatDay(project.deadline)}` : ""}
                  </span>
                  <Link href={`/projects/${project.id}`} className="btn btn-outline btn-sm">
                    Open board
                  </Link>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {createOpen && (
        <Modal
          title="New project"
          onClose={() => setCreateOpen(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setCreateOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                form="project-create-form"
                loading={saving}
                disabled={!name.trim() || !groupId}
              >
                Create project
              </Button>
            </>
          }
        >
          <form id="project-create-form" onSubmit={createProject}>
            {formError && (
              <div className="alert alert-error" role="alert">
                {formError}
              </div>
            )}
            <Select
              label="Group *"
              value={groupId}
              onChange={(event) => setGroupId(event.target.value)}
              options={(groups ?? []).map((group) => ({ value: group.id, label: group.name }))}
            />
            <label className="field">
              <span className="field-label">Project name *</span>
              <input
                className="input"
                value={name}
                onChange={(event) => setName(event.target.value)}
                minLength={3}
                maxLength={120}
                required
                autoFocus
              />
            </label>
            <Textarea
              label="Description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              maxLength={2000}
            />
            <Select
              label="Status"
              value={status}
              onChange={(event) => setStatus(event.target.value as ProjectStatus)}
              options={[
                { value: "PLANNING", label: "Planning" },
                { value: "ACTIVE", label: "Active" },
                { value: "ON_HOLD", label: "On hold" },
                { value: "COMPLETED", label: "Completed" },
              ]}
            />
            <label className="field">
              <span className="field-label">Deadline</span>
              <input
                className="input"
                type="date"
                value={deadline}
                onChange={(event) => setDeadline(event.target.value)}
              />
            </label>
          </form>
        </Modal>
      )}

      <ToastRegion toasts={toasts} />
    </div>
  );
}
