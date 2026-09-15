import { AlertCircle, ArrowRight, LoaderCircle } from "lucide-react";
import { useState } from "react";
import { previewReportImport } from "../api";
import type { HealthInput } from "../types";

const initialForm: HealthInput = {
  age: 22,
  gender: "male",
  height: 175,
  weight: 70,
  blood_pressure: "",
  sleep_hours: 7,
  exercise_frequency: 2,
};

const demoScenarios: { title: string; description: string; tone: string; input: HealthInput }[] = [
  {
    title: "规律生活案例",
    description: "展示一般关注等级与健康习惯建议",
    tone: "border-emerald-200 bg-emerald-50 text-emerald-900",
    input: { age: 22, gender: "female", height: 165, weight: 55, blood_pressure: "112/72", blood_glucose: 5.2, sleep_hours: 8, exercise_frequency: 4 },
  },
  {
    title: "作息待改善案例",
    description: "展示睡眠与运动频率的关注提示",
    tone: "border-amber-200 bg-amber-50 text-amber-900",
    input: { age: 22, gender: "male", height: 175, weight: 70, blood_pressure: "122/82", sleep_hours: 6.5, exercise_frequency: 1 },
  },
  {
    title: "重点关注案例",
    description: "展示 BMI、血压和睡眠的综合提示",
    tone: "border-rose-200 bg-rose-50 text-rose-900",
    input: { age: 22, gender: "male", height: 175, weight: 80, blood_pressure: "145/90", blood_glucose: 6.5, sleep_hours: 5, exercise_frequency: 1 },
  },
];

const sampleReportText = "报告日期：2026-08-20\n年龄：30\n性别：女\n身高：165 cm\n体重：62 kg\n血压：128/82\n空腹血糖：5.8 mmol/L";

type FormProps = {
  onSubmit: (input: HealthInput) => Promise<void>;
  isLoading: boolean;
  error: string | null;
  userId: string;
  defaultGoal?: string | null;
};

