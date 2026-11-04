"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type User = { name: string; email: string };

export default function AccountControl() {
  const router = useRouter();
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
  return <div className="fixed right-4 top-4 z-10 flex items-center gap-3 rounded-full border border-slate-700 bg-slate-900/95 px-3 py-2 text-xs shadow-lg"><Link href="/account" className="text-slate-200">{user.name}</Link><button type="button" onClick={signOut} className="font-semibold text-cyan-300">Sign out</button></div>;
}
