"use client";

import Link from "next/link";
import { ChangeEvent, FormEvent, useEffect, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Course = { id: number; title: string; code: string };
type Collaborator = { user_id: number; name: string; email: string; role: "editor" | "viewer" };

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, { ...options, credentials: "include" });
  const body = response.status === 204 ? null : await response.json();
  if (!response.ok) throw new Error(body?.detail ?? "Request failed.");
  return body as T;
}

export default function CollaborationPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [courseId, setCourseId] = useState("");
  const [collaborators, setCollaborators] = useState<Collaborator[]>([]);
  const [notice, setNotice] = useState("Choose a course you own to invite a registered teacher.");

  useEffect(() => { api<Course[]>("/api/courses").then(setCourses).catch((error) => setNotice(error.message)); }, []);

  async function selectCourse(event: ChangeEvent<HTMLSelectElement>) {
    const value = event.target.value;
    setCourseId(value);
    setCollaborators([]);
    if (!value) return;
    try {
      setCollaborators(await api<Collaborator[]>(`/api/courses/${value}/collaborators`));
      setNotice("Editors can manage course work; viewers can review results without changing them.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not load collaborators.");
    }
  }

  async function invite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!courseId) return;
    const form = new FormData(event.currentTarget);
    try {
      const collaborator = await api<Collaborator>(`/api/courses/${courseId}/collaborators`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: form.get("email"), role: form.get("role") }),
      });
      setCollaborators((items) => [...items.filter((item) => item.user_id !== collaborator.user_id), collaborator].sort((a, b) => a.name.localeCompare(b.name)));
      event.currentTarget.reset();
      setNotice(`${collaborator.name} now has ${collaborator.role} access.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not add teacher.");
    }
  }

  async function remove(collaborator: Collaborator) {
    if (!courseId || !window.confirm(`Remove ${collaborator.name} from this course?`)) return;
    try {
      await api<void>(`/api/courses/${courseId}/collaborators/${collaborator.user_id}`, { method: "DELETE" });
      setCollaborators((items) => items.filter((item) => item.user_id !== collaborator.user_id));
      setNotice(`${collaborator.name} no longer has access.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not remove teacher.");
    }
  }

  return <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100"><div className="mx-auto max-w-3xl"><Link href="/" className="text-sm font-semibold text-cyan-400">← RubriCheck AI</Link><h1 className="mt-6 text-4xl font-bold">Course collaboration</h1><p className="mt-2 text-slate-400">Share a course without sharing your account. Invited teachers need an existing RubriCheck account.</p><p className="mt-6 rounded-lg border border-cyan-400/25 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100">{notice}</p><section className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-6"><label className="text-sm font-semibold">Course</label><select value={courseId} onChange={selectCourse} className="field mt-2"><option value="">Select a course</option>{courses.map((course) => <option key={course.id} value={course.id}>{course.code} — {course.title}</option>)}</select>{courseId && <><form onSubmit={invite} className="mt-6 border-t border-slate-800 pt-6"><h2 className="font-semibold">Add or update a teacher</h2><div className="mt-3 grid gap-3 sm:grid-cols-[1fr_140px_auto]"><input required type="email" name="email" placeholder="teacher@example.com" className="field"/><select name="role" defaultValue="editor" className="field"><option value="editor">Editor</option><option value="viewer">Viewer</option></select><button className="button">Save access</button></div></form><div className="mt-6 border-t border-slate-800 pt-6"><h2 className="font-semibold">Shared teachers</h2>{collaborators.length === 0 ? <p className="mt-3 text-sm text-slate-400">This course is not shared yet.</p> : <ul className="mt-3 divide-y divide-slate-800">{collaborators.map((collaborator) => <li key={collaborator.user_id} className="flex items-center justify-between gap-4 py-3"><div><p className="font-semibold">{collaborator.name}</p><p className="text-sm text-slate-400">{collaborator.email} · {collaborator.role}</p></div><button type="button" onClick={() => remove(collaborator)} className="text-sm text-rose-300">Remove</button></li>)}</ul>}</div></>}</section></div></main>;
}
