"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type User = { name: string; email: string };

export default function AccountControl() {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    fetch(`${apiUrl}/api/auth/me`, { credentials: "include" })
      .then(async (response) => response.ok ? response.json() as Promise<User> : null)
      .then(setUser)
      .catch(() => setUser(null));
  }, []);

  async function signOut() {
    await fetch(`${apiUrl}/api/auth/logout`, { method: "POST", credentials: "include" });
    setUser(null);
    router.push("/auth");
  }

  if (!user) return null;
  const links = [["/dashboard", "Dashboard"], ["/setup", "Setup"], ["/submissions", "Intake"], ["/results", "Results"]] as const;
  return <nav className="fixed left-4 right-4 top-4 z-10 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-700 bg-slate-900/95 px-4 py-3 text-sm shadow-lg"><div className="flex flex-wrap items-center gap-3">{links.map(([href, label]) => <Link key={href} href={href} className={pathname === href ? "font-semibold text-cyan-300" : "text-slate-300"}>{label}</Link>)}</div><div className="flex items-center gap-3"><Link href="/account" className="text-slate-200">{user.name}</Link><button type="button" onClick={signOut} className="font-semibold text-cyan-300">Sign out</button></div></nav>;
}
