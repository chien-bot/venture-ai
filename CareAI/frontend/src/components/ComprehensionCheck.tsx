import { CheckCircle2, CircleAlert, GraduationCap, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchComprehensionCheck, submitComprehensionCheck } from "../api";
import type { ComprehensionCheckResult } from "../types";

type Answers = { meaning_answer: string; boundary_answer: string; action_answer: string };
const emptyAnswers: Answers = { meaning_answer: "", boundary_answer: "", action_answer: "" };

export function ComprehensionCheck({ reportId, userId, onStatusChange }: { reportId: number | null; userId: string; onStatusChange: (passed: boolean) => void }) {
  const [answers, setAnswers] = useState<Answers>(emptyAnswers);
  const [result, setResult] = useState<ComprehensionCheckResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [localAttempts, setLocalAttempts] = useState(0);

  useEffect(() => {
    setAnswers(emptyAnswers); setResult(null); setError(null); setLocalAttempts(0);
    onStatusChange(false);
    if (!reportId) return;
    void fetchComprehensionCheck(reportId, userId).then((saved) => { setResult(saved); onStatusChange(Boolean(saved?.passed)); }).catch(() => undefined);
  }, [reportId, userId, onStatusChange]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (Object.values(answers).some((value) => !value)) { setError("请完成三个问题后再检查理解。"); return; }
    setSubmitting(true); setError(null);
    try {
      const next = reportId
        ? await submitComprehensionCheck(reportId, userId, answers)
        : buildLocalResult(userId, answers, localAttempts + 1);
      if (!reportId) setLocalAttempts(next.attempts);
      setResult(next); onStatusChange(next.passed);
    }
    catch { setError("理解检查暂时无法保存，请稍后重试。"); }
    finally { setSubmitting(false); }
  }

  return <section className="mt-6 rounded-3xl bg-slate-950 p-6 text-white shadow-xl shadow-slate-900/10 sm:p-7">
    <div className="flex items-start gap-3"><span className="grid size-10 shrink-0 place-items-center rounded-xl bg-cyan-300/15 text-cyan-200"><GraduationCap size={21} /></span><div><h2 className="font-bold">确认你真正理解了报告</h2><p className="mt-1 text-sm leading-6 text-slate-300">三题全部正确后再开始行动。答错不会影响报告，只会显示更清楚的解释。{!reportId && " 本次检查只保留在当前页面。"}</p></div></div>
    {result ? <div className="mt-5">
      <div className={`flex items-center gap-3 rounded-2xl p-4 ${result.passed ? "bg-emerald-400/10 text-emerald-100" : "bg-amber-300/10 text-amber-100"}`}>{result.passed ? <CheckCircle2 /> : <CircleAlert />}<div><p className="font-semibold">{result.passed ? "理解确认通过" : `本次答对 ${result.score}/3 题`}</p><p className="text-xs opacity-75">第 {result.attempts} 次检查</p></div></div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">{result.feedback.map((item) => <article key={item.question} className="rounded-2xl border border-white/10 bg-white/5 p-4"><p className={`text-xs font-bold ${item.correct ? "text-emerald-300" : "text-amber-300"}`}>{item.question} · {item.correct ? "正确" : "需要再看"}</p><p className="mt-2 text-sm leading-6 text-slate-200">{item.explanation}</p></article>)}</div>
      {!result.passed && <button onClick={() => { setResult(null); setAnswers(emptyAnswers); onStatusChange(false); }} className="mt-4 inline-flex items-center gap-2 rounded-xl border border-white/20 px-4 py-2 text-sm font-semibold hover:bg-white/10"><RotateCcw size={15} />重新回答</button>}
    </div> : <form onSubmit={submit} className="mt-6 space-y-5">
      <Question legend="1. 这份报告表示什么？" name="meaning_answer" value={answers.meaning_answer} onChange={(value) => setAnswers((current) => ({ ...current, meaning_answer: value }))} options={[["health_education", "健康教育与生活方式提示"], ["medical_diagnosis", "已经完成医疗诊断"], ["guaranteed_outcome", "保证改善健康结果"]]} />
      <Question legend="2. 如果记录持续明显异常或伴随不适，应该怎么做？" name="boundary_answer" value={answers.boundary_answer} onChange={(value) => setAnswers((current) => ({ ...current, boundary_answer: value }))} options={[["repeat_and_seek_help", "复测，并在需要时咨询线下专业人员"], ["change_medicine", "自己调整药物"], ["ignore_all_results", "完全忽略"]]} />
      <Question legend="3. 计划开始时最合适的做法是什么？" name="action_answer" value={answers.action_answer} onChange={(value) => setAnswers((current) => ({ ...current, action_answer: value }))} options={[["choose_one_small_step", "先选择一个低负担行动"], ["complete_everything_today", "今天完成全部七天任务"], ["wait_for_diagnosis", "等待系统给出诊断"]]} />
      {error && <p className="text-sm text-amber-200">{error}</p>}
      <button disabled={submitting} className="rounded-xl bg-cyan-300 px-5 py-2.5 text-sm font-bold text-slate-950 transition hover:bg-cyan-200 disabled:opacity-60">{submitting ? "正在检查" : "检查我的理解"}</button>
    </form>}
  </section>;
}

function Question({ legend, name, value, onChange, options }: { legend: string; name: string; value: string; onChange: (value: string) => void; options: string[][] }) {
  return <fieldset><legend className="text-sm font-semibold text-white">{legend}</legend><div className="mt-2 grid gap-2 md:grid-cols-3">{options.map(([optionValue, label]) => <label key={optionValue} className={`cursor-pointer rounded-xl border px-3 py-3 text-sm transition ${value === optionValue ? "border-cyan-300 bg-cyan-300/10 text-white" : "border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"}`}><input className="mr-2 accent-cyan-300" type="radio" name={name} value={optionValue} checked={value === optionValue} onChange={() => onChange(optionValue)} />{label}</label>)}</div></fieldset>;
}

function buildLocalResult(userId: string, answers: Answers, attempts: number): ComprehensionCheckResult {
  const checks = [
    ["报告含义", answers.meaning_answer === "health_education", "这是健康教育和生活方式提示，不是医疗结论。"],
    ["安全边界", answers.boundary_answer === "repeat_and_seek_help", "明显异常应复测；持续异常或伴随不适时应咨询线下专业人员。"],
    ["下一步行动", answers.action_answer === "choose_one_small_step", "先选择一个低负担行动并记录执行情况，更容易判断什么有帮助。"],
  ] as const;
  const feedback = checks.map(([question, correct, explanation]) => ({ question, correct, explanation }));
  const score = feedback.filter((item) => item.correct).length;
  return { report_id: 0, user_id: userId, score, passed: score === 3, attempts, feedback, submitted_at: new Date().toISOString() };
}
