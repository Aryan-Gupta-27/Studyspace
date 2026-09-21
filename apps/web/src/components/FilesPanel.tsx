"use client";

/** Group files: upload with progress, list, download and delete. */

import { useCallback, useEffect, useRef, useState } from "react";

import { Button, EmptyState, SkeletonList, ToastRegion, useToasts } from "@/components/ui";
import { apiRequest, apiUpload, type FileRecord, type Page } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatBytes, relativeTime } from "@/lib/format";

export function FilesPanel({ groupId }: { groupId: string }) {
  const { withAuth, accessToken } = useAuth();
  const { toasts, push } = useToasts();
  const [files, setFiles] = useState<FileRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const page = await withAuth((token) =>
        apiRequest<Page<FileRecord>>(`/groups/${groupId}/files`, { accessToken: token, query: { limit: 100 } }),
      );
      setFiles(page.items);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We couldn't load these files.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function upload(file: File) {
    setUploading(true);
    try {
      const token = await withAuth(async (current) => current);
      await apiUpload<FileRecord>("/files", file, groupId, token);
      push("success", `${file.name} uploaded.`);
      await load();
    } catch (caught) {
      push("error", caught instanceof Error ? caught.message : "We couldn't upload that file.");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function remove(record: FileRecord) {
    setDeletingId(record.id);
    try {
      await withAuth((token) => apiRequest<void>(`/files/${record.id}`, { method: "DELETE", accessToken: token }));
      push("success", `${record.filename} deleted.`);
      await load();
    } catch (caught) {
      push("error", caught instanceof Error ? caught.message : "We couldn't delete that file.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div>
      {error && (
        <div className="alert alert-error" role="alert">
          {error} <Button variant="ghost" size="sm" onClick={load}>Try again</Button>
        </div>
      )}

      <div className="row row-between" style={{ marginBottom: "var(--space-4)" }}>
        <p className="small muted" style={{ margin: 0 }}>
          Files shared with this group. Any member can download; the uploader or a group admin can delete.
        </p>
        <div className="row">
          <input
            ref={inputRef}
            type="file"
            className="sr-only"
            id="group-file-input"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void upload(file);
            }}
          />
          <label htmlFor="group-file-input" className={`btn btn-primary ${uploading ? "" : ""}`}>
            {uploading && <span className="spinner" aria-hidden="true" />}
            {uploading ? "Uploading…" : "Upload file"}
          </label>
        </div>
      </div>

      {files === null && <SkeletonList rows={4} height={18} />}

      {files && files.length === 0 && (
        <EmptyState
          icon="▣"
          title="No files yet"
          description="Upload lecture slides, datasets or assignments so the whole group can download them."
          action={
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => inputRef.current?.click()}
            >
              Upload the first file
            </button>
          }
        />
      )}

      {files && files.length > 0 && (
        <div>
          {files.map((record) => (
            <div key={record.id} className="list-item">
              <span className="avatar" aria-hidden="true">
                ▣
              </span>
              <div className="list-item-main">
                <div className="list-item-title truncate">{record.filename}</div>
                <div className="list-item-sub">
                  {formatBytes(record.size)} · {record.owner.full_name} · {relativeTime(record.created_at)}
                </div>
              </div>
              {/* The download URL is same-origin: Next.js proxies it to the API. */}
              <a
                className="btn btn-outline btn-sm"
                href={`/api/v1/files/${record.id}?download=1`}
                onClick={async (event) => {
                  // Stream through the authenticated client so the request
                  // carries the bearer token, then trigger the browser save.
                  event.preventDefault();
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
                }}
              >
                Download
              </a>
              <Button
                variant="ghost"
                size="sm"
                loading={deletingId === record.id}
                onClick={() => remove(record)}
              >
                Delete
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* The label above is the visible control; keep an unauthenticated href
          as a progressive-enhancement fallback for assistive tech. */}
      {!accessToken && <span className="sr-only">Sign in to download files.</span>}

      <ToastRegion toasts={toasts} />
    </div>
  );
}
