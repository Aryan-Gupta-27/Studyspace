"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { Button, Input } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const { login, user, ready } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (ready && user) router.replace("/dashboard");
  }, [ready, user, router]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setFieldErrors({});
    try {
      await login(email.trim(), password);
      router.replace("/dashboard");
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message);
        setFieldErrors(caught.fields);
      } else {
        setError("We couldn't sign you in. Please try again.");
      }
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <span className="brand-mark" aria-hidden="true">
            ◆
          </span>
          StudySpace
        </div>
        <h1 style={{ fontSize: "var(--text-h2)", marginBottom: "var(--space-2)" }}>Welcome back</h1>
        <p className="small muted" style={{ marginBottom: "var(--space-5)" }}>
          Sign in to pick up where your groups left off.
        </p>

        {error && (
          <div className="alert alert-error" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={onSubmit} noValidate>
          <Input
            label="Email"
            type="email"
            name="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            error={fieldErrors.email}
            disabled={submitting}
          />
          <Input
            label="Password"
            type="password"
            name="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            error={fieldErrors.password}
            disabled={submitting}
          />
          <Button type="submit" block loading={submitting} disabled={!email || !password}>
            Sign in
          </Button>
        </form>

        <p className="small muted" style={{ marginTop: "var(--space-5)", marginBottom: 0 }}>
          Don&apos;t have an account? <Link href="/register">Sign up</Link>
        </p>
      </div>
    </div>
  );
}
