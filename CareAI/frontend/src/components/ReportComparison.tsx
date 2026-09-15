import { ArrowDownRight, ArrowRight, ArrowUpRight, ChartNoAxesCombined, History } from "lucide-react";
import type { HealthInput, ReportHistoryItem, StoredHealthInput } from "../types";

type ComparisonProps = {
  input: HealthInput | StoredHealthInput;
  bmi: number | null;
  riskLevel: ReportHistoryItem["report"]["risk_level"];
  previousReport: ReportHistoryItem | null;
};

const levelOrder = { normal: 0, attention: 1, high_attention: 2 } as const;

function getMetrics(input: HealthInput | StoredHealthInput, bmi: number | null) {
  const stored = "height_cm" in input;
  return {
    bmi,
    sleepHours: input.sleep_hours,
    exerciseDays: stored ? input.exercise_days_per_week : input.exercise_frequency,
  };
}

function ChangeIcon({ delta }: { delta: number }) {
  if (delta > 0) return <ArrowUpRight size={15} />;
  if (delta < 0) return <ArrowDownRight size={15} />;
  return <ArrowRight size={15} />;
}

export function ReportComparison({ input, bmi, riskLevel, previousReport }: ComparisonProps) {
  if (!previousReport) {
    return <section className="mt-6 rounded-3xl border border-dashed border-cyan-200 bg-cyan-50/60 p-6"><div className="flex gap-3"><span className="grid size-10 shrink-0 place-items-center rounded-xl bg-cyan-100 text-cyan-700"><History size={20} /></span><div><h2 className="font-bold text-slate-900">健康变化追踪将在下一次分析后开启</h2><p className="mt-2 text-sm leading-6 text-slate-600">本次报告已成为你的趋势基线。下一次录入相同指标后，CareAI 会并列展示 BMI、睡眠、运动和规则风险等级的变化。</p></div></div></section>;
  }

  const current = getMetrics(input, bmi);
  const previous = getMetrics(previousReport.input, previousReport.assessment.bmi);
  const riskDelta = levelOrder[riskLevel] - levelOrder[previousReport.report.risk_level];
  const riskText = riskDelta === 0 ? "与上次相同" : riskDelta > 0 ? "较上次提高" : "较上次降低";
  const metrics = [
    { label: "BMI", current: current.bmi, previous: previous.bmi, suffix: "", precision: 1 },
    { label: "睡眠", current: current.sleepHours, previous: previous.sleepHours, suffix: " h", precision: 1 },
    { label: "运动", current: current.exerciseDays, previous: previous.exerciseDays, suffix: " 天/周", precision: 0 },
  ];

  return <section className="mt-6 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm"><div className="flex flex-col gap-4 border-b border-slate-100 bg-gradient-to-r from-slate-950 to-slate-800 p-6 text-white sm:flex-row sm:items-center sm:justify-between"><div className="flex items-center gap-3"><span className="grid size-10 place-items-center rounded-xl bg-cyan-400/15 text-cyan-300"><ChartNoAxesCombined size={20} /></span><div><h2 className="font-bold">本次与上次报告对比</h2><p className="mt-1 text-sm text-slate-300">对比报告 #{previousReport.id} 的已保存健康数据</p></div></div><div className={`rounded-xl px-3 py-2 text-sm font-semibold ${riskDelta > 0 ? "bg-rose-400/15 text-rose-200" : riskDelta < 0 ? "bg-emerald-400/15 text-emerald-200" : "bg-white/10 text-slate-200"}`}>规则风险等级：{riskText}</div></div><div className="grid gap-3 p-5 sm:grid-cols-3">{metrics.map((metric) => {
    const delta = (metric.current ?? 0) - (metric.previous ?? 0);
    return <article key={metric.label} className="rounded-2xl border border-slate-100 bg-slate-50 p-4"><p className="text-xs font-semibold text-slate-500">{metric.label}</p><p className="mt-2 text-2xl font-bold text-slate-950">{metric.current?.toFixed(metric.precision) ?? "--"}{metric.suffix}</p><div className={`mt-2 flex items-center gap-1 text-xs font-medium ${delta > 0 ? "text-amber-700" : delta < 0 ? "text-teal-700" : "text-slate-500"}`}><ChangeIcon delta={delta} />上次 {metric.previous?.toFixed(metric.precision) ?? "--"}{metric.suffix} · {delta === 0 ? "无变化" : `${delta > 0 ? "+" : ""}${delta.toFixed(metric.precision)}${metric.suffix}`}</div></article>;
  })}</div><p className="px-5 pb-5 text-xs leading-5 text-slate-500">变化仅基于两次用户输入和规则等级的对照，用于健康习惯追踪，不构成医疗判断。</p></section>;
}
