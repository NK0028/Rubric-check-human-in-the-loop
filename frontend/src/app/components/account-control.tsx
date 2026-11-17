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
  return <nav className="fixed left-4 right-4 top-4 z-20 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-700/80 bg-slate-950/85 px-4 py-3 text-sm shadow-2xl shadow-slate-950/50 backdrop-blur-xl"><div className="flex flex-wrap items-center gap-5"><Link href="/dashboard" className="flex items-center gap-2 font-bold tracking-tight text-white"><span className="grid h-8 w-8 place-items-center rounded-lg bg-cyan-300 text-slate-950">✓</span>RubriCheck <span className="text-cyan-300">AI</span></Link><div className="hidden h-6 w-px bg-slate-700 md:block"/>{links.map(([href, label]) => <Link key={href} href={href} className={pathname === href ? "font-semibold text-cyan-300" : "text-slate-400 transition hover:text-slate-100"}>{label}</Link>)}</div><div className="flex items-center gap-3"><Link href="/account" className="hidden text-slate-200 sm:block"><span className="mr-2 inline-grid h-7 w-7 place-items-center rounded-full border border-cyan-400/30 bg-cyan-400/10 text-xs font-bold text-cyan-300">{user.name.slice(0, 1).toUpperCase()}</span>{user.name}</Link><button type="button" onClick={signOut} className="rounded-lg border border-cyan-400/30 px-3 py-2 font-semibold text-cyan-300 transition hover:bg-cyan-400/10">Sign out</button></div></nav>;
}
