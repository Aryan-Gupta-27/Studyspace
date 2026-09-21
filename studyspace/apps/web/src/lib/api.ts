"use client";

/**
 * Typed client for the StudySpace API.
 *
 * Every request goes to the relative "/api" path, which Next.js proxies to
 * FastAPI. Browser code therefore never needs to know the backend host.
 */

export const API_BASE = "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fields: Record<string, string>;

  constructor(status: number, code: string, message: string, fields: Record<string, string> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

export type HttpMethod = "GET" | "POST" | "PATCH" | "DELETE";

interface RequestOptions {
  method?: HttpMethod;
  body?: unknown;
  query?: Record<string, string | number | undefined>;
  accessToken?: string | null;
  signal?: AbortSignal;
}

interface ErrorPayload {
  error?: { code?: string; message?: string; details?: { fields?: { field: string; message: string }[] } };
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = `${API_BASE}${path}`;
  if (!query) return url;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "") params.append(key, String(value));
  }
  const serialised = params.toString();
  return serialised ? `${url}?${serialised}` : url;
}

/** Map API error codes onto messages a student can act on (spec section 123). */
const FRIENDLY_MESSAGES: Record<string, string> = {
  INVALID_CREDENTIALS: "The email or password you entered is incorrect.",
  RESOURCE_CONFLICT: "That already exists.",
  RESOURCE_NOT_FOUND: "We couldn't find that.",
  FORBIDDEN: "You don't have permission to do that.",
  UNAUTHORIZED: "Please sign in to continue.",
  RATE_LIMITED: "You're doing that too quickly. Please wait a moment.",
  PAYLOAD_TOO_LARGE: "That file is larger than the allowed limit.",
  INTERNAL_ERROR: "Something went wrong on our side. Please try again.",
};

function friendlyMessage(code: string, fallback: string): string {
  return FRIENDLY_MESSAGES[code] ?? fallback;
}

export async function apiRequest<T>(
  path: string,
  { method = "GET", body, query, accessToken, signal }: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(0, "NETWORK_ERROR", "We couldn't reach the server. Check your connection and try again.");
  }

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  let payload: unknown = undefined;
  if (text) {
    try {
      payload = JSON.parse(text) as unknown;
    } catch {
      payload = undefined;
    }
  }

  if (!response.ok) {
    const errorPayload = (payload ?? {}) as ErrorPayload;
    const code = errorPayload.error?.code ?? "UNKNOWN_ERROR";
    const rawMessage = errorPayload.error?.message ?? "Something went wrong. Please try again.";
    const fields: Record<string, string> = {};
    for (const field of errorPayload.error?.details?.fields ?? []) {
      fields[field.field] = field.message;
    }
    throw new ApiError(response.status, code, friendlyMessage(code, rawMessage), fields);
  }

  return payload as T;
}

/** Upload is multipart, so it cannot reuse the JSON request helper. */
export async function apiUpload<T>(
  path: string,
  file: File,
  groupId: string | null,
  accessToken: string,
): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  if (groupId) form.append("group_id", groupId);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { Accept: "application/json", Authorization: `Bearer ${accessToken}` },
      body: form,
    });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "We couldn't reach the server. Check your connection and try again.");
  }

  const text = await response.text();
  const payload = text ? (JSON.parse(text) as unknown) : undefined;
  if (!response.ok) {
    const errorPayload = (payload ?? {}) as ErrorPayload;
    const code = errorPayload.error?.code ?? "UNKNOWN_ERROR";
    const rawMessage = errorPayload.error?.message ?? "We couldn't upload that file.";
    throw new ApiError(response.status, code, friendlyMessage(code, rawMessage));
  }
  return payload as T;
}

/* ------------------------------------------------------------------ types */

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Profile {
  bio: string;
  institution: string;
  program: string;
  academic_year: string;
  skills: string[];
  interests: string[];
}

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  created_at: string;
  profile: Profile;
}

export interface UserBrief {
  id: string;
  username: string;
  full_name: string;
}

export interface AuthSession {
  user: User;
  tokens: Tokens;
}

export type GroupRole = "OWNER" | "ADMIN" | "MEMBER";

export interface Group {
  id: string;
  name: string;
  description: string;
  owner_id: string;
  is_public: boolean;
  join_code: string;
  created_at: string;
  updated_at: string;
  role: GroupRole;
  member_count: number;
  unread_count: number;
}

export interface GroupSummary {
  id: string;
  name: string;
  description: string;
  is_public: boolean;
  join_code: string;
  member_count: number;
  created_at: string;
}

export interface GroupMember {
  user_id: string;
  username: string;
  full_name: string;
  role: GroupRole;
  joined_at: string;
}

export interface Conversation {
  id: string;
  group_id: string;
  name: string;
  created_at: string;
  last_message_at: string | null;
}

export interface Message {
  id: string;
  conversation_id: string;
  author: UserBrief;
  body: string;
  created_at: string;
  edited_at: string | null;
}

export interface Note {
  id: string;
  title: string;
  body: string;
  owner: UserBrief;
  group_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface FileRecord {
  id: string;
  filename: string;
  mime_type: string;
  size: number;
  owner: UserBrief;
  group_id: string | null;
  created_at: string;
}

export type ProjectStatus = "PLANNING" | "ACTIVE" | "ON_HOLD" | "COMPLETED";
export type TaskStatus = "TODO" | "IN_PROGRESS" | "REVIEW" | "DONE";
export type TaskPriority = "LOW" | "MEDIUM" | "HIGH" | "URGENT";

export interface Project {
  id: string;
  group_id: string;
  name: string;
  description: string;
  status: ProjectStatus;
  deadline: string | null;
  created_by: UserBrief;
  created_at: string;
  updated_at: string;
  task_counts: Record<string, number>;
}

export interface Task {
  id: string;
  project_id: string;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  position: number;
  assignee: UserBrief | null;
  created_by: UserBrief;
  deadline: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export const TASK_COLUMNS: TaskStatus[] = ["TODO", "IN_PROGRESS", "REVIEW", "DONE"];

export const TASK_COLUMN_LABELS: Record<TaskStatus, string> = {
  TODO: "To do",
  IN_PROGRESS: "In progress",
  REVIEW: "Review",
  DONE: "Done",
};
