"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function AuthPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [notice, setNotice] = useState("Sign in to access your private teacher workspace.");
  const [saving, setSaving] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => { fetch(`${apiUrl}/api/auth/me`, { credentials: "include" }).then((response) => { if (response.ok) router.replace("/dashboard"); }).catch(() => undefined); }, [router]);

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

  return <main className="min-h-screen px-6 py-8 text-slate-100"><div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl overflow-hidden rounded-3xl border border-slate-700/70 bg-slate-950/60 shadow-2xl shadow-cyan-950/20 lg:grid-cols-[1.05fr_.95fr]"><aside className="hidden flex-col justify-between bg-gradient-to-br from-cyan-400/15 via-slate-900 to-indigo-950 p-10 lg:flex"><Link href="/" className="flex items-center gap-2 text-lg font-bold"><span className="grid h-9 w-9 place-items-center rounded-xl bg-cyan-300 text-slate-950">✓</span>RubriCheck <span className="text-cyan-300">AI</span></Link><div><p className="text-sm font-semibold uppercase tracking-[.22em] text-cyan-300">Teacher workspace</p><h2 className="mt-5 text-4xl font-bold leading-tight">Fair marking,<br/>with you in control.</h2><p className="mt-5 max-w-sm text-slate-300">Turn handwritten work into reviewed, evidence-based feedback—without losing the teacher&apos;s final word.</p></div><p className="text-sm text-slate-400">Secure sessions · Local OCR · Human-approved results</p></aside><div className="flex items-center justify-center p-6 sm:p-12"><div className="w-full max-w-md"><Link href="/" className="text-sm font-semibold text-cyan-400 lg:hidden">← RubriCheck AI</Link><p className="mt-6 text-sm font-semibold uppercase tracking-[.18em] text-cyan-300">Secure teacher access</p><h1 className="mt-3 text-4xl font-bold">{mode === "login" ? "Welcome back" : "Create your workspace"}</h1><p className="mt-3 text-slate-400">{mode === "login" ? "Sign in to continue grading with confidence." : "Start your private, teacher-led grading workspace."}</p><p className="mt-6 rounded-xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100">{notice}</p><form onSubmit={submit} className="glass-card mt-6 p-6">{mode === "register" && <><label className="text-sm font-medium text-slate-300">Full name</label><input required name="name" minLength={2} autoComplete="name" placeholder="Your name" className="field mt-2"/></>}<label className={mode === "register" ? "mt-4 block text-sm font-medium text-slate-300" : "text-sm font-medium text-slate-300"}>Email address</label><input required name="email" type="email" autoComplete="email" placeholder="teacher@example.com" className="field mt-2"/><label className="mt-4 block text-sm font-medium text-slate-300">Password</label><div className="relative mt-2"><input required name="password" type={showPassword ? "text" : "password"} autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={mode === "register" ? 10 : 1} placeholder={mode === "register" ? "At least 10 characters" : "Your password"} className="field pr-20"/><button type="button" onClick={() => setShowPassword((current) => !current)} className="absolute right-3 top-3 text-xs font-semibold text-cyan-300">{showPassword ? "Hide" : "Show"}</button></div><button disabled={saving} className="button mt-5 w-full">{saving ? "Please wait…" : mode === "login" ? "Sign in to workspace" : "Create account"}</button></form><button type="button" onClick={() => { setMode((current) => current === "login" ? "register" : "login"); setNotice(mode === "login" ? "Create an account to begin." : "Sign in to access your private teacher workspace."); }} className="mt-5 text-sm font-semibold text-cyan-400">{mode === "login" ? "New to RubriCheck? Create an account" : "Already have an account? Sign in"}</button></div></div></div></main>;
}
