"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Course = { id: number; title: string; code: string; is_archived: boolean };
type Exam = { id: number; title: string; course_id: number; description: string | null; is_archived: boolean };
type Criterion = { title: string; description: string; max_marks: number };

const defaultRubric: Criterion[] = [
  { title: "Proof / reasoning", description: "Checks whether the answer contains valid reasoning or proof.", max_marks: 2 },
  { title: "Derivation steps", description: "Checks whether the student shows the required derivation or steps.", max_marks: 2 },
  { title: "Correct conclusion", description: "Checks whether the final answer or conclusion is correct.", max_marks: 2 },
];

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, { ...options, credentials: "include", headers: { "Content-Type": "application/json", ...options?.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "Something went wrong. Please try again.");
  }
  return response.json() as Promise<T>;
}

export default function SetupPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [exams, setExams] = useState<Exam[]>([]);
  const [selectedCourse, setSelectedCourse] = useState("");
  const [selectedExam, setSelectedExam] = useState("");
  const [showArchived, setShowArchived] = useState(false);
  const [rubric, setRubric] = useState<Criterion[]>(defaultRubric);
  const [questionMaxMarks, setQuestionMaxMarks] = useState(6);
  const [notice, setNotice] = useState("Create your first course to begin.");
  const [saving, setSaving] = useState(false);
  const rubricTotal = useMemo(() => rubric.reduce((sum, item) => sum + Number(item.max_marks || 0), 0), [rubric]);

  useEffect(() => {
    request<Course[]>(`/api/courses?include_archived=${showArchived}`)
      .then((items) => { setCourses(items); setNotice(items.length ? "Choose an existing course or create a new one." : "Create your first course to begin."); })
      .catch((error) => setNotice(error instanceof Error ? error.message : "Unable to load courses."));
  }, [showArchived]);

  async function selectCourse(event: ChangeEvent<HTMLSelectElement>) {
    const value = event.target.value;
    setSelectedCourse(value); setSelectedExam(""); setExams([]);
    if (!value) return;
    try {
      const loaded = await request<Exam[]>(`/api/courses/${value}/exams?include_archived=${showArchived}`);
      setExams(loaded);
      setNotice(loaded.length ? "Choose an existing exam or create a new one." : "No exams exist for this course yet. Create one to continue.");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Unable to load exams."); }
  }

  async function createCourse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true);
    try {
      const course = await request<Course>("/api/courses", { method: "POST", body: JSON.stringify({ title: form.get("title"), code: form.get("code") }) });
      setCourses((items) => [course, ...items]);
      setSelectedCourse(String(course.id)); setSelectedExam(""); setExams([]);
      event.currentTarget.reset();
      setNotice(`${course.code} created. Now add an exam.`);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Unable to create course."); } finally { setSaving(false); }
  }

  async function createExam(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCourse) return setNotice("Choose a course first.");
    const form = new FormData(event.currentTarget);
    setSaving(true);
    try {
      const exam = await request<Exam>("/api/exams", { method: "POST", body: JSON.stringify({ course_id: Number(selectedCourse), title: form.get("title"), description: form.get("description") || null }) });
      setExams((items) => [exam, ...items]);
      setSelectedExam(String(exam.id));
      event.currentTarget.reset();
      setNotice(`${exam.title} created. Add a rubric-based question next.`);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Unable to create exam."); } finally { setSaving(false); }
  }

  async function createQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedExam) return setNotice("Choose an exam first.");
    const form = new FormData(event.currentTarget);
    const maxMarks = questionMaxMarks;
    if (rubricTotal !== maxMarks) return setNotice(`Rubric total (${rubricTotal}) must equal question marks (${maxMarks}).`);
    setSaving(true);
    try {
      await request("/api/questions", { method: "POST", body: JSON.stringify({ exam_id: Number(selectedExam), question_number: Number(form.get("question_number")), prompt: form.get("prompt"), max_marks: maxMarks, reference_answer: form.get("reference_answer") || null, rubric }) });
      event.currentTarget.reset();
      setQuestionMaxMarks(6);
      setNotice("Question and rubric saved. It is ready for answer-sheet evaluation.");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Unable to save question."); } finally { setSaving(false); }
  }

  async function updateCourse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCourse) return;
    const form = new FormData(event.currentTarget);
    setSaving(true);
    try {
      const updated = await request<Course>(`/api/courses/${selectedCourse}`, { method: "PUT", body: JSON.stringify({ title: form.get("title"), code: form.get("code") }) });
      setCourses((items) => items.map((item) => item.id === updated.id ? updated : item));
      setNotice(`${updated.code} updated.`);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Unable to update course."); } finally { setSaving(false); }
  }

  async function updateExam(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedExam) return;
    const form = new FormData(event.currentTarget);
    setSaving(true);
    try {
      const updated = await request<Exam>(`/api/exams/${selectedExam}`, { method: "PUT", body: JSON.stringify({ title: form.get("title"), description: form.get("description") || null }) });
      setExams((items) => items.map((item) => item.id === updated.id ? updated : item));
      setNotice(`${updated.title} updated.`);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Unable to update exam."); } finally { setSaving(false); }
  }

  async function setArchive(kind: "courses" | "exams", id: string, isArchived: boolean) {
    try {
      const updated = await request<Course | Exam>(`/api/${kind}/${id}/archive`, { method: "PATCH", body: JSON.stringify({ is_archived: isArchived }) });
      if (kind === "courses") { setCourses((items) => items.map((item) => item.id === updated.id ? updated as Course : item)); setSelectedCourse(""); setSelectedExam(""); setExams([]); }
      else { setExams((items) => items.map((item) => item.id === updated.id ? updated as Exam : item)); setSelectedExam(""); }
      setNotice(`${kind === "courses" ? "Course" : "Exam"} ${isArchived ? "archived" : "restored"}.`);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Unable to update archive status."); }
  }

  function updateCriterion(index: number, key: keyof Criterion, value: string) {
    setRubric((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, [key]: key === "max_marks" ? Number(value) : value } : item));
  }

  const course = courses.find((item) => item.id === Number(selectedCourse));
  const exam = exams.find((item) => item.id === Number(selectedExam));

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100">
      <div className="mx-auto max-w-5xl">
        <Link href="/" className="text-sm font-semibold text-cyan-400">← RubriCheck AI</Link>
        <h1 className="mt-6 text-4xl font-bold">Set up an exam rubric</h1>
        <p className="mt-3 max-w-2xl text-slate-400">Each question gets its own teacher-defined criteria. AI will later score against these criteria and ask you to approve the result.</p>
        <p className="mt-6 rounded-lg border border-cyan-400/25 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100">{notice}</p><label className="mt-4 flex w-fit items-center gap-2 text-sm text-slate-300"><input type="checkbox" checked={showArchived} onChange={(event) => { setShowArchived(event.target.checked); setSelectedCourse(""); setSelectedExam(""); setExams([]); }} /> Show archived courses and exams</label>

        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <form onSubmit={createCourse} className="rounded-xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">1. Create course</h2>
            <input required name="title" placeholder="Design and Analysis of Algorithms" className="field mt-5" />
            <input required name="code" placeholder="DAA-401" className="field mt-3" />
            <button disabled={saving} className="button mt-5">Save course</button>
          </form>

          <form onSubmit={createExam} className="rounded-xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">2. Create exam</h2>
            <select required value={selectedCourse} onChange={selectCourse} className="field mt-5"><option value="">Select course</option>{courses.map((course) => <option key={course.id} value={course.id}>{course.code} — {course.title}</option>)}</select>
            <input required name="title" placeholder="Midterm Examination" className="field mt-3" />
            <input name="description" placeholder="Optional instructions" className="field mt-3" />
            <button disabled={saving} className="button mt-5">Save exam</button>
          </form>
        </div>

        {course && <section className="mt-6 grid gap-6 lg:grid-cols-2"><form key={course.id} onSubmit={updateCourse} className="rounded-xl border border-slate-800 bg-slate-900 p-6"><h2 className="text-xl font-semibold">Manage course</h2><input required name="title" defaultValue={course.title} className="field mt-5"/><input required name="code" defaultValue={course.code} className="field mt-3"/><div className="mt-5 flex gap-3"><button disabled={saving} className="button">Save changes</button><button type="button" onClick={() => setArchive("courses", selectedCourse, !course.is_archived)} className="rounded-lg border border-slate-700 px-4 py-3 font-semibold text-slate-200">{course.is_archived ? "Restore course" : "Archive course"}</button></div></form>{exam && <form key={exam.id} onSubmit={updateExam} className="rounded-xl border border-slate-800 bg-slate-900 p-6"><h2 className="text-xl font-semibold">Manage exam</h2><input required name="title" defaultValue={exam.title} className="field mt-5"/><input name="description" defaultValue={exam.description ?? ""} placeholder="Optional instructions" className="field mt-3"/><div className="mt-5 flex gap-3"><button disabled={saving} className="button">Save changes</button><button type="button" onClick={() => setArchive("exams", selectedExam, !exam.is_archived)} className="rounded-lg border border-slate-700 px-4 py-3 font-semibold text-slate-200">{exam.is_archived ? "Restore exam" : "Archive exam"}</button></div></form>}</section>}

        <form onSubmit={createQuestion} className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-xl font-semibold">3. Add question and marking rubric</h2>
          <div className="mt-5 grid gap-3 md:grid-cols-[1fr_120px_120px]">
            <select required value={selectedExam} onChange={(event) => setSelectedExam(event.target.value)} className="field"><option value="">Select exam</option>{exams.map((exam) => <option key={exam.id} value={exam.id}>{exam.title}</option>)}</select>
            <input required name="question_number" type="number" min="1" placeholder="Question #" className="field" />
            <input required name="max_marks" type="number" min="0.5" step="0.5" value={questionMaxMarks} onChange={(event) => setQuestionMaxMarks(Number(event.target.value))} className="field" />
          </div>
          <textarea required name="prompt" placeholder="Write the question shown to students..." className="field mt-3 min-h-28" />
          <textarea name="reference_answer" placeholder="Optional reference answer or ideal solution..." className="field mt-3 min-h-24" />

          <div className="mt-6 flex items-center justify-between"><h3 className="font-semibold">Rubric criteria</h3><span className={rubricTotal === questionMaxMarks ? "text-cyan-400" : "text-amber-300"}>Current total: {rubricTotal} / {questionMaxMarks} marks</span></div>
          <div className="mt-3 space-y-3">{rubric.map((criterion, index) => <div key={index} className="grid gap-3 rounded-lg border border-slate-800 p-3 md:grid-cols-[1fr_2fr_110px_auto]"><input value={criterion.title} onChange={(event) => updateCriterion(index, "title", event.target.value)} className="field" /><input value={criterion.description} onChange={(event) => updateCriterion(index, "description", event.target.value)} className="field" /><input value={criterion.max_marks} onChange={(event) => updateCriterion(index, "max_marks", event.target.value)} type="number" min="0.5" step="0.5" className="field" /><button type="button" onClick={() => setRubric((items) => items.filter((_, itemIndex) => itemIndex !== index))} className="text-sm text-rose-300">Remove</button></div>)}</div>
          <button type="button" onClick={() => setRubric((items) => [...items, { title: "New criterion", description: "Describe the evidence required.", max_marks: 1 }])} className="mt-4 text-sm font-semibold text-cyan-400">+ Add criterion</button>
          <button disabled={saving} className="button mt-6 block">Save question & rubric</button>
        </form>
      </div>
    </main>
  );
}
