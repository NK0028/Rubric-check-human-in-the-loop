"use client";

import Link from "next/link";
import { ChangeEvent, useEffect, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Course = { id: number; title: string; code: string };
type Event = { id: number; actor_name: string; action: string; details: string; created_at: string };

export default function ActivityPage() {
  const [courses, setCourses] = useState<Course[]>([]); const [events, setEvents] = useState<Event[]>([]); const [notice, setNotice] = useState("Choose a course to view its recent activity.");
  useEffect(() => { fetch(`${apiUrl}/api/courses`, { credentials: "include" }).then((response) => response.json()).then(setCourses).catch(() => setNotice("Sign in to view activity.")); }, []);
  async function choose(event: ChangeEvent<HTMLSelectElement>) { setEvents([]); if (!event.target.value) return; const response = await fetch(`${apiUrl}/api/courses/${event.target.value}/activity`, { credentials: "include" }); const body = await response.json(); if (!response.ok) return setNotice(body.detail ?? "Could not load activity."); setEvents(body); setNotice(body.length ? "Showing the latest 100 course events." : "No tracked activity yet."); }
  return <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100"><div className="mx-auto max-w-3xl"><Link href="/" className="text-sm font-semibold text-cyan-400">← RubriCheck AI</Link><h1 className="mt-6 text-4xl font-bold">Course activity</h1><p className="mt-2 text-slate-400">A record of shared access, roster additions, and finalized marks.</p><p className="mt-6 rounded-lg border border-cyan-400/25 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100">{notice}</p><select className="field mt-6" onChange={choose}><option value="">Select course</option>{courses.map((course) => <option key={course.id} value={course.id}>{course.code} — {course.title}</option>)}</select><div className="mt-6 divide-y divide-slate-800 rounded-xl border border-slate-800 bg-slate-900 px-6">{events.map((item) => <article key={item.id} className="py-4"><p className="font-semibold">{item.actor_name} <span className="font-normal text-slate-300">{item.action}</span></p><p className="mt-1 text-sm text-slate-400">{item.details}</p><p className="mt-2 text-xs text-slate-500">{new Date(item.created_at).toLocaleString()}</p></article>)}</div></div></main>;
}
