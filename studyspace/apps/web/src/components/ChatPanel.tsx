"use client";

/**
 * Group chat.
 *
 * Realtime delivery is HTTP polling for the MVP: the transcript refreshes on
 * an interval and immediately after sending, which is the approach the task
 * book requires before WebSockets are introduced.
 */

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import { Avatar, Button, EmptyState } from "@/components/ui";
import { apiRequest, type Conversation, type Message } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { clockTime } from "@/lib/format";

const POLL_INTERVAL_MS = 5000;

export function ChatPanel({ groupId }: { groupId: string }) {
  const { withAuth, user } = useAuth();
  const [conversations, setConversations] = useState<Conversation[] | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[] | null>(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadConversations = useCallback(async () => {
    const list = await withAuth((token) =>
      apiRequest<Conversation[]>(`/groups/${groupId}/conversations`, { accessToken: token }),
    );
    setConversations(list);
    setActiveId((current) => current ?? (list[0]?.id ?? null));
    return list;
  }, [groupId, withAuth]);

  const loadMessages = useCallback(
    async (conversationId: string) => {
      const page = await withAuth((token) =>
        apiRequest<{ items: Message[]; total: number }>(`/conversations/${conversationId}/messages`, {
          accessToken: token,
          query: { limit: 50 },
        }),
      );
      setMessages(page.items);
      return page.items;
    },
    [withAuth],
  );

  useEffect(() => {
    let cancelled = false;
    setError(null);
    loadConversations()
      .then((list) => {
        if (!cancelled && list[0]) return loadMessages(list[0].id);
        return undefined;
      })
      .catch((caught) => {
        if (!cancelled) setError(caught instanceof Error ? caught.message : "We couldn't load this chat.");
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId]);

  // Poll while a conversation is open; pause when the tab is hidden.
  useEffect(() => {
    if (!activeId) return;
    const timer = window.setInterval(() => {
      if (document.visibilityState !== "visible") return;
      loadMessages(activeId).catch(() => {
        // A transient poll failure is not worth surfacing to the user.
      });
      if (editingId === null) {
        void withAuth((token) =>
          apiRequest<void>(`/conversations/${activeId}/read`, { method: "POST", accessToken: token }),
        ).catch(() => undefined);
      }
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId, editingId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "nearest" });
  }, [messages]);

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!activeId || draft.trim().length === 0) return;
    setSending(true);
    setError(null);
    try {
      await withAuth((token) =>
        apiRequest<Message>(`/conversations/${activeId}/messages`, {
          method: "POST",
          body: { body: draft.trim() },
          accessToken: token,
        }),
      );
      setDraft("");
      await loadMessages(activeId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We couldn't send that message.");
    } finally {
      setSending(false);
    }
  }

  async function saveEdit(messageId: string) {
    if (!activeId) return;
    try {
      await withAuth((token) =>
        apiRequest<Message>(`/messages/${messageId}`, {
          method: "PATCH",
          body: { body: editDraft.trim() },
          accessToken: token,
        }),
      );
      setEditingId(null);
      await loadMessages(activeId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We couldn't save that edit.");
    }
  }

  async function remove(messageId: string) {
    if (!activeId) return;
    try {
      await withAuth((token) =>
        apiRequest<void>(`/messages/${messageId}`, { method: "DELETE", accessToken: token }),
      );
      await loadMessages(activeId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We couldn't delete that message.");
    }
  }

  if (error) {
    return (
      <div className="alert alert-error" role="alert">
        {error}
      </div>
    );
  }

  return (
    <div className="chat-layout">
      <aside className="chat-side" aria-label="Conversations">
        <div className="sidebar-section" style={{ marginTop: 0, padding: "0 4px 8px" }}>
          Channels
        </div>
        {conversations?.map((conversation) => (
          <button
            key={conversation.id}
            type="button"
            className="conversation-item"
            aria-current={conversation.id === activeId}
            onClick={async () => {
              setActiveId(conversation.id);
              setMessages(null);
              try {
                await loadMessages(conversation.id);
              } catch (caught) {
                setError(caught instanceof Error ? caught.message : "We couldn't load this chat.");
              }
            }}
          >
            # {conversation.name}
          </button>
        ))}
      </aside>

      <section className="chat-panel" aria-label="Conversation">
        <div className="chat-messages" aria-live="polite">
          {messages === null && (
            <div className="stack" style={{ width: "100%" }}>
              <div className="skeleton" style={{ width: "45%" }} />
              <div className="skeleton" style={{ width: "70%" }} />
            </div>
          )}

          {messages && messages.length === 0 && (
            <EmptyState
              icon="◍"
              title="No messages yet"
              description="Start the conversation — share what you're working on or ask a question."
            />
          )}

          {messages?.map((message) => (
            <article key={message.id} className="message">
              <Avatar name={message.author.full_name} />
              <div className="message-body">
                <div className="message-head">
                  <span className="message-author">{message.author.full_name}</span>
                  <span className="message-time">
                    {clockTime(message.created_at)}
                    {message.edited_at ? " · edited" : ""}
                  </span>
                </div>

                {editingId === message.id ? (
                  <div>
                    <textarea
                      className="textarea"
                      value={editDraft}
                      onChange={(event) => setEditDraft(event.target.value)}
                      aria-label="Edit message"
                      maxLength={4000}
                    />
                    <div className="row" style={{ marginTop: "var(--space-2)" }}>
                      <Button size="sm" onClick={() => saveEdit(message.id)} disabled={!editDraft.trim()}>
                        Save
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => setEditingId(null)}>
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <>
                    <p className="message-text">{message.body}</p>
                    {message.author.id === user?.id && (
                      <div className="message-actions">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setEditingId(message.id);
                            setEditDraft(message.body);
                          }}
                        >
                          Edit
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => remove(message.id)}>
                          Delete
                        </Button>
                      </div>
                    )}
                  </>
                )}
              </div>
            </article>
          ))}
          <div ref={bottomRef} />
        </div>

        <form className="chat-composer" onSubmit={send}>
          <label className="sr-only" htmlFor="message-input">
            Write a message
          </label>
          <textarea
            id="message-input"
            className="textarea"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Write a message…"
            maxLength={4000}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void send(event);
              }
            }}
          />
          <Button type="submit" loading={sending} disabled={!draft.trim()}>
            Send
          </Button>
        </form>
      </section>
    </div>
  );
}