export function HealthForm({ onSubmit, isLoading, error, userId, defaultGoal }: FormProps) {
  const [form, setForm] = useState<HealthInput>(initialForm);
  const [reportText, setReportText] = useState("");
  const [reportFilename, setReportFilename] = useState<string | undefined>();
  const [importNotices, setImportNotices] = useState<string[]>([]);
  const [isImporting, setIsImporting] = useState(false);
  const setValue = <K extends keyof HealthInput>(key: K, value: HealthInput[K]) => setForm((current) => ({ ...current, [key]: value }));

  async function readTextReport(file: File | undefined) {
    if (!file) return;
    setReportFilename(file.name);
    setImportNotices([]);
    setReportText(await file.text());
  }

  async function extractReportText() {
    if (!reportText.trim()) { setImportNotices(["请先粘贴健康报告文字、选择 TXT 文件，或载入课堂样例。"]); return; }
    setIsImporting(true);
    try {
      const preview = await previewReportImport(reportText, reportFilename);
      setForm((current) => ({
        ...current,
        age: preview.age ?? current.age,
        gender: preview.gender ?? current.gender,
        height: preview.height_cm ?? current.height,
        weight: preview.weight_kg ?? current.weight,
        blood_pressure: preview.systolic_bp !== null && preview.diastolic_bp !== null ? `${preview.systolic_bp}/${preview.diastolic_bp}` : current.blood_pressure,
        blood_glucose: preview.fasting_blood_glucose_mmol_l ?? current.blood_glucose,
        sleep_hours: preview.sleep_hours ?? current.sleep_hours,
        exercise_frequency: preview.exercise_days_per_week ?? current.exercise_frequency,
        recorded_at: preview.recorded_at ?? current.recorded_at,
        source: "report_import",
      }));
      setImportNotices([`已提取：${preview.extracted_fields.length ? preview.extracted_fields.join("、") : "没有可用指标"}。请在下方逐项核对后再提交。`, ...preview.notices]);
    } catch {
      setImportNotices(["无法提取报告文字，请确认后端服务已启动后重试。"]);
    } finally { setIsImporting(false); }
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data: HealthInput = {
      ...form,
      blood_pressure: form.blood_pressure?.trim() || undefined,
      blood_glucose: form.blood_glucose || undefined,
      user_id: userId,
      recorded_at: form.recorded_at || new Date().toISOString().slice(0, 10),
      source: "manual",
      health_goal: form.health_goal || defaultGoal || undefined,
    };
    await onSubmit(data);
  }

  async function retryAnalysis() {
    await onSubmit({ ...form, blood_pressure: form.blood_pressure?.trim() || undefined, blood_glucose: form.blood_glucose || undefined, user_id: userId, recorded_at: form.recorded_at || new Date().toISOString().slice(0, 10), source: "manual", health_goal: form.health_goal || defaultGoal || undefined });
  }

  const inputClass = "mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:ring-4 focus:ring-teal-500/10";
  return (
    <main className="mx-auto max-w-3xl px-5 py-10">
      <div className="mb-8"><p className="text-sm font-semibold text-teal-700">健康 Memory · 新增记录</p><h1 className="mt-2 text-3xl font-bold text-slate-950">记录一次健康状态</h1><p className="mt-3 text-slate-600">这次记录会进入你的健康时间轴，用于后续趋势分析。带“可选”的指标未填写时不会参与风险判断。</p></div>
      <section className="mb-6 rounded-2xl border border-cyan-100 bg-cyan-50/60 p-4"><div className="flex flex-wrap items-baseline justify-between gap-2"><h2 className="font-bold text-slate-900">快速演示案例</h2><span className="text-xs text-slate-500">仅用于产品演示，可随时修改数据</span></div><div className="mt-3 grid gap-3 sm:grid-cols-3">{demoScenarios.map((scenario) => <button type="button" key={scenario.title} onClick={() => setForm(scenario.input)} className={`rounded-xl border p-3 text-left transition hover:-translate-y-0.5 hover:shadow-sm ${scenario.tone}`}><p className="text-sm font-bold">{scenario.title}</p><p className="mt-1 text-xs leading-5 opacity-75">{scenario.description}</p><span className="mt-3 inline-block text-xs font-semibold">载入此数据 →</span></button>)}</div></section>
      <section className="mb-6 rounded-2xl border border-violet-100 bg-violet-50/60 p-4"><div className="flex flex-wrap items-baseline justify-between gap-2"><div><h2 className="font-bold text-slate-900">从健康报告建立记录</h2><p className="mt-1 text-xs leading-5 text-slate-600">粘贴电子报告文字或选择 TXT 后，系统提取草稿；必须由你在下方确认、编辑后才会保存。</p></div><button type="button" onClick={() => { setReportText(sampleReportText); setReportFilename("课堂样例健康报告.txt"); setImportNotices([]); }} className="text-xs font-semibold text-violet-700 underline underline-offset-4">载入课堂样例</button></div><div className="mt-3 grid gap-3 sm:grid-cols-[1fr_auto]"><textarea value={reportText} onChange={(event) => { setReportText(event.target.value); setImportNotices([]); }} rows={4} placeholder="例如：报告日期：2026-08-20；身高：165 cm；体重：62 kg；血压：128/82" className={inputClass} /><div className="flex flex-col gap-2"><label className="cursor-pointer rounded-xl border border-violet-200 bg-white px-3 py-2 text-center text-xs font-semibold text-violet-700 hover:bg-violet-50">选择 TXT<input type="file" accept=".txt,text/plain" className="hidden" onChange={(event) => void readTextReport(event.target.files?.[0])} /></label><button type="button" disabled={isImporting} onClick={() => void extractReportText()} className="rounded-xl bg-violet-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">{isImporting ? "正在提取" : "提取并核对"}</button></div></div>{reportFilename && <p className="mt-2 text-xs text-violet-700">当前文字来源：{reportFilename}</p>}{importNotices.length > 0 && <ul className="mt-3 space-y-1 rounded-xl bg-white/70 p-3 text-xs leading-5 text-slate-600">{importNotices.map((notice) => <li key={notice}>• {notice}</li>)}</ul>}</section>
      <form onSubmit={submit} className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <section><h2 className="text-lg font-bold text-slate-900">基本信息</h2><div className="mt-4 grid gap-5 sm:grid-cols-2">
          <label className="text-sm font-medium text-slate-700">年龄<input required min="18" max="120" type="number" value={form.age} onChange={(e) => setValue("age", Number(e.target.value))} className={inputClass} /></label>
          <label className="text-sm font-medium text-slate-700">性别<select value={form.gender} onChange={(e) => setValue("gender", e.target.value as HealthInput["gender"])} className={inputClass}><option value="male">男</option><option value="female">女</option><option value="other">其他</option></select></label>
        </div></section>
        <div className="my-7 border-t border-slate-100" />
        <section><h2 className="text-lg font-bold text-slate-900">本次记录</h2><div className="mt-4 grid gap-5 sm:grid-cols-2">
          <label className="text-sm font-medium text-slate-700">记录日期<input required type="date" value={form.recorded_at ?? new Date().toISOString().slice(0, 10)} onChange={(e) => setValue("recorded_at", e.target.value)} className={inputClass} /></label>
          <label className="text-sm font-medium text-slate-700">本周主要目标<select value={form.health_goal ?? defaultGoal ?? ""} onChange={(e) => setValue("health_goal", e.target.value || undefined)} className={inputClass}><option value="">请选择（可选）</option><option value="改善睡眠">改善睡眠</option><option value="建立运动习惯">建立运动习惯</option><option value="体重管理">体重管理</option><option value="规律记录血压">规律记录血压</option></select></label>
        </div></section>
        <div className="my-7 border-t border-slate-100" />
        <section><h2 className="text-lg font-bold text-slate-900">健康指标</h2><div className="mt-4 grid gap-5 sm:grid-cols-2">
          <label className="text-sm font-medium text-slate-700">身高（cm）<input required min="100" max="250" type="number" value={form.height} onChange={(e) => setValue("height", Number(e.target.value))} className={inputClass} /></label>
          <label className="text-sm font-medium text-slate-700">体重（kg）<input required min="20" max="350" type="number" value={form.weight} onChange={(e) => setValue("weight", Number(e.target.value))} className={inputClass} /></label>
          <label className="text-sm font-medium text-slate-700">血压（可选）<input pattern="\d{2,3}/\d{2,3}" title="请按 120/80 格式填写" value={form.blood_pressure ?? ""} onChange={(e) => setValue("blood_pressure", e.target.value)} placeholder="例如：120/80" className={inputClass} /></label>
          <label className="text-sm font-medium text-slate-700">空腹血糖 mmol/L（可选）<input min="1" max="40" step="0.1" type="number" value={form.blood_glucose ?? ""} onChange={(e) => setValue("blood_glucose", e.target.value === "" ? undefined : Number(e.target.value))} placeholder="例如：5.2" className={inputClass} /></label>
          <label className="text-sm font-medium text-slate-700">平均睡眠时长（小时/晚）<input required min="0" max="24" step="0.5" type="number" value={form.sleep_hours} onChange={(e) => setValue("sleep_hours", Number(e.target.value))} className={inputClass} /></label>
          <label className="text-sm font-medium text-slate-700">每周运动天数<select value={form.exercise_frequency} onChange={(e) => setValue("exercise_frequency", Number(e.target.value))} className={inputClass}>{Array.from({ length: 8 }, (_, value) => <option key={value} value={value}>{value} 天</option>)}</select></label>
        </div></section>
        {error && <div className="mt-6 flex gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700"><AlertCircle className="shrink-0" size={19} /><div><p>分析未完成：{error}</p><button type="button" disabled={isLoading} onClick={() => void retryAnalysis()} className="mt-2 font-semibold underline underline-offset-4 hover:text-rose-900 disabled:opacity-60">使用当前数据重新尝试</button></div></div>}
        <div className="mt-7 flex flex-col gap-3 border-t border-slate-100 pt-6 sm:flex-row sm:items-center sm:justify-between"><p className="max-w-md text-xs leading-5 text-slate-500">提交后将由规则引擎与 AI 生成健康风险提示。成功报告会保存至 CareAI 的 SQLite 历史记录；本服务不诊断疾病，也不替代医生。</p><button disabled={isLoading} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-teal-600 px-5 py-3 font-semibold text-white shadow-lg shadow-teal-600/20 transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-60">{isLoading ? <><LoaderCircle size={18} className="animate-spin" />正在分析</> : <>生成健康报告 <ArrowRight size={18} /></>}</button></div>
      </form>
    </main>
  );
}
