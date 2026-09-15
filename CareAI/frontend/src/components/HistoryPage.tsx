import { BarChart3, CalendarDays, ChevronRight, FileClock, LoaderCircle, RefreshCw, Trash2, WifiOff } from "lucide-react";
import { useState } from "react";
import { confirmWeeklyPlanDraft, createWeeklyPlanDraft } from "../api";
import { LevelBadge } from "./LevelBadge";
import type { HealthTrendPoint, ReportHistoryItem, TrendInsight, UserProfile, WeeklyPlanDraft, WeeklyReview } from "../types";

type Props = { reports: ReportHistoryItem[]; trends: HealthTrendPoint[]; insights: TrendInsight[]; weeklyReview: WeeklyReview | null; user: UserProfile; isLoading: boolean; error: string | null; onView: (report: ReportHistoryItem) => void; onDelete: (reportId: number) => Promise<void>; onRetry: () => Promise<void>; };

export function HistoryPage({ reports, trends, insights, weeklyReview, user, isLoading, error, onView, onDelete, onRetry }: Props) {
  return <main className="mx-auto max-w-5xl px-5 py-10">
    <div><p className="text-sm font-semibold text-teal-700">健康 Memory · {user.display_name}</p><h1 className="mt-2 text-3xl font-bold text-slate-950">健康时间轴与趋势</h1><p className="mt-3 text-slate-600">每次记录、风险变化与行动计划都归入同一份个人健康记忆，趋势提示不构成医疗诊断。</p></div>
    {isLoading ? <div className="mt-10 flex items-center gap-3 text-slate-600"><LoaderCircle className="animate-spin text-teal-600" />正在读取健康记忆…</div>
      : error ? <ErrorCard error={error} onRetry={onRetry} />
        : <><InsightPanel insights={insights} /><TrendPanel trends={trends} />
          {weeklyReview && <WeeklyReviewPanel review={weeklyReview} userId={user.id} />}
          <section className="mt-7"><div className="mb-4 flex items-center gap-2"><span className="grid size-8 place-items-center rounded-lg bg-slate-900 text-xs font-bold text-white">M</span><h2 className="font-bold text-slate-900">健康 Memory 时间轴</h2></div>
            <div className="space-y-4">{reports.map((item) => <article key={item.id} className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0"><div className="flex flex-wrap items-center gap-3"><h2 className="font-bold text-slate-900">健康记录 · {item.input.source === "manual" ? "手动录入" : item.input.source}</h2><LevelBadge level={item.report.risk_level} /></div><p className="mt-2 truncate text-sm text-slate-600">{item.report.summary}</p><p className="mt-3 flex items-center gap-1.5 text-xs text-slate-500"><CalendarDays size={14} />记录日期：{item.input.recorded_at} · BMI {item.assessment.bmi}</p></div>
              <div className="flex shrink-0 gap-2"><button onClick={() => onView(item)} className="inline-flex items-center justify-center gap-1 rounded-xl border border-teal-200 px-4 py-2.5 text-sm font-semibold text-teal-700 transition hover:bg-teal-50">查看报告 <ChevronRight size={16} /></button><button aria-label="删除健康记录" title="删除健康记录" onClick={() => { if (window.confirm("确定删除这条健康记录吗？对应趋势和行动计划也会一并删除。")) void onDelete(item.id); }} className="grid size-10 place-items-center rounded-xl border border-rose-200 text-rose-700 hover:bg-rose-50"><Trash2 size={16} /></button></div>
            </article>)}</div>
            {!reports.length && <div className="mt-8 flex items-center gap-3 rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-500"><FileClock className="text-slate-400" size={22} />暂未保存健康记录。完成首次分析后，健康 Memory 会从这里开始。</div>}
          </section>
        </>}
  </main>;
}

function WeeklyReviewPanel({ review, userId }: { review: WeeklyReview; userId: string }) {
  const [draft, setDraft] = useState<WeeklyPlanDraft | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  async function generate() {
    setLoading(true); setMessage(null);
    try { setDraft(await createWeeklyPlanDraft(userId)); }
    catch { setMessage("暂时无法生成 AI 计划。请确认模型服务已配置；原有计划不会被修改。"); }
    finally { setLoading(false); }
  }
  async function confirm() {
    if (!draft) return;
    setLoading(true); setMessage(null);
    try { const saved = await confirmWeeklyPlanDraft(draft.id, userId); setDraft(saved); setMessage("已确认并保存到健康 Memory。下一轮复盘可继续基于此计划调整。"); }
    catch { setMessage("暂时无法保存该计划，请稍后重试。"); }
    finally { setLoading(false); }
  }
  return <section className="mt-6 rounded-3xl border border-teal-100 bg-teal-50 p-5"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-sm font-semibold text-teal-800">本周行动复盘{review.completion_rate !== null ? " · 完成 " + review.completion_rate + "%" : ""}</p><p className="mt-2 max-w-2xl text-sm leading-6 text-teal-950">{review.summary}</p></div><button disabled={loading || Boolean(draft?.confirmed_at)} onClick={() => void generate()} className="rounded-xl bg-teal-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60">{loading ? "正在生成" : draft?.confirmed_at ? "计划已确认" : "AI 生成下周计划"}</button></div>{message && <p className="mt-4 rounded-xl bg-white/70 p-3 text-sm text-teal-900">{message}</p>}{draft && <div className="mt-5 rounded-2xl border border-teal-100 bg-white p-4"><p className="text-sm font-bold text-slate-900">下周目标：{draft.goal}</p><p className="mt-2 text-sm leading-6 text-slate-600">{draft.summary}</p><p className="mt-2 text-sm leading-6 text-teal-800">调整依据：{draft.adjustment_reason}</p><ol className="mt-4 grid gap-2 sm:grid-cols-2">{draft.tasks.map((task) => <li key={task.id} className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">第 {task.day_number} 天：{task.content.replace(/^第\d+天：?/, "")}</li>)}</ol>{!draft.confirmed_at && <button disabled={loading} onClick={() => void confirm()} className="mt-4 rounded-xl border border-teal-300 px-4 py-2 text-sm font-semibold text-teal-700 hover:bg-teal-50 disabled:opacity-60">确认并保存本计划</button>}</div>}</section>;
}

