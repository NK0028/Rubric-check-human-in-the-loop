"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Result = { question_number: number; question_prompt: string; awarded_total: number; maximum_marks: number; teacher_feedback: string | null };
type Report = { exam_id: number; exam_title: string; awarded_total: number; maximum_marks: number; finalized_questions: number; total_questions: number; results: Result[] };
type Portal = { course_title: string; student_name: string; student_identifier: string; reports: Report[] };

export default function StudentPortalPage() {
  const [report, setReport] = useState<Portal | null>(null);
  const [notice, setNotice] = useState("Enter the course code, portal access code, and your student ID.");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch(`${apiUrl}/api/student-portal/results`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ course_code: form.get("course_code"), portal_code: form.get("portal_code"), student_identifier: form.get("student_identifier") }) });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "Could not load results.");
      setReport(body); setNotice(body.reports.length ? "Your finalized results are ready." : "Your teacher has not published finalized results yet.");
    } catch (error) { setReport(null); setNotice(error instanceof Error ? error.message : "Could not load results."); }
  }

  return <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100"><div className="mx-auto max-w-3xl"><Link href="/" className="text-sm font-semibold text-cyan-400">← RubriCheck AI</Link><h1 className="mt-6 text-4xl font-bold">Student results portal</h1><p className="mt-2 text-slate-400">View your teacher-finalized marks and feedback. No account is required.</p><p className="mt-6 rounded-lg border border-cyan-400/25 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100">{notice}</p><form onSubmit={submit} className="mt-6 grid gap-3 rounded-xl border border-slate-800 bg-slate-900 p-6"><input required name="course_code" placeholder="Course code, e.g. DAA-401" className="field"/><input required name="portal_code" placeholder="Portal access code from your teacher" className="field"/><input required name="student_identifier" placeholder="Your student ID" className="field"/><button className="button w-fit">View my results</button></form>{report && <section className="mt-6 space-y-5"><div><h2 className="text-2xl font-semibold">{report.student_name}</h2><p className="text-slate-400">{report.course_title} · {report.student_identifier}</p></div>{report.reports.map((exam) => <article key={exam.exam_id} className="rounded-xl border border-slate-800 bg-slate-900 p-6"><div className="flex items-center justify-between gap-4"><div><h3 className="text-xl font-semibold">{exam.exam_title}</h3><p className="mt-1 text-sm text-slate-400">{exam.finalized_questions} of {exam.total_questions} questions finalized</p></div><p className="text-xl font-bold text-cyan-300">{exam.awarded_total} / {exam.maximum_marks}</p></div><div className="mt-5 space-y-3">{exam.results.map((result) => <div key={result.question_number} className="rounded-lg border border-slate-800 bg-slate-950 p-4"><p className="font-semibold">Q{result.question_number}: {result.awarded_total} / {result.maximum_marks}</p><p className="mt-1 text-sm text-slate-400">{result.question_prompt}</p>{result.teacher_feedback && <p className="mt-3 text-sm text-cyan-100">Feedback: {result.teacher_feedback}</p>}</div>)}</div></article>)}</section>}</div></main>;
}
