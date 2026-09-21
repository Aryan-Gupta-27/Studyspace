"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { Button, Input } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";

export default function RegisterPage() {
  const { register, user, ready } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ full_name: "", email: "", username: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (ready && user) router.replace("/dashboard");
  }, [ready, user, router]);

  function update(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setFieldErrors({});
    try {
      await register({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        username: form.username.trim().toLowerCase(),
        password: form.password,
      });
      router.replace("/dashboard");
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message);
        setFieldErrors(caught.fields);
      } else {
        setError("We couldn't create your account. Please try again.");
      }
      setSubmitting(false);
    }
  }

  const passwordTooShort = form.password.length > 0 && form.password.length < 8;

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <span className="brand-mark" aria-hidden="true">
            ◆
          </span>
          StudySpace
        </div>
        <h1 style={{ fontSize: "var(--text-h2)", marginBottom: "var(--space-2)" }}>Create your account</h1>
        <p className="small muted" style={{ marginBottom: "var(--space-5)" }}>
          Set up a workspace for your study groups and projects.
        </p>

        {error && (
          <div className="alert alert-error" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={onSubmit} noValidate>
          <Input
            label="Full name"
            autoComplete="name"
            required
            value={form.full_name}
            onChange={(event) => update("full_name", event.target.value)}
            error={fieldErrors.full_name}
            disabled={submitting}
          />
          <Input
            label="Email"
            type="email"
            autoComplete="email"
            required
            value={form.email}
            onChange={(event) => update("email", event.target.value)}
            error={fieldErrors.email}
            disabled={submitting}
          />
          <Input
            label="Username"
            autoComplete="username"
            required
            hint="3-32 characters: lowercase letters, numbers or underscores."
            value={form.username}
            onChange={(event) => update("username", event.target.value)}
            error={fieldErrors.username}
            disabled={submitting}
          />
          <Input
            label="Password"
            type="password"
            autoComplete="new-password"
            required
            hint="At least 8 characters."
            value={form.password}
            onChange={(event) => update("password", event.target.value)}
            error={fieldErrors.password ?? (passwordTooShort ? "Use at least 8 characters." : undefined)}
            disabled={submitting}
          />
          <Button
            type="submit"
            block
            loading={submitting}
            disabled={!form.full_name || !form.email || !form.username || form.password.length < 8}
          >
            Create account
          </Button>
        </form>

        <p className="small muted" style={{ marginTop: "var(--space-5)", marginBottom: 0 }}>
          Already registered? <Link href="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
