"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type User = { name: string; email: string };
type Session = { id: number; created_at: string; expires_at: string; is_current: boolean };

export default function AccountPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [notice, setNotice] = useState("Loading account…");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch(`${apiUrl}/api/auth/me`, { credentials: "include" })
      .then(async (response) => { if (!response.ok) throw new Error("Sign in to manage your account."); return response.json() as Promise<User>; })
      .then(async (account) => { setUser(account); const response = await fetch(`${apiUrl}/api/auth/sessions`, { credentials: "include" }); if (response.ok) setSessions(await response.json()); setNotice(""); })
      .catch((error) => { setNotice(error instanceof Error ? error.message : "Sign in to manage your account."); router.replace("/auth"); });
  }, [router]);

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const newPassword = String(form.get("new_password") ?? "");
    if (newPassword !== form.get("confirm_password")) return setNotice("New password entries must match.");
    setSaving(true);
    try {
      const response = await fetch(`${apiUrl}/api/auth/password`, { method: "PUT", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ current_password: form.get("current_password"), new_password: newPassword }) });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "Could not change password.");
      event.currentTarget.reset();
      setNotice("Password updated. Other active sessions were signed out.");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not change password."); } finally { setSaving(false); }
  }

  async function revokeSession(sessionId: number) { try { const response = await fetch(`${apiUrl}/api/auth/sessions/${sessionId}`, { method: "DELETE", credentials: "include" }); if (!response.ok) throw new Error("Could not sign out that session."); setSessions((items) => items.filter((item) => item.id !== sessionId)); setNotice("Session signed out."); } catch (error) { setNotice(error instanceof Error ? error.message : "Could not sign out that session."); } }

  return <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100"><div className="mx-auto max-w-lg"><Link href="/" className="text-sm font-semibold text-cyan-400">← RubriCheck AI</Link><h1 className="mt-6 text-4xl font-bold">Account & security</h1>{user && <p className="mt-2 text-slate-400">{user.name} · {user.email}</p>}<p className="mt-6 rounded-lg border border-cyan-400/25 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100">{notice}</p><form onSubmit={changePassword} className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-6"><h2 className="text-xl font-semibold">Change password</h2><p className="mt-2 text-sm text-slate-400">Changing your password signs out all other browser sessions.</p><input required name="current_password" type="password" placeholder="Current password" className="field mt-5"/><input required name="new_password" type="password" minLength={10} placeholder="New password (10+ characters)" className="field mt-3"/><input required name="confirm_password" type="password" minLength={10} placeholder="Confirm new password" className="field mt-3"/><button disabled={saving} className="button mt-5">{saving ? "Updating…" : "Update password"}</button></form><section className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-6"><h2 className="text-xl font-semibold">Active sessions</h2><p className="mt-2 text-sm text-slate-400">Sign out browsers you no longer use.</p><div className="mt-4 divide-y divide-slate-800">{sessions.map((item) => <div key={item.id} className="flex items-center justify-between gap-4 py-3"><div><p className="font-semibold">{item.is_current ? "This browser" : "Signed-in browser"}</p><p className="text-xs text-slate-400">Started {new Date(item.created_at).toLocaleString()}</p></div>{item.is_current ? <span className="text-sm text-cyan-300">Current</span> : <button type="button" onClick={() => revokeSession(item.id)} className="text-sm font-semibold text-rose-300">Sign out</button>}</div>)}</div></section></div></main>;
}
