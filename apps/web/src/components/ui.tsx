"use client";

/**
 * Reusable UI primitives.
 *
 * Only components used in more than one place live here, and each one covers
 * the states the design spec requires: default, hover, focus, disabled,
 * loading, empty and error (spec sections 16-23, 79).
 */

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";

/* ---------------------------------------------------------------- button */

type ButtonVariant = "primary" | "secondary" | "outline" | "danger" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: "sm" | "md";
  loading?: boolean;
  block?: boolean;
}

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  block = false,
  className = "",
  children,
  disabled,
  ...rest
}: ButtonProps) {
  const classes = [
    "btn",
    `btn-${variant}`,
    size === "sm" ? "btn-sm" : "",
    block ? "btn-block" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button className={classes} disabled={disabled || loading} aria-busy={loading} {...rest}>
      {loading && <span className="spinner" aria-hidden="true" />}
      {children}
    </button>
  );
}

/* ----------------------------------------------------------------- input */

interface FieldWrapProps {
  label: string;
  hint?: string;
  error?: string;
  required?: boolean;
  htmlFor: string;
  children: ReactNode;
}

function FieldWrap({ label, hint, error, required, htmlFor, children }: FieldWrapProps) {
  return (
    <div className="field">
      <label className="field-label" htmlFor={htmlFor}>
        {label}
        {required && <span aria-hidden="true"> *</span>}
      </label>
      {children}
      {hint && !error && <span className="field-hint">{hint}</span>}
      {error && (
        <span className="field-error" id={`${htmlFor}-error`}>
          {error}
        </span>
      )}
    </div>
  );
}

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
  error?: string;
}

export function Input({ label, hint, error, id, required, ...rest }: InputProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  return (
    <FieldWrap label={label} hint={hint} error={error} required={required} htmlFor={inputId}>
      <input
        id={inputId}
        className="input"
        required={required}
        aria-invalid={error ? "true" : undefined}
        aria-describedby={error ? `${inputId}-error` : undefined}
        {...rest}
      />
    </FieldWrap>
  );
}

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string;
}

export function Textarea({ label, hint, error, id, required, ...rest }: TextareaProps) {
  const generatedId = useId();
  const textareaId = id ?? generatedId;
  const control = (
    <textarea
      id={textareaId}
      className="textarea"
      required={required}
      aria-invalid={error ? "true" : undefined}
      aria-describedby={error ? `${textareaId}-error` : undefined}
      {...rest}
    />
  );
  if (!label) return control;
  return (
    <FieldWrap label={label} hint={hint} error={error} required={required} htmlFor={textareaId}>
      {control}
    </FieldWrap>
  );
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  hint?: string;
  error?: string;
  options: { value: string; label: string }[];
}

export function Select({ label, hint, error, id, required, options, ...rest }: SelectProps) {
  const generatedId = useId();
  const selectId = id ?? generatedId;
  return (
    <FieldWrap label={label} hint={hint} error={error} required={required} htmlFor={selectId}>
      <select
        id={selectId}
        className="select"
        required={required}
        aria-invalid={error ? "true" : undefined}
        {...rest}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </FieldWrap>
  );
}

/* ------------------------------------------------------------------ card */

export function Card({
  children,
  className = "",
  hover = false,
}: {
  children: ReactNode;
  className?: string;
  hover?: boolean;
}) {
  return <div className={`card ${hover ? "card-hover" : ""} ${className}`.trim()}>{children}</div>;
}

export function Avatar({ name, large = false }: { name: string; large?: boolean }) {
  const letters = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0] ?? "")
    .join("")
    .toUpperCase();
  return (
    <span className={`avatar ${large ? "avatar-lg" : ""}`.trim()} aria-hidden="true">
      {letters || "?"}
    </span>
  );
}

type BadgeTone = "default" | "primary" | "success" | "warning" | "danger" | "info";

export function Badge({ children, tone = "default" }: { children: ReactNode; tone?: BadgeTone }) {
  const toneClass = tone === "default" ? "" : `badge-${tone}`;
  return <span className={`badge ${toneClass}`.trim()}>{children}</span>;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon" aria-hidden="true">
        {icon}
      </div>
      <h3 className="empty-title">{title}</h3>
      <p className="empty-text">{description}</p>
      {action}
    </div>
  );
}

/** Shows line placeholders instead of a blank area while data loads (spec 21). */
export function SkeletonList({ rows = 3, height = 14 }: { rows?: number; height?: number }) {
  return (
    <div className="stack" aria-hidden="true">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="skeleton" style={{ height, width: `${100 - index * 12}%` }} />
      ))}
    </div>
  );
}

export function Alert({
  tone,
  children,
  role = "status",
}: {
  tone: "error" | "success" | "info";
  children: ReactNode;
  role?: string;
}) {
  return (
    <div className={`alert alert-${tone}`} role={role}>
      {children}
    </div>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div className="page-header-text">
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}

/* ----------------------------------------------------------------- modal */

export function Modal({
  title,
  onClose,
  children,
  footer,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const titleId = useId();

  useEffect(() => {
    // Move focus into the dialog and restore it on close so keyboard users
    // are never stranded behind the overlay.
    const previouslyFocused = document.activeElement as HTMLElement | null;
    dialogRef.current?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previouslyFocused?.focus?.();
    };
  }, [onClose]);

  return (
    <div
      className="modal-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        ref={dialogRef}
        tabIndex={-1}
      >
        <div className="modal-header">
          <h2 id={titleId} style={{ fontSize: "var(--text-h3)" }}>
            {title}
          </h2>
          <Button variant="ghost" className="btn-icon" onClick={onClose} aria-label="Close dialog">
            ✕
          </Button>
        </div>
        {children}
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  );
}

/* ----------------------------------------------------------------- toast */

export interface ToastMessage {
  id: number;
  tone: "success" | "error" | "info";
  text: string;
}

let toastId = 0;

export function useToasts() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const push = useCallback(
    (tone: ToastMessage["tone"], text: string) => {
      toastId += 1;
      const id = toastId;
      setToasts((current) => [...current, { id, tone, text }]);
      // Toasts are for short feedback only; critical information never lives
      // here because it would disappear (design spec section 20).
      window.setTimeout(() => dismiss(id), 4500);
    },
    [dismiss],
  );

  return { toasts, push, dismiss };
}

export function ToastRegion({ toasts }: { toasts: ToastMessage[] }) {
  if (toasts.length === 0) return null;
  return (
    <div className="toast-region" role="status" aria-live="polite">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast-${toast.tone}`}>
          {toast.text}
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ tabs */

export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: T; label: string; badge?: number }[];
  active: T;
  onChange: (id: T) => void;
}) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          className="tab"
          role="tab"
          type="button"
          aria-selected={active === tab.id}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
          {tab.badge ? <span className="nav-count">{tab.badge}</span> : null}
        </button>
      ))}
    </div>
  );
}
