"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function AuthPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [notice, setNotice] = useState("Sign in to access your private teacher workspace.");
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true);
    try {
      const response = await fetch(`${apiUrl}/api/auth/${mode === "login" ? "login" : "register"}`, {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: form.get("name"), email: form.get("email"), password: form.get("password") }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "Unable to continue.");
      router.push("/setup");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Unable to continue."); } finally { setSaving(false); }
  }

  return <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100"><div className="mx-auto max-w-md"><Link href="/" className="text-sm font-semibold text-cyan-400">← RubriCheck AI</Link><h1 className="mt-8 text-4xl font-bold">{mode === "login" ? "Welcome back" : "Create your workspace"}</h1><p className="mt-3 text-slate-400">Your courses, scans, and grading records stay private to your account.</p><p className="mt-6 rounded-lg border border-cyan-400/25 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100">{notice}</p><form onSubmit={submit} className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-6">{mode === "register" && <input required name="name" minLength={2} placeholder="Your name" className="field"/>}<input required name="email" type="email" placeholder="teacher@example.com" className={mode === "register" ? "field mt-3" : "field"}/><input required name="password" type="password" minLength={mode === "register" ? 10 : 1} placeholder="Password" className="field mt-3"/><button disabled={saving} className="button mt-5 w-full">{saving ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}</button></form><button type="button" onClick={() => { setMode((current) => current === "login" ? "register" : "login"); setNotice(mode === "login" ? "Create an account to begin." : "Sign in to access your private teacher workspace."); }} className="mt-5 text-sm font-semibold text-cyan-400">{mode === "login" ? "New to RubriCheck? Create an account" : "Already have an account? Sign in"}</button></div></main>;
}
