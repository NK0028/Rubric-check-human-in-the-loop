"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Result = { question_number: number; question_prompt: string; awarded_total: number; maximum_marks: number; teacher_feedback: string | null };
type Report = { exam_title: string; student_name: string; student_identifier: string; awarded_total: number; maximum_marks: number; finalized_questions: number; total_questions: number; results: Result[] };

function ReportContent() {
  const params = useSearchParams();
  const examId = params.get("exam");
  const studentId = params.get("student");
  const missingParameters = !examId || !studentId;
  const [report, setReport] = useState<Report | null>(null);
  const [notice, setNotice] = useState("Loading student report…");

  useEffect(() => {
    if (missingParameters) return;
    fetch(`${apiUrl}/api/exams/${examId}/students/${studentId}/report`, { credentials: "include" })
      .then(async (response) => { const body = await response.json(); if (!response.ok) throw new Error(body.detail ?? "Could not load report."); return body as Report; })
      .then((loaded) => { setReport(loaded); setNotice(""); })
      .catch((error) => setNotice(error instanceof Error ? error.message : "Could not load report."));
  }, [examId, studentId, missingParameters]);

  return <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100 print:bg-white print:p-0 print:text-slate-950"><div className="mx-auto max-w-4xl"><div className="print:hidden"><Link href="/results" className="text-sm font-semibold text-cyan-400">← Finalized results</Link></div>{missingParameters ? <p className="mt-6 rounded-lg border border-cyan-400/25 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100 print:hidden">Choose a student from the gradebook to open a report.</p> : notice && <p className="mt-6 rounded-lg border border-cyan-400/25 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100 print:hidden">{notice}</p>}{report && <article className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-8 print:mt-0 print:border-0 print:bg-white print:p-0"><div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-700 pb-6 print:border-slate-300"><div><p className="text-sm font-semibold uppercase tracking-widest text-cyan-400 print:text-slate-600">RubriCheck AI · teacher-approved report</p><h1 className="mt-2 text-3xl font-bold">{report.exam_title}</h1><p className="mt-3 text-slate-400 print:text-slate-600">{report.student_name} · {report.student_identifier}</p></div><div className="text-right"><p className="text-sm text-slate-400 print:text-slate-600">Finalized total</p><p className="text-3xl font-bold text-cyan-300 print:text-slate-950">{report.awarded_total} <span className="text-base text-slate-400">/ {report.maximum_marks}</span></p><p className="mt-1 text-sm text-slate-400 print:text-slate-600">{report.finalized_questions} of {report.total_questions} questions finalized</p></div></div><div className="mt-6 space-y-4">{report.results.length ? report.results.map((result) => <section key={result.question_number} className="rounded-lg border border-slate-700 p-5 print:border-slate-300"><div className="flex items-start justify-between gap-4"><div><h2 className="font-semibold">Question {result.question_number}</h2><p className="mt-1 text-sm text-slate-400 print:text-slate-600">{result.question_prompt}</p></div><p className="whitespace-nowrap font-bold text-cyan-300 print:text-slate-950">{result.awarded_total} / {result.maximum_marks}</p></div><p className="mt-4 text-sm leading-6 text-slate-300 print:text-slate-700"><span className="font-semibold">Teacher feedback: </span>{result.teacher_feedback ?? "No additional feedback was recorded."}</p></section>) : <p className="rounded-lg border border-dashed border-slate-700 p-5 text-slate-400 print:border-slate-300 print:text-slate-600">No questions have been finalized for this student yet.</p>}</div><div className="mt-8 print:hidden"><button type="button" onClick={() => window.print()} className="button">Print report</button></div></article>}</div></main>;
}

export default function ReportPage() {
  return <Suspense fallback={<main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100"><div className="mx-auto max-w-4xl text-slate-400">Loading student report…</div></main>}><ReportContent /></Suspense>;
}
