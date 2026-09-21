"use client";

/** Kanban board with the four statuses required by milestone 6. */

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { Badge, Button, Modal, Select, Textarea, ToastRegion, useToasts } from "@/components/ui";
import {
  TASK_COLUMNS,
  TASK_COLUMN_LABELS,
  apiRequest,
  type GroupMember,
  type Task,
  type TaskPriority,
  type TaskStatus,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDay } from "@/lib/format";

const PRIORITY_TONE: Record<TaskPriority, "default" | "info" | "warning" | "danger"> = {
  LOW: "default",
  MEDIUM: "info",
  HIGH: "warning",
  URGENT: "danger",
};

export function ProjectBoard({
  projectId,
  groupId,
}: {
  projectId: string;
  groupId: string;
}) {
  const { withAuth } = useAuth();
  const { toasts, push } = useToasts();
  const [board, setBoard] = useState<Record<string, Task[]> | null>(null);
  const [members, setMembers] = useState<GroupMember[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [detail, setDetail] = useState<Task | null>(null);
  const [saving, setSaving] = useState(false);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<TaskPriority>("MEDIUM");
  const [assignee, setAssignee] = useState("");

  const load = useCallback(async () => {
    try {
      const [boardData, memberData] = await Promise.all([
        withAuth((token) =>
          apiRequest<Record<string, Task[]>>(`/projects/${projectId}/board`, { accessToken: token }),
        ),
        withAuth((token) => apiRequest<GroupMember[]>(`/groups/${groupId}/members`, { accessToken: token })),
      ]);
      setBoard(boardData);
      setMembers(memberData);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We couldn't load this board.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, groupId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function createTask(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await withAuth((token) =>
        apiRequest<Task>(`/projects/${projectId}/tasks`, {
          method: "POST",
          body: {
            title: title.trim(),
            description: description.trim(),
            priority,
            assignee_id: assignee || null,
          },
          accessToken: token,
        }),
      );
      setCreating(false);
      setTitle("");
      setDescription("");
      setAssignee("");
      setPriority("MEDIUM");
      push("success", "Task created.");
      await load();
    } catch (caught) {
      push("error", caught instanceof Error ? caught.message : "We couldn't create that task.");
    } finally {
      setSaving(false);
    }
  }

  async function move(task: Task, status: TaskStatus) {
    try {
      await withAuth((token) =>
        apiRequest<Task>(`/tasks/${task.id}/move`, {
          method: "POST",
          body: { status, position: 0 },
          accessToken: token,
        }),
      );
      await load();
    } catch (caught) {
      push("error", caught instanceof Error ? caught.message : "We couldn't move that task.");
    }
  }

  async function saveDetail() {
    if (!detail) return;
    setSaving(true);
    try {
      const updated = await withAuth((token) =>
        apiRequest<Task>(`/tasks/${detail.id}`, {
          method: "PATCH",
          body: {
            title: detail.title,
            description: detail.description,
            priority: detail.priority,
            assignee_id: detail.assignee?.id ?? null,
          },
          accessToken: token,
        }),
      );
      setDetail(updated);
      push("success", "Task updated.");
      await load();
    } catch (caught) {
      push("error", caught instanceof Error ? caught.message : "We couldn't update that task.");
    } finally {
      setSaving(false);
    }
  }

  async function remove(taskId: string) {
    try {
      await withAuth((token) => apiRequest<void>(`/tasks/${taskId}`, { method: "DELETE", accessToken: token }));
      setDetail(null);
      push("success", "Task deleted.");
      await load();
    } catch (caught) {
      push("error", caught instanceof Error ? caught.message : "We couldn't delete that task.");
    }
  }

  if (error) {
    return (
      <div className="alert alert-error" role="alert">
        {error} <Button variant="ghost" size="sm" onClick={load}>Try again</Button>
      </div>
    );
  }

  return (
    <div>
      <div className="row row-between" style={{ marginBottom: "var(--space-4)" }}>
        <p className="small muted" style={{ margin: 0 }}>
          Move tasks between columns as work progresses. Completion is recorded automatically.
        </p>
        <Button onClick={() => setCreating(true)}>+ Add task</Button>
      </div>

      {board === null && (
        <div className="stack">
          <div className="skeleton" style={{ height: 120 }} />
        </div>
      )}

      {board && (
        <div className="board">
          {TASK_COLUMNS.map((column) => (
            <section key={column} className="board-column" aria-label={TASK_COLUMN_LABELS[column]}>
              <div className="board-column-head">
                <span>{TASK_COLUMN_LABELS[column]}</span>
                <Badge>{board[column]?.length ?? 0}</Badge>
              </div>

              {(board[column] ?? []).length === 0 && (
                <p className="caption" style={{ margin: "var(--space-2) 0" }}>
                  Nothing here yet.
                </p>
              )}

              {(board[column] ?? []).map((task) => (
                <article key={task.id} className="task-card">
                  <button
                    type="button"
                    className="task-title"
                    style={{
                      background: "none",
                      border: "none",
                      padding: 0,
                      textAlign: "left",
                      cursor: "pointer",
                      color: "inherit",
                      font: "inherit",
                      fontWeight: 600,
                    }}
                    onClick={() => setDetail(task)}
                  >
                    {task.title}
                  </button>
                  <div className="row" style={{ gap: "var(--space-2)", marginBottom: "var(--space-2)" }}>
                    <Badge tone={PRIORITY_TONE[task.priority]}>{task.priority}</Badge>
                    {task.assignee && <span className="caption">{task.assignee.full_name}</span>}
                  </div>
                  {task.deadline && <div className="caption">Due {formatDay(task.deadline)}</div>}

                  {/* Move controls are buttons, never drag-only: drag-and-drop
                      must not be the only way to reach an action. */}
                  <div className="task-move" style={{ marginTop: "var(--space-2)" }}>
                    {TASK_COLUMNS.filter((target) => target !== column).map((target) => (
                      <Button
                        key={target}
                        size="sm"
                        variant="secondary"
                        onClick={() => move(task, target)}
                        aria-label={`Move ${task.title} to ${TASK_COLUMN_LABELS[target]}`}
                      >
                        → {TASK_COLUMN_LABELS[target]}
                      </Button>
                    ))}
                  </div>
                </article>
              ))}
            </section>
          ))}
        </div>
      )}

      {creating && (
        <Modal
          title="New task"
          onClose={() => setCreating(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setCreating(false)}>
                Cancel
              </Button>
              <Button type="submit" form="task-create-form" loading={saving} disabled={!title.trim()}>
                Create task
              </Button>
            </>
          }
        >
          <form id="task-create-form" onSubmit={createTask}>
            <label className="field">
              <span className="field-label">Title *</span>
              <input
                className="input"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={200}
                required
                autoFocus
              />
            </label>
            <Textarea
              label="Description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              maxLength={4000}
            />
            <Select
              label="Priority"
              value={priority}
              onChange={(event) => setPriority(event.target.value as TaskPriority)}
              options={[
                { value: "LOW", label: "Low" },
                { value: "MEDIUM", label: "Medium" },
                { value: "HIGH", label: "High" },
                { value: "URGENT", label: "Urgent" },
              ]}
            />
            <Select
              label="Assignee"
              value={assignee}
              onChange={(event) => setAssignee(event.target.value)}
              options={[
                { value: "", label: "Unassigned" },
                ...members.map((member) => ({
                  value: member.user_id,
                  label: `${member.full_name} (@${member.username})`,
                })),
              ]}
            />
          </form>
        </Modal>
      )}

      {detail && (
        <Modal
          title="Task details"
          onClose={() => setDetail(null)}
          footer={
            <>
              <Button variant="danger" onClick={() => remove(detail.id)}>
                Delete
              </Button>
              <Button variant="secondary" onClick={() => setDetail(null)}>
                Close
              </Button>
              <Button onClick={saveDetail} loading={saving}>
                Save changes
              </Button>
            </>
          }
        >
          <label className="field">
            <span className="field-label">Title</span>
            <input
              className="input"
              value={detail.title}
              onChange={(event) => setDetail({ ...detail, title: event.target.value })}
            />
          </label>
          <Textarea
            label="Description"
            value={detail.description}
            onChange={(event) => setDetail({ ...detail, description: event.target.value })}
          />
          <Select
            label="Priority"
            value={detail.priority}
            onChange={(event) => setDetail({ ...detail, priority: event.target.value as TaskPriority })}
            options={[
              { value: "LOW", label: "Low" },
              { value: "MEDIUM", label: "Medium" },
              { value: "HIGH", label: "High" },
              { value: "URGENT", label: "Urgent" },
            ]}
          />
          <Select
            label="Assignee"
            value={detail.assignee?.id ?? ""}
            onChange={(event) => {
              const next = members.find((member) => member.user_id === event.target.value);
              setDetail({
                ...detail,
                assignee: next
                  ? { id: next.user_id, username: next.username, full_name: next.full_name }
                  : null,
              });
            }}
            options={[
              { value: "", label: "Unassigned" },
              ...members.map((member) => ({
                value: member.user_id,
                label: `${member.full_name} (@${member.username})`,
              })),
            ]}
          />
          <p className="caption">
            Status {TASK_COLUMN_LABELS[detail.status]}
            {detail.completed_at ? ` · completed ${formatDay(detail.completed_at)}` : ""}
          </p>
        </Modal>
      )}

      <ToastRegion toasts={toasts} />
    </div>
  );
}