function ErrorCard({ error, onRetry }: { error: string; onRetry: () => Promise<void> }) {
  return <div className="mt-8 rounded-3xl border border-rose-200 bg-rose-50 p-6"><div className="flex gap-3 text-rose-800"><WifiOff className="mt-0.5 shrink-0" size={20} /><div><h2 className="font-bold">暂时无法读取健康记忆</h2><p className="mt-1 text-sm leading-6">{error} 请确认后端服务仍在运行后重试。</p><button onClick={() => void onRetry()} className="mt-4 inline-flex items-center gap-2 rounded-xl bg-rose-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-rose-800"><RefreshCw size={15} />重新读取</button></div></div></div>;
}

function InsightPanel({ insights }: { insights: TrendInsight[] }) {
  if (!insights.length) return null;
  return <section className="mt-8 rounded-3xl border border-cyan-100 bg-gradient-to-br from-cyan-50 to-white p-6"><p className="text-sm font-semibold text-cyan-800">AI 主动趋势提示</p><div className="mt-4 grid gap-3 md:grid-cols-2">{insights.map((insight) => <article key={insight.category + "-" + insight.title} className="rounded-2xl border border-white bg-white/90 p-4 shadow-sm"><div className="flex items-center justify-between gap-3"><h2 className="font-bold text-slate-900">{insight.title}</h2><LevelBadge level={insight.level} /></div><p className="mt-2 text-sm leading-6 text-slate-600">{insight.explanation}</p><p className="mt-3 text-sm font-medium leading-6 text-teal-800">下一步：{insight.next_step}</p></article>)}</div></section>;
}

function TrendPanel({ trends }: { trends: HealthTrendPoint[] }) {
  if (!trends.length) return null;
  const maxBmi = Math.max(...trends.map((item) => item.bmi), 1);
  const latest = trends.at(-1)!;
  const previous = trends.at(-2);
  const comparisons = [{ label: "BMI", value: latest.bmi.toFixed(1), delta: previous ? latest.bmi - previous.bmi : null, suffix: "" }, { label: "睡眠", value: latest.sleep_hours + " h", delta: previous ? latest.sleep_hours - previous.sleep_hours : null, suffix: " h" }, { label: "运动", value: latest.exercise_frequency + " 天", delta: previous ? latest.exercise_frequency - previous.exercise_frequency : null, suffix: " 天" }];
  return <section className="mt-8 rounded-3xl bg-slate-950 p-6 text-white shadow-xl shadow-slate-900/10"><div className="flex flex-wrap items-center justify-between gap-4"><div className="flex items-center gap-3"><span className="grid size-10 place-items-center rounded-xl bg-cyan-400/15 text-cyan-300"><BarChart3 size={21} /></span><div><h2 className="font-bold">健康趋势</h2><p className="text-sm text-slate-400">最近 {trends.length} 次记录的 BMI、睡眠与运动变化</p></div></div><LevelBadge level={latest.risk_level} /></div><div className="mt-6 grid gap-3 sm:grid-cols-3">{comparisons.map((item) => <article key={item.label} className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-xs text-slate-400">最新{item.label}</p><p className="mt-1 text-xl font-bold">{item.value}</p><p className={"mt-1 text-xs " + (item.delta === null ? "text-slate-500" : item.delta > 0 ? "text-amber-300" : item.delta < 0 ? "text-emerald-300" : "text-slate-400")}>{item.delta === null ? "等待下一次记录对比" : "较上次 " + (item.delta > 0 ? "+" : "") + item.delta.toFixed(1) + item.suffix}</p></article>)}</div><div className="mt-6 flex h-32 items-end gap-3">{trends.map((item) => <div key={item.report_id} className="flex min-w-0 flex-1 flex-col items-center gap-2"><span className="text-xs text-cyan-200">{item.bmi}</span><div className="w-full rounded-t-lg bg-gradient-to-t from-teal-600 to-cyan-300" style={{ height: Math.max((item.bmi / maxBmi) * 100, 15) + "%" }} /><span className="text-[10px] text-slate-400">{new Date(item.created_at).toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" })}</span></div>)}</div></section>;
}
