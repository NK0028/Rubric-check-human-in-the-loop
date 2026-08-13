"use client";

import Link from "next/link";
import { ChangeEvent, FormEvent, useEffect, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Course = { id: number; title: string; code: string };
type Exam = { id: number; title: string };
type Student = { id: number; name: string; identifier: string };
type RosterProgress = { total_students: number; students_with_missing_submissions: number; students: { student_id: number; name: string; identifier: string; submitted_questions: number; finalized_questions: number; missing_question_numbers: number[] }[] };

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail ?? "Request failed.");
  return body as T;
}

export default function RosterPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [exams, setExams] = useState<Exam[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [progress, setProgress] = useState<RosterProgress | null>(null);
  const [courseId, setCourseId] = useState("");
  const [examId, setExamId] = useState("");
  const [notice, setNotice] = useState("Choose a course, then add students or inspect an exam for missing submissions.");

  useEffect(() => { api<Course[]>("/api/courses").then(setCourses).catch((error) => setNotice(error.message)); }, []);

  async function selectCourse(event: ChangeEvent<HTMLSelectElement>) {
    const value = event.target.value;
    setCourseId(value); setExamId(""); setProgress(null); setExams([]); setStudents([]);
    if (!value) return;
    try {
      const [loadedExams, loadedStudents] = await Promise.all([api<Exam[]>(`/api/courses/${value}/exams`), api<Student[]>(`/api/courses/${value}/students`)]);
      setExams(loadedExams); setStudents(loadedStudents);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not load roster."); }
  }

  async function addStudent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!courseId) return;
    const form = new FormData(event.currentTarget);
    try {
      const student = await api<Student>(`/api/courses/${courseId}/students`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: form.get("name"), identifier: form.get("identifier") }) });
      setStudents((items) => [...items, student].sort((a, b) => a.name.localeCompare(b.name)));
      event.currentTarget.reset(); setNotice(`${student.name} added to the roster.`);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not add student."); }
  }

  async function selectExam(event: ChangeEvent<HTMLSelectElement>) {
    const value = event.target.value;
    setExamId(value); setProgress(null);
    if (!value) return;
    try {
      const loaded = await api<RosterProgress>(`/api/exams/${value}/roster-progress`);
      setProgress(loaded);
      setNotice(loaded.students_with_missing_submissions ? `${loaded.students_with_missing_submissions} student(s) have missing submissions.` : "Every rostered student has submitted every question.");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not load missing-submission status."); }
  }

  return <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100"><div className="mx-auto max-w-6xl">
    <Link href="/" className="text-sm font-semibold text-cyan-400">← RubriCheck AI</Link>
    <h1 className="mt-6 text-4xl font-bold">Student roster</h1>
    <p className="mt-2 text-slate-400">Use the same student ID here and on every answer-sheet upload to track missing work.</p>
    <p className="mt-6 rounded-lg border border-cyan-400/25 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100">{notice}</p>
    <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-6"><select value={courseId} onChange={selectCourse} className="field"><option value="">Select course</option>{courses.map((course) => <option key={course.id} value={course.id}>{course.code} — {course.title}</option>)}</select>{courseId && <><form onSubmit={addStudent} className="mt-4 grid gap-3 md:grid-cols-[1fr_1fr_auto]"><input required name="name" placeholder="Student name" className="field"/><input required name="identifier" placeholder="Roll number / student ID" className="field"/><button className="button">Add student</button></form><p className="mt-3 text-sm text-slate-400">Rostered students: {students.length}</p></>}</section>
    {courseId && <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-6"><h2 className="text-xl font-semibold">Missing-submission tracking</h2><select value={examId} onChange={selectExam} className="field mt-4"><option value="">Select exam</option>{exams.map((exam) => <option key={exam.id} value={exam.id}>{exam.title}</option>)}</select>{progress && <div className="mt-5 overflow-x-auto"><p className="mb-3 text-sm text-slate-400">Roster: {progress.total_students} · Missing work: {progress.students_with_missing_submissions}</p><table className="min-w-full text-left text-sm"><thead className="border-b border-slate-800 text-slate-400"><tr><th className="py-3">Student</th><th>Submitted</th><th>Finalized</th><th>Missing questions</th></tr></thead><tbody>{progress.students.map((student) => <tr key={student.student_id} className="border-b border-slate-800"><td className="py-3"><p className="font-semibold">{student.name}</p><p className="text-slate-400">{student.identifier}</p></td><td>{student.submitted_questions}</td><td>{student.finalized_questions}</td><td className={student.missing_question_numbers.length ? "text-amber-300" : "text-cyan-300"}>{student.missing_question_numbers.length ? student.missing_question_numbers.map((number) => `Q${number}`).join(", ") : "Complete"}</td></tr>)}</tbody></table></div>}</section>}
  </div></main>;
}
