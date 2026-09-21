"use client";

/** Notes for a group: list, create, edit and delete (design spec section 45). */

import { useCallback, useEffect, useState, type FormEvent } from "react";

import {
  Button,
  EmptyState,
  Modal,
  SkeletonList,
  Textarea,
  ToastRegion,
  useToasts,
} from "@/components/ui";
import { apiRequest, type Note, type Page } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { relativeTime } from "@/lib/format";

export function NotesPanel({ groupId }: { groupId: string }) {
  const { withAuth } = useAuth();
  const { toasts, push } = useToasts();
  const [notes, setNotes] = useState<Note[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Note | null>(null);
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const page = await withAuth((token) =>
        apiRequest<Page<Note>>(`/groups/${groupId}/notes`, { accessToken: token, query: { limit: 50 } }),
      );
      setNotes(page.items);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We couldn't load these notes.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function createNote(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setFormError(null);
    try {
      const note = await withAuth((token) =>
        apiRequest<Note>("/notes", {
          method: "POST",
          body: { title: title.trim(), body, group_id: groupId },
          accessToken: token,
        }),
      );
      setCreating(false);
      setTitle("");
      setBody("");
      setSelected(note);
      push("success", "Note created.");
      await load();
    } catch (caught) {
      setFormError(caught instanceof Error ? caught.message : "We couldn't save that note.");
    } finally {
      setSaving(false);
    }
  }

  async function saveSelected() {
    if (!selected) return;
    setSaving(true);
    try {
      const updated = await withAuth((token) =>
        apiRequest<Note>(`/notes/${selected.id}`, {
          method: "PATCH",
          body: { title: selected.title, body: selected.body },
          accessToken: token,
        }),
      );
      setSelected(updated);
      push("success", "Note saved.");
      await load();
    } catch (caught) {
      push("error", caught instanceof Error ? caught.message : "We couldn't save that note.");
    } finally {
      setSaving(false);
    }
  }

  async function deleteNote(noteId: string) {
    try {
      await withAuth((token) => apiRequest<void>(`/notes/${noteId}`, { method: "DELETE", accessToken: token }));
      setSelected(null);
      push("success", "Note deleted.");
      await load();
    } catch (caught) {
      push("error", caught instanceof Error ? caught.message : "We couldn't delete that note.");
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
          Notes shared with this group. Anyone in the group can read and edit them.
        </p>
        <Button onClick={() => setCreating(true)}>+ New note</Button>
      </div>

      {notes === null && <SkeletonList rows={4} height={18} />}

      {notes && notes.length === 0 && (
        <EmptyState
          icon="✎"
          title="No notes yet"
          description="Capture lecture notes, revision summaries or meeting notes so the whole group can use them."
          action={<Button onClick={() => setCreating(true)}>Create the first note</Button>}
        />
      )}

      {notes && notes.length > 0 && (
        <div className="grid grid-2">
          {notes.map((note) => (
            <button
              key={note.id}
              type="button"
              className="card card-hover"
              style={{ textAlign: "left", cursor: "pointer" }}
              onClick={() => setSelected(note)}
            >
              <h3 className="card-title">{note.title}</h3>
              <p className="card-meta">{note.body.slice(0, 120) || "Empty note."}</p>
              <p className="caption" style={{ marginTop: "var(--space-3)", marginBottom: 0 }}>
                {note.owner.full_name} · updated {relativeTime(note.updated_at)}
              </p>
            </button>
          ))}
        </div>
      )}

      {creating && (
        <Modal
          title="New note"
          onClose={() => setCreating(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setCreating(false)}>
                Cancel
              </Button>
              <Button type="submit" form="note-create-form" loading={saving} disabled={!title.trim()}>
                Create note
              </Button>
            </>
          }
        >
          <form id="note-create-form" onSubmit={createNote}>
            {formError && (
              <div className="alert alert-error" role="alert">
                {formError}
              </div>
            )}
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
              label="Body"
              value={body}
              onChange={(event) => setBody(event.target.value)}
              placeholder="Markdown is supported."
            />
          </form>
        </Modal>
      )}

      {selected && (
        <Modal
          title="Edit note"
          onClose={() => setSelected(null)}
          footer={
            <>
              <Button variant="danger" onClick={() => deleteNote(selected.id)}>
                Delete
              </Button>
              <Button variant="secondary" onClick={() => setSelected(null)}>
                Close
              </Button>
              <Button onClick={saveSelected} loading={saving}>
                Save
              </Button>
            </>
          }
        >
          <label className="field">
            <span className="field-label">Title</span>
            <input
              className="input"
              value={selected.title}
              onChange={(event) => setSelected({ ...selected, title: event.target.value })}
              maxLength={200}
            />
          </label>
          <Textarea
            label="Body"
            value={selected.body}
            onChange={(event) => setSelected({ ...selected, body: event.target.value })}
            style={{ minHeight: 220 }}
          />
          <p className="caption">
            Last updated {relativeTime(selected.updated_at)} · owner {selected.owner.full_name}
          </p>
        </Modal>
      )}

      <ToastRegion toasts={toasts} />
    </div>
  );
}
