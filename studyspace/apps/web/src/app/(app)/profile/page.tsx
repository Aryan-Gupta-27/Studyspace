"use client";

/** Profile view and edit (milestone 3 gate). */

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { Avatar, Button, Card, PageHeader, SkeletonList, Textarea, ToastRegion, useToasts } from "@/components/ui";
import { ApiError, apiRequest, type Profile as ProfileData, type User } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDay } from "@/lib/format";

interface ProfileForm {
  bio: string;
  institution: string;
  program: string;
  academic_year: string;
  skills: string;
  interests: string;
}

const EMPTY_FORM: ProfileForm = {
  bio: "",
  institution: "",
  program: "",
  academic_year: "",
  skills: "",
  interests: "",
};

function toForm(profile: ProfileData | undefined): ProfileForm {
  if (!profile) return EMPTY_FORM;
  return {
    bio: profile.bio,
    institution: profile.institution,
    program: profile.program,
    academic_year: profile.academic_year,
    skills: profile.skills.join(", "),
    interests: profile.interests.join(", "),
  };
}

function splitTags(value: string): string[] {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

export default function ProfilePage() {
  const { user, withAuth, refreshProfile } = useAuth();
  const { toasts, push } = useToasts();
  const [form, setForm] = useState<ProfileForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (user) setForm(toForm(user.profile));
  }, [user]);

  const load = useCallback(async () => {
    try {
      await refreshProfile();
    } catch {
      // The dashboard already surfaces connection problems.
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function update(field: keyof ProfileForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setFieldErrors({});
    try {
      const updated = await withAuth((token) =>
        apiRequest<User>("/users/me", {
          method: "PATCH",
          body: {
            bio: form.bio,
            institution: form.institution,
            program: form.program,
            academic_year: form.academic_year,
            skills: splitTags(form.skills),
            interests: splitTags(form.interests),
          },
          accessToken: token,
        }),
      );
      setForm(toForm(updated.profile));
      push("success", "Profile updated.");
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message);
        setFieldErrors(caught.fields);
      } else {
        setError("We couldn't save your profile. Please try again.");
      }
    } finally {
      setSaving(false);
    }
  }

  if (!user) {
    return (
      <div className="page">
        <SkeletonList rows={4} height={20} />
      </div>
    );
  }

  return (
    <div className="page">
      <PageHeader title="Your profile" subtitle="This is how classmates and teammates will see you." />

      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      <div className="grid grid-2">
        <Card>
          <div className="row" style={{ marginBottom: "var(--space-5)" }}>
            <Avatar name={user.full_name} large />
            <div>
              <h2 className="card-title" style={{ marginBottom: 2 }}>
                {user.full_name}
              </h2>
              <p className="card-meta">@{user.username}</p>
              <p className="caption">{user.email}</p>
            </div>
          </div>

          <dl className="stack" style={{ gap: "var(--space-2)" }}>
            <div className="row row-between">
              <dt className="small muted">Institution</dt>
              <dd className="small" style={{ margin: 0 }}>
                {user.profile?.institution || "Not set"}
              </dd>
            </div>
            <div className="row row-between">
              <dt className="small muted">Program</dt>
              <dd className="small" style={{ margin: 0 }}>
                {user.profile?.program || "Not set"}
              </dd>
            </div>
            <div className="row row-between">
              <dt className="small muted">Academic year</dt>
              <dd className="small" style={{ margin: 0 }}>
                {user.profile?.academic_year || "Not set"}
              </dd>
            </div>
            <div className="row row-between">
              <dt className="small muted">Joined</dt>
              <dd className="small" style={{ margin: 0 }}>
                {formatDay(user.created_at)}
              </dd>
            </div>
          </dl>

          {user.profile?.skills.length ? (
            <div style={{ marginTop: "var(--space-5)" }}>
              <p className="caption" style={{ marginBottom: 6 }}>Skills</p>
              <div className="row" style={{ gap: 6 }}>
                {user.profile.skills.map((skill) => (
                  <span key={skill} className="badge badge-primary">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          {user.profile?.interests.length ? (
            <div style={{ marginTop: "var(--space-4)" }}>
              <p className="caption" style={{ marginBottom: 6 }}>Interests</p>
              <div className="row" style={{ gap: 6 }}>
                {user.profile.interests.map((interest) => (
                  <span key={interest} className="badge">{interest}</span>
                ))}
              </div>
            </div>
          ) : null}
        </Card>

        <Card>
          <h2 className="card-title">Edit profile</h2>
          <form onSubmit={save}>
            <label className="field">
              <span className="field-label">Full name</span>
              <input className="input" value={user.full_name} disabled />
              <span className="field-hint">Name changes are not part of the MVP.</span>
            </label>

            <Textarea
              label="About you"
              value={form.bio}
              onChange={(event) => update("bio", event.target.value)}
              maxLength={1000}
              placeholder="What are you studying or working on?"
              error={fieldErrors.bio}
            />

            <label className="field">
              <span className="field-label">College / school</span>
              <input
                className="input"
                value={form.institution}
                onChange={(event) => update("institution", event.target.value)}
                maxLength={200}
              />
            </label>

            <label className="field">
              <span className="field-label">Program / course</span>
              <input
                className="input"
                value={form.program}
                onChange={(event) => update("program", event.target.value)}
                maxLength={200}
              />
            </label>

            <label className="field">
              <span className="field-label">Academic year</span>
              <input
                className="input"
                value={form.academic_year}
                onChange={(event) => update("academic_year", event.target.value)}
                maxLength={50}
                placeholder="3rd year"
              />
            </label>

            <label className="field">
              <span className="field-label">Skills</span>
              <input
                className="input"
                value={form.skills}
                onChange={(event) => update("skills", event.target.value)}
                placeholder="Python, Machine Learning, UI design"
              />
              <span className="field-hint">Separate each skill with a comma (up to 20).</span>
            </label>

            <label className="field">
              <span className="field-label">Interests</span>
              <input
                className="input"
                value={form.interests}
                onChange={(event) => update("interests", event.target.value)}
                placeholder="Open source, Robotics"
              />
              <span className="field-hint">Separate each interest with a comma (up to 20).</span>
            </label>

            <Button type="submit" loading={saving}>
              Save profile
            </Button>
          </form>
        </Card>
      </div>

      <ToastRegion toasts={toasts} />
    </div>
  );
}
