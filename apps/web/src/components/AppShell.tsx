"use client";

/**
 * Persistent application shell: top bar, sidebar and mobile bottom
 * navigation. The same frame wraps every signed-in page so navigation stays
 * predictable (design spec sections 4-8, 68-69).
 */

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { apiRequest, type Group } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Avatar, Button } from "@/components/ui";

const PRIMARY_NAV = [
  { href: "/dashboard", label: "Home", icon: "◎" },
  { href: "/groups", label: "Groups", icon: "◍" },
  { href: "/projects", label: "Projects", icon: "▤" },
  { href: "/notes", label: "Notes", icon: "✎" },
  { href: "/files", label: "Files", icon: "▣" },
];

const SECONDARY_NAV = [{ href: "/profile", label: "Profile", icon: "◉" }];

function useUnreadCount() {
  const { withAuth, ready } = useAuth();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    if (!ready) return;
    let active = true;
    withAuth((token) => apiRequest<{ items: Group[] }>("/groups", { accessToken: token, query: { limit: 50 } }))
      .then((page) => {
        if (!active) return;
        setUnread(page.items.reduce((total, group) => total + group.unread_count, 0));
      })
      .catch(() => {
        // A failed badge fetch must never break the shell.
      });
    return () => {
      active = false;
    };
  }, [ready, withAuth]);

  return unread;
}

export function AppShell({ children }: { children: ReactNode }) {
  const { user, ready, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const unread = useUnreadCount();

  useEffect(() => {
    if (ready && !user) router.replace("/login");
  }, [ready, user, router]);

  if (!ready) {
    return (
      <div className="app-shell">
        <div className="main-content">
          <div className="page">
            <div className="stack" aria-busy="true" aria-live="polite">
              <span className="sr-only">Loading StudySpace…</span>
              <div className="skeleton" style={{ width: "30%", height: 26 }} />
              <div className="skeleton" style={{ width: "100%", height: 90 }} />
              <div className="skeleton" style={{ width: "80%", height: 90 }} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!user) return null;

  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  const navLink = (item: { href: string; label: string; icon: string }, badge?: number) => (
    <Link
      key={item.href}
      href={item.href}
      className="nav-link"
      aria-current={isActive(item.href) ? "page" : undefined}
    >
      <span className="nav-icon" aria-hidden="true">
        {item.icon}
      </span>
      <span className="nav-label">{item.label}</span>
      {badge ? <span className="nav-count">{badge}</span> : null}
    </Link>
  );

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link href="/dashboard" className="brand">
          <span className="brand-mark" aria-hidden="true">
            ◆
          </span>
          StudySpace
        </Link>

        <div className="topbar-search">
          <label className="sr-only" htmlFor="global-search">
            Search
          </label>
          {/* Global search ships after the MVP gate; the control is present but
              explicitly marked unavailable rather than pretending to work. */}
          <input
            id="global-search"
            className="input"
            type="search"
            placeholder="Search (coming after the MVP)"
            disabled
            aria-describedby="search-status"
          />
          <span id="search-status" className="sr-only">
            Search is not part of the MVP.
          </span>
        </div>

        <div className="topbar-right">
          <Link href="/groups" className="btn btn-ghost btn-sm" aria-label={`Groups, ${unread} unread messages`}>
            ◍ {unread > 0 ? <span className="badge badge-primary">{unread}</span> : null}
          </Link>
          <Link href="/profile" className="row" style={{ gap: "var(--space-2)", color: "var(--color-text)" }}>
            <Avatar name={user.full_name} />
            <span className="small nowrap">{user.full_name}</span>
          </Link>
          <Button
            variant="ghost"
            size="sm"
            onClick={async () => {
              await logout();
              router.replace("/login");
            }}
          >
            Sign out
          </Button>
        </div>
      </header>

      <div className="shell-body">
        <nav className="sidebar" aria-label="Primary">
          {PRIMARY_NAV.map((item) => navLink(item, item.href === "/groups" ? unread : undefined))}
          <div className="sidebar-section">Account</div>
          {SECONDARY_NAV.map((item) => navLink(item))}
        </nav>

        <main className="main-content">
          <div className="page">{children}</div>
        </main>
      </div>

      {/* Mobile navigation is designed deliberately, not a shrunken sidebar */}
      <nav className="mobile-nav" aria-label="Primary mobile">
        {[...PRIMARY_NAV, ...SECONDARY_NAV].map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="nav-link"
            aria-current={isActive(item.href) ? "page" : undefined}
          >
            <span className="nav-icon" aria-hidden="true">
              {item.icon}
            </span>
            <span className="nav-label">{item.label}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
}
