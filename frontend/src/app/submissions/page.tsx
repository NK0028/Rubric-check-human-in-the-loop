"use client";

import Link from "next/link";
import { ChangeEvent, FormEvent, useEffect, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Course = { id: number; title: string; code: string };
type Exam = { id: number; title: string };
type Question = { id: number; question_number: number; prompt: string; max_marks: number };
type Submission = { id: number; student_name: string; student_identifier: string | null; original_filename: string; status: string; extracted_text: string | null; file_url: string };
type Evaluation = { id: number; suggested_total: number; maximum_marks: number; method: string; status: string; criteria: { id: number; criterion_title: string; maximum_marks: number; awarded_marks: number; evidence: string; confidence: string }[] };
type FinalEvaluation = { awarded_total: number; maximum_marks: number; teacher_feedback: string | null; criteria: { criterion_title: string; maximum_marks: number; awarded_marks: number; teacher_note: string | null }[] };

const statusLabel: Record<string, string> = {
  ocr_complete: "OCR draft ready",
  ocr_no_text: "OCR found no text",
  ocr_unavailable: "OCR needs setup",
  ocr_failed: "OCR needs review",
  transcribed: "Transcript reviewed",
  suggested: "Score suggested",
  finalized: "Final marks recorded",
};

async function api<T>(path: string): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`);
  if (!response.ok) throw new Error("Could not load the requested data.");
  return response.json() as Promise<T>;
}

export default function SubmissionsPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [exams, setExams] = useState<Exam[]>([]);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [courseId, setCourseId] = useState("");
  const [examId, setExamId] = useState("");
  const [questionId, setQuestionId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [selectedSubmission, setSelectedSubmission] = useState<Submission | null>(null);
  const [transcript, setTranscript] = useState("");
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [teacherMarks, setTeacherMarks] = useState<Record<number, number>>({});
  const [teacherFeedback, setTeacherFeedback] = useState("");
  const [finalization, setFinalization] = useState<FinalEvaluation | null>(null);
  const [notice, setNotice] = useState("Select the question the scanned answer belongs to.");
  const [uploading, setUploading] = useState(false);
  const [runningOcr, setRunningOcr] = useState(false);

  useEffect(() => { api<Course[]>("/api/courses").then(setCourses).catch((error) => setNotice(error.message)); }, []);

  async function selectCourse(event: ChangeEvent<HTMLSelectElement>) {
    const value = event.target.value;
    setCourseId(value); setExamId(""); setQuestionId(""); setExams([]); setQuestions([]); setSubmissions([]); setSelectedSubmission(null); setEvaluation(null); setFinalization(null);
    if (!value) return;
    try { setExams(await api<Exam[]>(`/api/courses/${value}/exams`)); } catch (error) { setNotice(error instanceof Error ? error.message : "Could not load exams."); }
  }

  async function selectExam(event: ChangeEvent<HTMLSelectElement>) {
    const value = event.target.value;
    setExamId(value); setQuestionId(""); setQuestions([]); setSubmissions([]); setSelectedSubmission(null); setEvaluation(null); setFinalization(null);
    if (!value) return;
    try { setQuestions(await api<Question[]>(`/api/exams/${value}/questions`)); } catch (error) { setNotice(error instanceof Error ? error.message : "Could not load questions."); }
  }

  async function selectQuestion(event: ChangeEvent<HTMLSelectElement>) {
    const value = event.target.value;
    setQuestionId(value); setSubmissions([]); setSelectedSubmission(null); setEvaluation(null); setFinalization(null);
    if (!value) return;
    try { setSubmissions(await api<Submission[]>(`/api/questions/${value}/submissions`)); } catch (error) { setNotice(error instanceof Error ? error.message : "Could not load submissions."); }
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!questionId || !file) return setNotice("Select a question and scan before uploading.");
    const form = new FormData(event.currentTarget);
    form.append("question_id", questionId);
    form.append("file", file);
    setUploading(true);
    try {
      const response = await fetch(`${apiUrl}/api/submissions`, { method: "POST", body: form });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "Upload failed.");
      setSubmissions((items) => [body as Submission, ...items]);
      setFile(null); event.currentTarget.reset();
      setNotice(`${body.original_filename} was added to the review queue.`);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Upload failed."); } finally { setUploading(false); }
  }

  async function beginReview(submission: Submission) {
    setSelectedSubmission(submission);
    setTranscript(submission.extracted_text ?? "");
    setEvaluation(null); setFinalization(null); setTeacherFeedback("");
    setNotice(submission.extracted_text ? `Local OCR filled a draft transcript for ${submission.student_name}. Review it against the scan before saving.` : `Review the scan, then enter a transcript for ${submission.student_name}.`);
    if (submission.status !== "finalized") return;
    try {
      const finalMarks = await api<FinalEvaluation>(`/api/submissions/${submission.id}/final-evaluation`);
      setFinalization(finalMarks);
      setNotice(`Final marks for ${submission.student_name} are shown below as a read-only record.`);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not load final marks."); }
  }

  async function saveTranscript() {
    if (!selectedSubmission || transcript.trim().length < 2) return setNotice("Enter at least a short reviewed transcript.");
    try {
      const response = await fetch(`${apiUrl}/api/submissions/${selectedSubmission.id}/extraction`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ extracted_text: transcript }) });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "Could not save transcript.");
      setSelectedSubmission(body as Submission); setSubmissions((items) => items.map((item) => item.id === body.id ? body : item));
      setNotice("Reviewed transcript saved. You can now request a mark suggestion.");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not save transcript."); }
  }

  async function retryOcr() {
    if (!selectedSubmission) return;
    setRunningOcr(true);
    try {
      const response = await fetch(`${apiUrl}/api/submissions/${selectedSubmission.id}/ocr`, { method: "POST" });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "Could not run local OCR.");
      const updated = body as Submission;
      setSelectedSubmission(updated); setTranscript(updated.extracted_text ?? "");
      setSubmissions((items) => items.map((item) => item.id === updated.id ? updated : item));
      setNotice(updated.extracted_text ? "Local OCR refreshed the draft transcript. Review it against the scan before saving." : "OCR finished without a usable draft. You can transcribe the scan manually.");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not run local OCR."); } finally { setRunningOcr(false); }
  }

  async function createSuggestion() {
    if (!selectedSubmission) return setNotice("Choose a submission first.");
    if (!selectedSubmission.extracted_text && transcript.trim().length < 2) return setNotice("Save the transcript before requesting a score suggestion.");
    try {
      const response = await fetch(`${apiUrl}/api/submissions/${selectedSubmission.id}/evaluate`, { method: "POST" });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "Could not create suggestion.");
      const suggested = body as Evaluation;
      setEvaluation(suggested); setTeacherMarks(Object.fromEntries(suggested.criteria.map((criterion) => [criterion.id, criterion.awarded_marks]))); setFinalization(null);
      setNotice("Score suggestion ready. Adjust any criterion marks, then record the teacher-approved result.");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not create suggestion."); }
  }

  async function finalizeEvaluation() {
    if (!evaluation || !selectedSubmission) return;
    try {
      const response = await fetch(`${apiUrl}/api/evaluations/${evaluation.id}/finalize`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ criteria: evaluation.criteria.map((criterion) => ({ evaluation_criterion_id: criterion.id, awarded_marks: Number(teacherMarks[criterion.id] ?? criterion.awarded_marks) })), teacher_feedback: teacherFeedback || null }) });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "Could not record final marks.");
      setFinalization(body as FinalEvaluation);
      const updated = { ...selectedSubmission, status: "finalized" };
      setSelectedSubmission(updated); setSubmissions((items) => items.map((item) => item.id === updated.id ? updated : item));
      setNotice("Final marks have been recorded.");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not record final marks."); }
  }

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100">
      <div className="mx-auto max-w-5xl"><Link href="/" className="text-sm font-semibold text-cyan-400">← RubriCheck AI</Link>
        <div className="mt-6 flex flex-wrap items-end justify-between gap-4"><div><h1 className="text-4xl font-bold">Answer-sheet intake</h1><p className="mt-2 text-slate-400">Upload a scan for one question. Local Tesseract OCR creates a draft for teacher review.</p></div><Link href="/setup" className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold">Set up a rubric</Link></div>
        <p className="mt-6 rounded-lg border border-cyan-400/25 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100">{notice}</p>

        <section className="mt-8 rounded-xl border border-slate-800 bg-slate-900 p-6"><h2 className="text-xl font-semibold">Choose the question</h2><div className="mt-4 grid gap-3 md:grid-cols-3">
          <select value={courseId} onChange={selectCourse} className="field"><option value="">Select course</option>{courses.map((course) => <option key={course.id} value={course.id}>{course.code} — {course.title}</option>)}</select>
          <select value={examId} onChange={selectExam} disabled={!courseId} className="field"><option value="">Select exam</option>{exams.map((exam) => <option key={exam.id} value={exam.id}>{exam.title}</option>)}</select>
          <select value={questionId} onChange={selectQuestion} disabled={!examId} className="field"><option value="">Select question</option>{questions.map((question) => <option key={question.id} value={question.id}>Q{question.question_number} — {question.max_marks} marks</option>)}</select>
        </div>{questionId && <p className="mt-4 text-sm text-slate-400">{questions.find((question) => question.id === Number(questionId))?.prompt}</p>}</section>

        <form onSubmit={upload} className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-6"><h2 className="text-xl font-semibold">Upload a student answer</h2><div className="mt-5 grid gap-3 md:grid-cols-2"><input required name="student_name" placeholder="Student name" className="field" /><input name="student_identifier" placeholder="Roll number (optional)" className="field" /></div><label className="mt-4 block rounded-lg border border-dashed border-slate-600 bg-slate-950 p-6 text-center text-sm text-slate-400"><input required type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className="block w-full text-sm text-slate-300" />{file && <span className="mt-3 block text-cyan-300">Ready: {file.name}</span>}</label><button disabled={uploading || !questionId} className="button mt-5">{uploading ? "Uploading…" : "Add to review queue"}</button></form>

        <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-6"><h2 className="text-xl font-semibold">Review queue</h2>{submissions.length === 0 ? <p className="mt-4 text-slate-400">No submissions loaded for this question yet.</p> : <div className="mt-4 divide-y divide-slate-800">{submissions.map((submission) => <div key={submission.id} className="flex flex-wrap items-center justify-between gap-3 py-4"><div><p className="font-semibold">{submission.student_name} {submission.student_identifier && <span className="text-slate-400">· {submission.student_identifier}</span>}</p><p className="text-sm text-slate-400">{submission.original_filename}</p></div><div className="flex items-center gap-3"><span className="rounded-full bg-amber-400/15 px-3 py-1 text-sm text-amber-300">{statusLabel[submission.status] ?? submission.status}</span><a href={`${apiUrl}${submission.file_url}`} target="_blank" rel="noreferrer" className="text-sm font-semibold text-cyan-400">View scan</a><button type="button" onClick={() => beginReview(submission)} className="text-sm font-semibold text-cyan-400">Review</button></div></div>)}</div>}</section>

        {selectedSubmission && <section className="mt-6 rounded-xl border border-cyan-400/30 bg-slate-900 p-6"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-semibold">Transcript and score suggestion</h2><p className="mt-1 text-sm text-slate-400">{selectedSubmission.student_name} · {selectedSubmission.original_filename}</p></div><a href={`${apiUrl}${selectedSubmission.file_url}`} target="_blank" rel="noreferrer" className="text-sm font-semibold text-cyan-400">Open scan ↗</a></div><p className="mt-5 text-sm text-amber-200">Tesseract runs locally and its text is only a draft—verify and correct it against the scan before saving.</p><textarea value={transcript} onChange={(event) => setTranscript(event.target.value)} placeholder="Reviewed text from the student's answer…" disabled={selectedSubmission.status === 'finalized'} className="field mt-3 min-h-40" /><div className="mt-4 flex flex-wrap gap-3">{!['transcribed', 'suggested', 'finalized'].includes(selectedSubmission.status) && <button type="button" onClick={retryOcr} disabled={runningOcr} className="rounded-lg border border-slate-700 px-4 py-3 font-semibold text-slate-200">{runningOcr ? "Running local OCR…" : "Run local OCR again"}</button>}<button type="button" onClick={saveTranscript} disabled={selectedSubmission.status === 'finalized'} className="button">Save reviewed transcript</button><button type="button" onClick={createSuggestion} disabled={selectedSubmission.status === 'finalized'} className="rounded-lg border border-cyan-400 px-4 py-3 font-semibold text-cyan-300">Generate score suggestion</button></div>{evaluation && <div className="mt-6 rounded-lg border border-slate-700 bg-slate-950 p-5"><div className="flex items-center justify-between"><div><p className="font-semibold">Suggested score</p><p className="text-sm text-slate-400">Method: {evaluation.method.replace("_", " ")} · teacher approval required</p></div><p className="text-3xl font-bold text-cyan-400">{evaluation.suggested_total}<span className="text-base text-slate-400"> / {evaluation.maximum_marks}</span></p></div><div className="mt-4 space-y-3">{evaluation.criteria.map((criterion) => <div key={criterion.id} className="rounded-lg border border-slate-800 p-3"><div className="flex flex-wrap items-center justify-between gap-3"><span className="font-medium">{criterion.criterion_title}</span><label className="flex items-center gap-2 text-cyan-300"><input type="number" min="0" max={criterion.maximum_marks} step="0.5" value={teacherMarks[criterion.id] ?? criterion.awarded_marks} onChange={(event) => setTeacherMarks((marks) => ({ ...marks, [criterion.id]: Number(event.target.value) }))} disabled={Boolean(finalization)} className="w-20 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-right" /> / {criterion.maximum_marks}</label></div><p className="mt-1 text-sm text-slate-400">{criterion.evidence}</p></div>)}</div>{finalization ? <p className="mt-5 rounded-lg bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200">Final mark recorded: {finalization.awarded_total} / {finalization.maximum_marks}</p> : <div className="mt-5"><textarea value={teacherFeedback} onChange={(event) => setTeacherFeedback(event.target.value)} placeholder="Optional teacher feedback…" className="field min-h-24" /><button type="button" onClick={finalizeEvaluation} className="button mt-3">Record final marks</button></div>}</div>}{finalization && selectedSubmission.status === "finalized" && <div className="mt-6 rounded-lg border border-emerald-400/30 bg-emerald-400/5 p-5"><p className="font-semibold text-emerald-200">Teacher-approved final record</p><div className="mt-3 space-y-2">{finalization.criteria.map((criterion) => <div key={criterion.criterion_title} className="flex justify-between text-sm"><span>{criterion.criterion_title}</span><span className="text-emerald-200">{criterion.awarded_marks} / {criterion.maximum_marks}</span></div>)}</div>{finalization.teacher_feedback && <p className="mt-4 text-sm text-slate-300">Feedback: {finalization.teacher_feedback}</p>}</div>}</section>}
      </div>
    </main>
  );
}
