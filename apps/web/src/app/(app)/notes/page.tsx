"use client";

/** Personal and group notes, with search (design spec section 45). */

import { useCallback, useEffect, useState, type FormEvent } from "react";

import {
  Badge,
  Button,
  EmptyState,
  Modal,
  PageHeader,
  SkeletonList,
  Textarea,
  ToastRegion,
  useToasts,
} from "@/components/ui";
import { apiRequest, type Group, type Note, type Page } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { relativeTime } from "@/lib/format";

export default function NotesPage() {
  const { withAuth, ready, user } = useAuth();
  const { toasts, push } = useToasts();
  const [notes, setNotes] = useState<Note[] | null>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<Note | null>(null);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [groupId, setGroupId] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const [page, groupPage] = await Promise.all([
        withAuth((token) =>
          apiRequest<Page<Note>>("/notes", { accessToken: token, query: { limit: 50, search: search || undefined } }),
        ),
        withAuth((token) => apiRequest<{ items: Group[] }>("/groups", { accessToken: token, query: { limit: 50 } })),
      ]);
      setNotes(page.items);
      setGroups(groupPage.items);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We couldn't load your notes.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, search]);

  useEffect(() => {
    if (ready) void load();
  }, [ready, load]);

  function openNew() {
    setEditing(null);
    setTitle("");
    setBody("");
    setGroupId("");
    setEditorOpen(true);
  }

  function openExisting(note: Note) {
    setEditing(note);
    setTitle(note.title);
    setBody(note.body);
    setGroupId(note.group_id ?? "");
    setEditorOpen(true);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      if (editing) {
        await withAuth((token) =>
          apiRequest<Note>(`/notes/${editing.id}`, {
            method: "PATCH",
            body: { title: title.trim(), body },
            accessToken: token,
          }),
        );
        push("success", "Note saved.");
      } else {
        await withAuth((token) =>
          apiRequest<Note>("/notes", {
            method: "POST",
            body: { title: title.trim(), body, group_id: groupId || null },
            accessToken: token,
          }),
        );
        push("success", "Note created.");
      }
      setEditorOpen(false);
      await load();
    } catch (caught) {
      push("error", caught instanceof Error ? caught.message : "We couldn't save that note.");
    } finally {
      setSaving(false);
    }
  }

  async function remove(noteId: string) {
    try {
      await withAuth((token) => apiRequest<void>(`/notes/${noteId}`, { method: "DELETE", accessToken: token }));
      setEditorOpen(false);
      push("success", "Note deleted.");
      await load();
    } catch (caught) {
      push("error", caught instanceof Error ? caught.message : "We couldn't delete that note.");
    }
  }

  return (
    <div className="page">
      <PageHeader
        title="Notes"
        subtitle="Fast, lightweight writing for yourself or shared with a group."
        actions={<Button onClick={openNew}>+ New note</Button>}
      />

      {error && (
        <div className="alert alert-error" role="alert">
          {error} <Button variant="ghost" size="sm" onClick={load}>Try again</Button>
        </div>
      )}

      <div className="field" style={{ maxWidth: 360 }}>
        <label className="field-label" htmlFor="note-search">
          Search notes
        </label>
        <input
          id="note-search"
          className="input"
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search by title or content"
        />
      </div>

      {notes === null && <SkeletonList rows={4} height={18} />}

      {notes && notes.length === 0 && (
        <EmptyState
          icon="✎"
          title={search ? "No notes match that search" : "No notes yet"}
          description={
            search
              ? "Try a different keyword, or clear the search to see every note."
              : "Write lecture notes, revision summaries or project documentation. Share a note with a group to collaborate on it."
          }
          action={search ? <Button variant="secondary" onClick={() => setSearch("")}>Clear search</Button> : <Button onClick={openNew}>Write your first note</Button>}
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
              onClick={() => openExisting(note)}
            >
              <div className="row row-between" style={{ marginBottom: "var(--space-2)" }}>
                <h2 className="card-title" style={{ margin: 0 }}>
                  {note.title}
                </h2>
                <Badge tone={note.group_id ? "primary" : "default"}>
                  {note.group_id ? "Group" : "Private"}
                </Badge>
              </div>
              <p className="card-meta">{note.body.slice(0, 140) || "Empty note."}</p>
              <p className="caption" style={{ marginTop: "var(--space-3)", marginBottom: 0 }}>
                {note.owner.id === user?.id ? "You" : note.owner.full_name} · updated{" "}
                {relativeTime(note.updated_at)}
              </p>
            </button>
          ))}
        </div>
      )}

      {editorOpen && (
        <Modal
          title={editing ? "Edit note" : "New note"}
          onClose={() => setEditorOpen(false)}
          footer={
            <>
              {editing && (
                <Button variant="danger" onClick={() => remove(editing.id)} style={{ marginRight: "auto" }}>
                  Delete
                </Button>
              )}
              <Button variant="secondary" onClick={() => setEditorOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" form="note-form" loading={saving} disabled={!title.trim()}>
                {editing ? "Save changes" : "Create note"}
              </Button>
            </>
          }
        >
          <form id="note-form" onSubmit={save}>
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
              style={{ minHeight: 240 }}
            />
            {!editing && (
              <label className="field">
                <span className="field-label">Share with</span>
                <select
                  className="select"
                  value={groupId}
                  onChange={(event) => setGroupId(event.target.value)}
                >
                  <option value="">Only me (private note)</option>
                  {groups.map((group) => (
                    <option key={group.id} value={group.id}>
                      {group.name}
                    </option>
                  ))}
                </select>
                <span className="field-hint">
                  Shared notes can be read and edited by everyone in the group.
                </span>
              </label>
            )}
          </form>
        </Modal>
      )}

      <ToastRegion toasts={toasts} />
    </div>
  );
}
