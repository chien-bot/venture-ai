import { CheckCircle2, FlaskConical, LoaderCircle, RefreshCw, ShieldAlert, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchSafetySuite } from "../api";
import type { SafetySuiteResult } from "../types";

export function SafetyLabPage() {
  const [suite, setSuite] = useState<SafetySuiteResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function run() { setLoading(true); setError(null); try { setSuite(await fetchSafetySuite()); } catch { setError("无法运行安全测试，请确认后端服务。") } finally { setLoading(false); } }
  useEffect(() => { void run(); }, []);
  return <main className="mx-auto max-w-5xl px-5 py-10">
    <div className="flex flex-wrap items-start justify-between gap-5"><div className="max-w-3xl"><h1 className="text-3xl font-bold text-slate-950">健康AI安全实验室</h1><p className="mt-3 leading-7 text-slate-600">用固定回归案例检查生成层是否越权给出诊断、处方或药物剂量，同时确认低风险生活方式建议能够正常通过。</p></div><button disabled={loading} onClick={() => void run()} className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60">{loading ? <LoaderCircle className="animate-spin" size={16} /> : <RefreshCw size={16} />}重新运行</button></div>
    {error && <p className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-800">{error}</p>}
    {suite && <>
      <section className={`mt-8 flex flex-col gap-5 rounded-3xl p-6 text-white sm:flex-row sm:items-center sm:justify-between ${suite.passed ? "bg-emerald-700" : "bg-rose-700"}`}><div className="flex items-center gap-4"><span className="grid size-12 place-items-center rounded-2xl bg-white/15"><FlaskConical /></span><div><p className="text-sm text-white/75">{suite.suite_version}</p><h2 className="mt-1 text-xl font-bold">{suite.passed ? "全部安全回归通过" : "存在未通过的安全案例"}</h2></div></div><p className="text-3xl font-bold tabular-nums">{suite.pass_count}/{suite.total_count}</p></section>
      <section className="mt-6 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm"><div className="border-b border-slate-100 px-6 py-4"><h2 className="font-bold text-slate-900">测试案例</h2><p className="mt-1 text-sm text-slate-500">测试结果证明边界校验代码当前可运行，不等于临床安全认证。</p></div><div className="divide-y divide-slate-100">{suite.cases.map((item) => <article key={item.id} className="grid gap-3 px-6 py-4 sm:grid-cols-[auto_1fr_auto] sm:items-center"><span className={`grid size-9 place-items-center rounded-xl ${item.passed ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"}`}>{item.passed ? <CheckCircle2 size={18} /> : <XCircle size={18} />}</span><div><div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold text-slate-900">{item.id} · {item.title}</h3><span className="text-xs font-medium text-slate-500">预期：{item.expected}</span></div><p className="mt-1 text-sm text-slate-600">{item.detail}</p></div><span className={`text-sm font-bold ${item.passed ? "text-emerald-700" : "text-rose-700"}`}>{item.passed ? "通过" : "失败"}</span></article>)}</div></section>
      <section className="mt-6 flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950"><ShieldAlert className="mt-0.5 shrink-0" size={19} /><p>这套测试只覆盖当前列出的文本边界。真实部署仍需要专业内容复核、隐私审查、异常监控和人工监督。</p></section>
    </>}
  </main>;
}
