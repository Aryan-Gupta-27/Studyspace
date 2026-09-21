"use client";

/**
 * Public landing page. Signed-in visitors are sent straight to the dashboard.
 */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/lib/auth";

const PILLARS = [
  { icon: "✎", title: "Learn", text: "Notes and study material that stay connected to the group they belong to." },
  { icon: "◍", title: "Collaborate", text: "Group chat, shared files and projects without switching applications." },
  { icon: "▤", title: "Build", text: "Projects, tasks and a four-column board for real academic work." },
  { icon: "▣", title: "Organise", text: "Personal and group files with ownership enforced on the server." },
];

export default function LandingPage() {
  const { user, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (ready && user) router.replace("/dashboard");
  }, [ready, user, router]);

  return (
    <div className="landing">
      <div className="landing-inner">
        <div className="landing-nav">
          <span className="brand">
            <span className="brand-mark" aria-hidden="true">
              ◆
            </span>
            StudySpace
          </span>
          <div className="row">
            <Link href="/login" className="btn btn-secondary btn-sm">
              Sign in
            </Link>
            <Link href="/register" className="btn btn-primary btn-sm">
              Create account
            </Link>
          </div>
        </div>

        <section className="landing-hero">
          <h1>One workspace for studying, discussing and building together.</h1>
          <p>
            StudySpace brings your study groups, conversations, notes, files, projects and tasks into a single
            connected environment — so collaboration feels like one continuous workflow.
          </p>
          <div className="row">
            <Link href="/register" className="btn btn-primary">
              Get started free
            </Link>
            <Link href="/login" className="btn btn-secondary">
              I already have an account
            </Link>
          </div>
        </section>

        <section className="pillar-grid" aria-label="What you can do">
          {PILLARS.map((pillar) => (
            <article key={pillar.title} className="card">
              <div aria-hidden="true" style={{ fontSize: 22, marginBottom: 8 }}>
                {pillar.icon}
              </div>
              <h2 className="card-title">{pillar.title}</h2>
              <p className="card-meta">{pillar.text}</p>
            </article>
          ))}
        </section>

        <section style={{ marginTop: "var(--space-12)" }}>
          <p className="caption">
            MVP scope: accounts and profiles, groups, group chat, notes, files, projects and tasks. Communities,
            realtime presence, repositories and search are planned after this release.
          </p>
        </section>
      </div>
    </div>
  );
}
