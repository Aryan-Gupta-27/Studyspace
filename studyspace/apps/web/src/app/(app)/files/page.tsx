"use client";

/** All files the signed-in user owns or can see through their groups. */

import { useCallback, useEffect, useRef, useState } from "react";

import {
  Button,
  EmptyState,
  PageHeader,
  SkeletonList,
  ToastRegion,
  useToasts,
} from "@/components/ui";
import { apiRequest, apiUpload, type FileRecord, type Group, type Page } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatBytes, relativeTime } from "@/lib/format";

export default function FilesPage() {
  const { withAuth, ready } = useAuth();
  const { toasts, push } = useToasts();
  const [files, setFiles] = useState<FileRecord[] | null>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [groupId, setGroupId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const [page, groupPage] = await Promise.all([
        withAuth((token) =>
          apiRequest<Page<FileRecord>>("/files", { accessToken: token, query: { limit: 100 } }),
        ),
        withAuth((token) => apiRequest<{ items: Group[] }>("/groups", { accessToken: token, query: { limit: 50 } })),
      ]);
      setFiles(page.items);
      setGroups(groupPage.items);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We couldn't load your files.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);

  useEffect(() => {
    if (ready) void load();
  }, [ready, load]);

  async function upload(file: File) {
    setUploading(true);
    try {
      const token = await withAuth(async (current) => current);
      await apiUpload<FileRecord>("/files", file, groupId || null, token);
      push("success", `${file.name} uploaded.`);
      await load();
    } catch (caught) {
      push("error", caught instanceof Error ? caught.message : "We couldn't upload that file.");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function download(record: FileRecord) {
    try {
      const token = await withAuth(async (current) => current);
      const response = await fetch(`/api/v1/files/${record.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("download failed");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = record.filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      push("error", "We couldn't download that file.");
    }
  }

  async function remove(record: FileRecord) {
    try {
      await withAuth((token) => apiRequest<void>(`/files/${record.id}`, { method: "DELETE", accessToken: token }));
      push("success", `${record.filename} deleted.`);
      await load();
    } catch (caught) {
      push("error", caught instanceof Error ? caught.message : "We couldn't delete that file.");
    }
  }

  return (
    <div className="page">
      <PageHeader
        title="Files"
        subtitle="Your private uploads plus everything shared in your groups."
        actions={
          <>
            <select
              className="select"
              style={{ width: "auto" }}
              value={groupId}
              onChange={(event) => setGroupId(event.target.value)}
              aria-label="Upload destination"
            >
              <option value="">Upload to: private</option>
              {groups.map((group) => (
                <option key={group.id} value={group.id}>
                  Upload to: {group.name}
                </option>
              ))}
            </select>
            <input
              ref={inputRef}
              id="file-input"
              type="file"
              className="sr-only"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void upload(file);
              }}
            />
            <label htmlFor="file-input" className="btn btn-primary">
              {uploading && <span className="spinner" aria-hidden="true" />}
              {uploading ? "Uploading…" : "Upload file"}
            </label>
          </>
        }
      />

      {error && (
        <div className="alert alert-error" role="alert">
          {error} <Button variant="ghost" size="sm" onClick={load}>Try again</Button>
        </div>
      )}

      {files === null && <SkeletonList rows={4} height={18} />}

      {files && files.length === 0 && (
        <EmptyState
          icon="▣"
          title="No files yet"
          description="Upload lecture notes, datasets, slides or assignments. Files stay private unless you share them with a group."
          action={
            <button type="button" className="btn btn-primary" onClick={() => inputRef.current?.click()}>
              Upload your first file
            </button>
          }
        />
      )}

      {files && files.length > 0 && (
        <div className="card" style={{ padding: 0 }}>
          <div style={{ padding: "var(--space-5) var(--space-5) 0" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <caption className="sr-only">Your files</caption>
              <thead>
                <tr style={{ textAlign: "left" }}>
                  <th scope="col" className="caption" style={{ paddingBottom: 8 }}>Name</th>
                  <th scope="col" className="caption" style={{ paddingBottom: 8 }}>Size</th>
                  <th scope="col" className="caption" style={{ paddingBottom: 8 }}>Owner</th>
                  <th scope="col" className="caption" style={{ paddingBottom: 8 }}>Added</th>
                  <th scope="col" className="caption" style={{ paddingBottom: 8 }}>
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {files.map((record) => (
                  <tr key={record.id} style={{ borderTop: "1px solid var(--color-border)" }}>
                    <td style={{ padding: "12px 0" }}>
                      <span className="list-item-title">{record.filename}</span>
                      <div className="caption">{record.group_id ? "Shared with a group" : "Private"}</div>
                    </td>
                    <td className="small muted">{formatBytes(record.size)}</td>
                    <td className="small muted">{record.owner.full_name}</td>
                    <td className="small muted">{relativeTime(record.created_at)}</td>
                    <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                      <Button variant="ghost" size="sm" onClick={() => download(record)}>
                        Download
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => remove(record)}>
                        Delete
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ height: "var(--space-5)" }} />
        </div>
      )}

      <ToastRegion toasts={toasts} />
    </div>
  );
}
