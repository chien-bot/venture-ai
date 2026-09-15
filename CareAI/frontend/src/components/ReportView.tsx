import { Activity, CheckCircle2, ClipboardList, HeartPulse, Lightbulb, MoonStar, Printer, ShieldAlert, Sparkles, TimerReset } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchPlan, updatePlanTask } from "../api";
import { readCompletedDays, saveCompletedDays } from "../lib/reportStorage";
import { LevelBadge } from "./LevelBadge";
import { ReportComparison } from "./ReportComparison";
import type { ActionPlanState, HealthInput, HealthReport, ReportHistoryItem, StoredHealthInput } from "../types";

type ReportViewProps = {
  report: HealthReport | null;
  input: HealthInput | StoredHealthInput | null;
  bmi: number | null;
  planStorageKey: string | null;
  previousReport: ReportHistoryItem | null;
  onStart: () => void;
  reportId: number | null;
  userId: string;
};

const riskStyle = {
  normal: "from-emerald-500 to-teal-600 shadow-emerald-500/20",
  attention: "from-amber-500 to-orange-600 shadow-amber-500/20",
  high_attention: "from-rose-500 to-red-600 shadow-rose-500/20",
};

export function ReportView({ report, input, bmi, planStorageKey, previousReport, onStart, reportId, userId }: ReportViewProps) {
  const [serverPlan, setServerPlan] = useState<ActionPlanState | null>(null);
  useEffect(() => {
    setServerPlan(null);
    if (!reportId) return;
    void fetchPlan(reportId, userId).then(setServerPlan).catch(() => undefined);
  }, [reportId, userId]);

  async function toggleServerTask(taskId: number, completed: boolean) {
    const previous = serverPlan;
    if (!previous) return;
    const completionReason = completed ? undefined : window.prompt("可选：记录这项行动未完成的原因，供下周计划复盘使用。") ?? undefined;
    setServerPlan({ ...previous, tasks: previous.tasks.map((task) => task.id === taskId ? { ...task, completed } : task) });
    try {
      const updated = await updatePlanTask(taskId, userId, completed, completionReason);
      setServerPlan((current) => current ? { ...current, tasks: current.tasks.map((task) => task.id === updated.id ? updated : task) } : current);
    } catch { setServerPlan(previous); }
  }
  if (!report) return <main className="mx-auto max-w-3xl px-5 py-20 text-center"><div className="rounded-3xl border border-dashed border-slate-300 bg-white p-10"><ClipboardList className="mx-auto text-slate-400" size={40} /><h1 className="mt-4 text-2xl font-bold text-slate-900">还没有健康报告</h1><p className="mt-3 text-slate-600">完成健康数据录入后，这里会展示你的健康风险分析结果。</p><button onClick={onStart} className="mt-6 rounded-xl bg-teal-600 px-5 py-3 font-semibold text-white">开始健康分析</button></div></main>;
  return <main className="print-report mx-auto max-w-5xl px-5 py-10">
    <div className="mb-7 flex flex-wrap items-start justify-between gap-4"><div><p className="text-sm font-semibold text-teal-700">CareAI · 健康风险报告</p><h1 className="mt-2 text-3xl font-bold text-slate-950">你的健康分析结果</h1></div><div className="no-print flex items-center gap-2"><LevelBadge level={report.risk_level} /><button type="button" onClick={() => window.print()} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-teal-300 hover:bg-teal-50"><Printer size={16} />打印 / 保存 PDF</button></div></div>
    <div className="print-only mb-4"><LevelBadge level={report.risk_level} /></div>
    <section className={`overflow-hidden rounded-3xl bg-gradient-to-br ${riskStyle[report.risk_level]} p-6 text-white shadow-xl sm:p-8`}><div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-start"><div className="max-w-2xl"><div className="flex items-center gap-2 text-white/80"><Sparkles size={18} /><span className="text-sm font-semibold">AI 健康总结</span></div><p className="mt-4 text-xl font-semibold leading-8">{report.summary}</p></div><div className="rounded-2xl border border-white/25 bg-white/10 px-4 py-3 backdrop-blur"><p className="text-xs text-white/75">当前风险等级</p><p className="mt-1 text-lg font-bold">{report.risk_level === "normal" ? "一般关注" : report.risk_level === "attention" ? "建议关注" : "重点关注"}</p></div></div></section>
    {input && <HealthMetrics input={input} bmi={bmi} />}
    {input && <ReportComparison input={input} bmi={bmi} riskLevel={report.risk_level} previousReport={previousReport} />}
    <div className="mt-6 grid gap-6 lg:grid-cols-2"><ReportCard icon={<ShieldAlert size={21} />} title="需要关注的指标"><ul className="space-y-3">{report.key_risks.map((item) => <li key={item} className="rounded-xl border border-amber-100 bg-amber-50 p-3 text-sm leading-6 text-amber-950">{item}</li>)}</ul></ReportCard><ReportCard icon={<Lightbulb size={21} />} title="健康建议"><ul className="space-y-3">{report.recommendations.map((item) => <li key={item} className="flex gap-2 text-sm leading-6 text-slate-700"><CheckCircle2 size={18} className="mt-0.5 shrink-0 text-teal-600" />{item}</li>)}</ul></ReportCard></div>
    <ActionPlan items={report.action_plan} storageKey={planStorageKey} serverPlan={serverPlan} onToggleServerTask={toggleServerTask} />
    <section className="mt-6 flex gap-3 rounded-2xl border border-sky-100 bg-sky-50 p-4 text-sm leading-6 text-sky-950"><ShieldAlert className="mt-0.5 shrink-0 text-sky-700" size={19} /><p><strong>健康免责声明：</strong>{report.safety_notice}</p></section>
  </main>;
}

