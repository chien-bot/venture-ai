import { BookOpenCheck, Bot, ChevronDown, Database, ExternalLink, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchReportEvidence } from "../api";
import type { ReportEvidenceBundle } from "../types";

export function EvidenceCards({ reportId, userId }: { reportId: number; userId: string }) {
  const [bundle, setBundle] = useState<ReportEvidenceBundle | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setBundle(null); setError(false);
    void fetchReportEvidence(reportId, userId).then(setBundle).catch(() => setError(true));
  }, [reportId, userId]);

  if (error) return <p className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">证据卡暂时无法读取，健康报告本身不受影响。</p>;
  if (!bundle) return <div className="mt-6 h-36 animate-pulse rounded-3xl bg-slate-100" aria-label="正在读取证据卡" />;

  return <section className="mt-6 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-7">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div><div className="flex items-center gap-2 text-teal-700"><BookOpenCheck size={20} /><h2 className="font-bold">建议证据卡</h2></div><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">查看每项判断使用了什么数据、由谁决定，以及哪些地方仍然不确定。</p></div>
      <div className="grid gap-1 text-right text-xs text-slate-500"><span>规则 {bundle.rule_version}</span><span>Agent {bundle.agent_version}</span></div>
    </div>
    <div className="mt-5 divide-y divide-slate-100 border-y border-slate-100">
      {bundle.cards.map((card) => <details key={card.id} className="group py-1">
        <summary className="flex cursor-pointer list-none items-center gap-3 rounded-xl px-2 py-3 outline-none transition hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-teal-500">
          <span className={`grid size-9 shrink-0 place-items-center rounded-xl ${card.decision_owner === "local_rule" ? "bg-teal-50 text-teal-700" : card.decision_owner === "constrained_ai" ? "bg-cyan-50 text-cyan-700" : "bg-amber-50 text-amber-700"}`}>{card.decision_owner === "local_rule" ? <Database size={18} /> : <Bot size={18} />}</span>
          <span className="min-w-0 flex-1"><span className="block font-semibold text-slate-900">{card.title}</span><span className="mt-0.5 block text-xs text-slate-500">{card.decision_owner === "local_rule" ? "本地规则决定" : card.decision_owner === "constrained_ai" ? "受限AI负责表达" : "历史来源未知"}</span></span>
          <ChevronDown size={18} className="text-slate-400 transition group-open:rotate-180" />
        </summary>
        <div className="mb-3 ml-12 grid gap-4 rounded-2xl bg-slate-50 p-4 text-sm leading-6 md:grid-cols-2">
          <div><p className="text-xs font-semibold text-slate-500">依据与说明</p><p className="mt-1 text-slate-800">{card.explanation}</p><p className="mt-3 text-xs text-slate-500">输入：{card.source_fields.length ? card.source_fields.join("、") : "规则关注项"}</p></div>
          <div><p className="flex items-center gap-1.5 text-xs font-semibold text-amber-700"><ShieldCheck size={14} />不确定性</p><p className="mt-1 text-slate-700">{card.uncertainty}</p>{card.references.map((reference) => reference.url ? <a key={reference.title} href={reference.url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-teal-700 underline underline-offset-4">{reference.title}<ExternalLink size={12} /></a> : <p key={reference.title} className="mt-2 text-xs font-semibold text-amber-700">{reference.title}</p>)}</div>
        </div>
      </details>)}
    </div>
    <p className="mt-4 text-xs leading-5 text-slate-500">{bundle.safety_notice} 当前模型：{bundle.model}</p>
  </section>;
}
