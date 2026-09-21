"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { ProjectBoard } from "@/components/ProjectBoard";
import { Badge, Button, Modal, PageHeader, SkeletonList, ToastRegion, useToasts } from "@/components/ui";
import { apiRequest, type Project } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDay } from "@/lib/format";

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const router = useRouter();
  const { withAuth } = useAuth();
  const { toasts, push } = useToasts();

  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await withAuth((token) =>
        apiRequest<Project>(`/projects/${projectId}`, { accessToken: token }),
      );
      setProject(data);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We couldn't load this project.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function removeProject() {
    setDeleting(true);
    try {
      await withAuth((token) =>
        apiRequest<void>(`/projects/${projectId}`, { method: "DELETE", accessToken: token }),
      );
      push("success", "Project deleted.");
      router.replace("/projects");
    } catch (caught) {
      push("error", caught instanceof Error ? caught.message : "We couldn't delete that project.");
    } finally {
      setDeleting(false);
      setDeleteOpen(false);
    }
  }

  if (error) {
    return (
      <div className="page">
        <div className="alert alert-error" role="alert">
          {error}
        </div>
        <Link href="/projects" className="btn btn-secondary">
          Back to projects
        </Link>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="page">
        <SkeletonList rows={4} height={22} />
      </div>
    );
  }

  const total = Object.values(project.task_counts).reduce((a, b) => a + b, 0);

  return (
    <div className="page">
      <PageHeader
        title={project.name}
        subtitle={
          project.description ||
          "Track this project's tasks across to do, in progress, review and done."
        }
        actions={
          <>
            <Link href={`/groups/${project.group_id}`} className="btn btn-secondary">
              Group workspace
            </Link>
            <Button variant="ghost" onClick={() => setDeleteOpen(true)}>
              Delete
            </Button>
          </>
        }
      />

      <div className="stat-grid">
        <div className="stat">
          <div className="stat-value">{total}</div>
          <div className="stat-label">Tasks</div>
        </div>
        <div className="stat">
          <div className="stat-value">{project.task_counts.DONE ?? 0}</div>
          <div className="stat-label">Done</div>
        </div>
        <div className="stat">
          <div className="stat-value">{project.task_counts.IN_PROGRESS ?? 0}</div>
          <div className="stat-label">In progress</div>
        </div>
        <div className="stat">
          <div className="stat-value">
            <Badge tone={project.status === "COMPLETED" ? "success" : "primary"}>
              {project.status.replace("_", " ")}
            </Badge>
          </div>
          <div className="stat-label">Status</div>
        </div>
      </div>

      {project.deadline && (
        <p className="small muted">Deadline {formatDay(project.deadline)}</p>
      )}

      <ProjectBoard projectId={project.id} groupId={project.group_id} />

      {deleteOpen && (
        <Modal
          title="Delete this project?"
          onClose={() => setDeleteOpen(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setDeleteOpen(false)}>
                Cancel
              </Button>
              <Button variant="danger" loading={deleting} onClick={removeProject}>
                Delete project
              </Button>
            </>
          }
        >
          <p className="small muted" style={{ margin: 0 }}>
            This removes the project and every task on its board. This action cannot be undone.
          </p>
        </Modal>
      )}

      <ToastRegion toasts={toasts} />
    </div>
  );
}