function ActionPlan({ items, storageKey, serverPlan, onToggleServerTask }: { items: string[]; storageKey: string | null; serverPlan: ActionPlanState | null; onToggleServerTask: (taskId: number, completed: boolean) => Promise<void> }) {
  const [completedDays, setCompletedDays] = useState<number[]>([]);

  useEffect(() => {
    setCompletedDays(storageKey ? readCompletedDays(storageKey) : []);
  }, [storageKey]);

  function toggleDay(day: number) {
    setCompletedDays((current) => {
      const next = current.includes(day) ? current.filter((item) => item !== day) : [...current, day].sort((a, b) => a - b);
      if (storageKey) saveCompletedDays(storageKey, next);
      return next;
    });
  }

  const displayItems = serverPlan?.tasks.map((task) => task.content) ?? items;
  const completedCount = serverPlan ? serverPlan.tasks.filter((task) => task.completed).length : completedDays.length;
  const progress = Math.round((completedCount / displayItems.length) * 100);
  return <section className="mt-6 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm"><div className="border-b border-slate-100 bg-gradient-to-r from-teal-50 to-cyan-50 p-6"><div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div className="flex items-center gap-3"><span className="grid size-10 place-items-center rounded-xl bg-teal-600 text-white"><ClipboardList size={20} /></span><div><h2 className="font-bold text-slate-900">7 天行动计划</h2><p className="text-sm text-slate-500">{serverPlan ? `目标：${serverPlan.goal} · 完成情况已保存到健康 Memory` : "用一周的可执行步骤，建立长期健康习惯。"}</p></div></div><div className="min-w-40"><div className="flex items-center justify-between text-xs font-semibold text-teal-800"><span>计划进度</span><span>{completedCount}/{displayItems.length} 天</span></div><div className="mt-2 h-2 overflow-hidden rounded-full bg-teal-100"><div className="h-full rounded-full bg-teal-600 transition-all" style={{ width: `${progress}%` }} /></div></div></div></div><ol className="grid divide-y divide-slate-100 md:grid-cols-2 md:divide-x md:divide-y-0">{displayItems.map((item, index) => { const task = serverPlan?.tasks[index]; const completed = task ? task.completed : completedDays.includes(index); return <li key={task?.id ?? item}><button type="button" onClick={() => task ? void onToggleServerTask(task.id, !completed) : toggleDay(index)} aria-pressed={completed} className={`flex w-full gap-4 p-5 text-left transition ${completed ? "bg-emerald-50/70" : "hover:bg-slate-50"}`}><span className={`grid size-8 shrink-0 place-items-center rounded-full text-xs font-bold ${completed ? "bg-emerald-600 text-white" : "bg-slate-950 text-white"}`}>{completed ? <CheckCircle2 size={17} /> : `D${index + 1}`}</span><div><p className={`text-xs font-semibold uppercase tracking-wider ${completed ? "text-emerald-700" : "text-teal-700"}`}>第 {index + 1} 天 {completed && "· 已完成"}</p><p className={`mt-1 text-sm leading-6 ${completed ? "text-emerald-900 line-through decoration-emerald-400" : "text-slate-700"}`}>{item.replace(/^第\d+天：?/, "")}</p></div></button></li>; })}</ol></section>;
}

function HealthMetrics({ input, bmi }: { input: HealthInput | StoredHealthInput; bmi: number | null }) {
  const stored = "height_cm" in input;
  const sleepHours = input.sleep_hours;
  const exerciseDays = stored ? input.exercise_days_per_week : input.exercise_frequency;
  const systolic = stored ? input.systolic_bp : input.blood_pressure?.split("/")[0];
  const diastolic = stored ? input.diastolic_bp : input.blood_pressure?.split("/")[1];
  const glucose = stored ? input.fasting_blood_glucose_mmol_l : input.blood_glucose;
  const metrics = [
    { label: "BMI", value: bmi?.toFixed(1) ?? "--", detail: "身高体重计算", icon: Activity },
    { label: "睡眠", value: `${sleepHours} h`, detail: "平均每晚", icon: MoonStar },
    { label: "运动", value: `${exerciseDays} 天`, detail: "每周频率", icon: TimerReset },
    { label: "血压", value: systolic && diastolic ? `${systolic}/${diastolic}` : "未记录", detail: "mmHg", icon: HeartPulse },
    ...(glucose ? [{ label: "空腹血糖", value: `${glucose}`, detail: "mmol/L", icon: Activity }] : []),
  ];
  return <section className="mt-6"><div className="mb-3 flex items-center gap-2"><HeartPulse size={19} className="text-teal-700" /><h2 className="font-bold text-slate-900">本次健康指标</h2></div><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{metrics.map(({ label, value, detail, icon: Icon }) => <article key={label} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><Icon size={18} className="text-teal-700" /><p className="mt-4 text-xs font-medium text-slate-500">{label}</p><p className="mt-1 text-xl font-bold text-slate-950">{value}</p><p className="mt-1 text-xs text-slate-400">{detail}</p></article>)}</div></section>;
}

function ReportCard({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="mb-4 flex items-center gap-2 font-bold text-slate-900"><span className="text-teal-700">{icon}</span>{title}</h2>{children}</section>;
}
