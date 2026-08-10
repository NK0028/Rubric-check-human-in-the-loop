"use client";

import Link from "next/link";
import { ChangeEvent, useEffect, useMemo, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Course = { id: number; title: string; code: string };
type Exam = { id: number; title: string };
type Result = { final_evaluation_id: number; submission_id: number; student_name: string; student_identifier: string | null; question_number: number; question_prompt: string; awarded_total: number; maximum_marks: number; teacher_feedback: string | null; finalized_at: string | null };

async function api<T>(path: string): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`);
  if (!response.ok) throw new Error("Could not load results.");
  return response.json() as Promise<T>;
}

export default function ResultsPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [exams, setExams] = useState<Exam[]>([]);
  const [courseId, setCourseId] = useState("");
  const [examId, setExamId] = useState("");
  const [results, setResults] = useState<Result[]>([]);
  const [notice, setNotice] = useState("Choose an exam to view its teacher-finalized results.");

  useEffect(() => { api<Course[]>("/api/courses").then(setCourses).catch((error) => setNotice(error.message)); }, []);

  async function selectCourse(event: ChangeEvent<HTMLSelectElement>) {
    const value = event.target.value;
    setCourseId(value); setExamId(""); setExams([]); setResults([]);
    if (!value) return;
    try { setExams(await api<Exam[]>(`/api/courses/${value}/exams`)); } catch (error) { setNotice(error instanceof Error ? error.message : "Could not load exams."); }
  }

  async function selectExam(event: ChangeEvent<HTMLSelectElement>) {
    const value = event.target.value;
    setExamId(value); setResults([]);
    if (!value) return;
    try {
      const loaded = await api<Result[]>(`/api/exams/${value}/results`);
      setResults(loaded); setNotice(loaded.length ? `${loaded.length} finalized question result${loaded.length === 1 ? "" : "s"} ready for export.` : "No finalized results yet for this exam.");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not load results."); }
  }

  const average = useMemo(() => results.length ? results.reduce((sum, item) => sum + (item.awarded_total / item.maximum_marks) * 100, 0) / results.length : 0, [results]);
  const studentTotals = useMemo(() => {
    const totals = new Map<string, { name: string; identifier: string | null; awarded: number; maximum: number; questions: number }>();
    for (const result of results) {
      const key = result.student_identifier || result.student_name.toLocaleLowerCase();
      const current = totals.get(key) ?? { name: result.student_name, identifier: result.student_identifier, awarded: 0, maximum: 0, questions: 0 };
      current.awarded += result.awarded_total; current.maximum += result.maximum_marks; current.questions += 1;
      totals.set(key, current);
    }
    return [...totals.values()].sort((a, b) => a.name.localeCompare(b.name));
  }, [results]);

  return <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100"><div className="mx-auto max-w-6xl">
    <Link href="/" className="text-sm font-semibold text-cyan-400">← RubriCheck AI</Link>
    <div className="mt-6 flex flex-wrap items-end justify-between gap-4"><div><h1 className="text-4xl font-bold">Finalized results</h1><p className="mt-2 text-slate-400">Review teacher-approved marks and export them for your gradebook.</p></div><Link href="/submissions" className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold">Review submissions</Link></div>
    <p className="mt-6 rounded-lg border border-cyan-400/25 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100">{notice}</p>
    <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-6"><div className="grid gap-3 md:grid-cols-2"><select value={courseId} onChange={selectCourse} className="field"><option value="">Select course</option>{courses.map((course) => <option key={course.id} value={course.id}>{course.code} — {course.title}</option>)}</select><select value={examId} onChange={selectExam} disabled={!courseId} className="field"><option value="">Select exam</option>{exams.map((exam) => <option key={exam.id} value={exam.id}>{exam.title}</option>)}</select></div>{examId && <div className="mt-5 flex flex-wrap items-center justify-between gap-3"><div className="flex gap-6 text-sm text-slate-400"><p>Students: <span className="font-semibold text-cyan-300">{studentTotals.length}</span></p><p>Question average: <span className="font-semibold text-cyan-300">{average.toFixed(1)}%</span></p></div><a href={`${apiUrl}/api/exams/${examId}/results.csv`} className="button">Download question CSV</a></div>}</section>
    {studentTotals.length > 0 && <section className="mt-6 overflow-hidden rounded-xl border border-cyan-400/30 bg-slate-900"><div className="border-b border-slate-800 px-6 py-4"><h2 className="text-xl font-semibold">Student gradebook summary</h2><p className="mt-1 text-sm text-slate-400">Totals include every finalized question currently recorded for this exam.</p></div><div className="overflow-x-auto"><table className="min-w-full text-left text-sm"><thead className="border-b border-slate-800 bg-slate-950 text-slate-400"><tr><th className="px-5 py-3 font-medium">Student</th><th className="px-5 py-3 font-medium">Finalized questions</th><th className="px-5 py-3 font-medium">Exam total</th><th className="px-5 py-3 font-medium">Percentage</th></tr></thead><tbody>{studentTotals.map((student) => <tr key={student.identifier ?? student.name} className="border-b border-slate-800 last:border-0"><td className="px-5 py-4"><p className="font-semibold">{student.name}</p>{student.identifier && <p className="text-slate-400">{student.identifier}</p>}</td><td className="px-5 py-4">{student.questions}</td><td className="px-5 py-4 font-semibold text-cyan-300">{student.awarded} / {student.maximum}</td><td className="px-5 py-4">{((student.awarded / student.maximum) * 100).toFixed(1)}%</td></tr>)}</tbody></table></div></section>}
    <section className="mt-6 overflow-hidden rounded-xl border border-slate-800 bg-slate-900">{results.length === 0 ? <p className="p-6 text-slate-400">Finalized answers will appear here once you record final marks.</p> : <div className="overflow-x-auto"><table className="min-w-full text-left text-sm"><thead className="border-b border-slate-800 bg-slate-950 text-slate-400"><tr><th className="px-5 py-3 font-medium">Student</th><th className="px-5 py-3 font-medium">Question</th><th className="px-5 py-3 font-medium">Final mark</th><th className="px-5 py-3 font-medium">Feedback</th></tr></thead><tbody>{results.map((result) => <tr key={result.final_evaluation_id} className="border-b border-slate-800 last:border-0"><td className="px-5 py-4"><p className="font-semibold">{result.student_name}</p>{result.student_identifier && <p className="text-slate-400">{result.student_identifier}</p>}</td><td className="px-5 py-4"><p className="font-medium">Q{result.question_number}</p><p className="max-w-md truncate text-slate-400" title={result.question_prompt}>{result.question_prompt}</p></td><td className="px-5 py-4 font-semibold text-cyan-300">{result.awarded_total} / {result.maximum_marks}</td><td className="max-w-sm px-5 py-4 text-slate-400">{result.teacher_feedback ?? "—"}</td></tr>)}</tbody></table></div>}</section>
  </div></main>;
}
