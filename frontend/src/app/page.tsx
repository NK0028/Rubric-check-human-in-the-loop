import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100">
      <div className="mx-auto max-w-6xl">
        <nav className="mb-14 flex items-center justify-between">
          <span className="text-xl font-bold tracking-tight">RubriCheck <span className="text-cyan-400">AI</span></span>
          <span className="rounded-full border border-slate-700 px-3 py-1 text-sm text-slate-300">Teacher workspace</span>
        </nav>

        <section className="grid gap-10 lg:grid-cols-[1.25fr_0.75fr] lg:items-center">
          <div>
            <p className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-cyan-400">Human-in-the-loop grading</p>
            <h1 className="max-w-3xl text-5xl font-bold tracking-tight sm:text-6xl">Fairer feedback. Less marking time.</h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">Create question-specific rubrics, review handwritten answers, and approve evidence-based AI mark suggestions—without giving up teacher control.</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/setup" className="rounded-lg bg-cyan-400 px-5 py-3 font-semibold text-slate-950">Create an exam</Link>
              <Link href="/submissions" className="rounded-lg border border-slate-700 px-5 py-3 font-semibold text-slate-200">Upload answer sheets</Link>
              <Link href="/results" className="rounded-lg border border-slate-700 px-5 py-3 font-semibold text-slate-200">View results</Link>
              <Link href="/dashboard" className="rounded-lg border border-slate-700 px-5 py-3 font-semibold text-slate-200">Review dashboard</Link>
              <Link href="/roster" className="rounded-lg border border-slate-700 px-5 py-3 font-semibold text-slate-200">Student roster</Link>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl shadow-cyan-950/40">
            <div className="mb-6 flex items-center justify-between"><span className="font-semibold">Algorithm Analysis — Q3</span><span className="rounded-full bg-amber-400/15 px-3 py-1 text-sm text-amber-300">Review needed</span></div>
            <div className="space-y-4">
              {[['Proof / reasoning', '1.5 / 2'], ['Derivation steps', '2 / 2'], ['Correct conclusion', '2 / 2']].map(([criterion, score]) => (
                <div key={criterion} className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                  <div className="flex justify-between font-medium"><span>{criterion}</span><span className="text-cyan-400">{score}</span></div>
                  <p className="mt-2 text-sm text-slate-400">Evidence detected and ready for teacher review.</p>
                </div>
              ))}
            </div>
            <div className="mt-5 flex items-center justify-between border-t border-slate-800 pt-5"><span className="text-slate-400">Suggested score</span><span className="text-2xl font-bold">5.5 <span className="text-base text-slate-400">/ 6</span></span></div>
          </div>
        </section>

        <section className="mt-20 grid gap-4 md:grid-cols-3">
          {[['1', 'Design the rubric', 'Set marks, criteria, expected evidence, and partial-credit guidance.'], ['2', 'Upload answer sheets', 'Organize scanned submissions by exam, question, and student.'], ['3', 'Approve the result', 'Review AI suggestions, edit marks, and export final results.']].map(([number, title, description]) => (
            <article key={number} className="rounded-xl border border-slate-800 bg-slate-900/60 p-6"><span className="text-cyan-400">0{number}</span><h2 className="mt-3 text-xl font-semibold">{title}</h2><p className="mt-2 leading-7 text-slate-400">{description}</p></article>
          ))}
        </section>
      </div>
    </main>
  );
}
