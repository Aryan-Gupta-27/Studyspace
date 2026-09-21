import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";

/** Every signed-in page shares one visual frame (design spec section 4). */
export default function AppLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
