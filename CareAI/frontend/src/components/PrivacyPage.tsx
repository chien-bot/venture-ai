import { Database, Download, EyeOff, LoaderCircle, Printer, Save, ShieldCheck, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { deleteAllHealthData, fetchFhirExport, fetchPortableSummary, fetchPrivacyPreferences, updatePrivacyPreferences } from "../api";
import type { PrivacyPreferences, UserProfile } from "../types";

export function PrivacyPage({ user, onDataDeleted }: { user: UserProfile; onDataDeleted: () => void }) {
  const [preferences, setPreferences] = useState<PrivacyPreferences | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { setPreferences(null); setStatus(null); void fetchPrivacyPreferences(user.id).then(setPreferences).catch(() => setStatus("无法读取隐私设置，请确认后端服务。")); }, [user.id]);

  async function save() {
    if (!preferences) return;
    setBusy(true); setStatus(null);
    try { setPreferences(await updatePrivacyPreferences(user.id, preferences)); setStatus("隐私设置已保存。"); }
    catch { setStatus("设置没有保存，请稍后重试。"); }
    finally { setBusy(false); }
  }

  async function download(kind: "summary" | "fhir") {
    setBusy(true); setStatus(null);
    try {
      const data = kind === "summary" ? await fetchPortableSummary(user.id) : await fetchFhirExport(user.id);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob); const link = document.createElement("a");
      link.href = url; link.download = `careai-${kind}-${new Date().toISOString().slice(0, 10)}.json`; link.click(); URL.revokeObjectURL(url);
      setStatus(kind === "summary" ? "便携健康摘要已下载。" : "FHIR演示数据已下载。该文件不是认证医疗交换记录。");
    } catch { setStatus("暂时无法导出，请检查是否已允许摘要导出。"); }
    finally { setBusy(false); }
  }

  async function printSummary() {
    const printWindow = window.open("", "careai-summary", "width=900,height=760");
    if (!printWindow) { setStatus("浏览器阻止了打印窗口，请允许弹出窗口后重试。"); return; }
    printWindow.document.write("<p style='font-family:sans-serif;padding:32px'>正在准备CareAI便携摘要…</p>");
    setBusy(true); setStatus(null);
    try {
      const data = await fetchPortableSummary(user.id);
      const observations = data.observations.map((item) => `<tr><td>${escapeHtml(item.display)}</td><td>${escapeHtml(String(item.value))} ${escapeHtml(item.unit ?? "")}</td><td>${escapeHtml(item.recorded_at)}</td><td>${escapeHtml(item.source)}</td></tr>`).join("");
      const insights = data.trend_insights.length ? data.trend_insights.map((item) => `<li><strong>${escapeHtml(item.title)}</strong>：${escapeHtml(item.explanation)} 下一步：${escapeHtml(item.next_step)}</li>`).join("") : "<li>当前记录不足，尚未生成趋势提示。</li>";
      printWindow.document.open();
      printWindow.document.write(`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>CareAI便携健康摘要</title><style>body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;color:#0f172a;line-height:1.6;max-width:820px;margin:0 auto;padding:36px}h1{font-size:28px;margin:0}h2{font-size:17px;margin-top:28px;border-bottom:1px solid #cbd5e1;padding-bottom:8px}p,li,td,th{font-size:13px}table{width:100%;border-collapse:collapse}td,th{border:1px solid #cbd5e1;padding:8px;text-align:left}.notice{margin-top:30px;padding:14px;background:#fef3c7}.meta{color:#64748b;font-size:12px}@media print{body{padding:0}.no-print{display:none}}</style></head><body><button class="no-print" onclick="window.print()">打印 / 保存PDF</button><h1>CareAI 便携健康摘要</h1><p class="meta">用户：${escapeHtml(data.user.display_name)} · 生成时间：${escapeHtml(data.provenance.generated_at)} · 规则：${escapeHtml(data.provenance.rule_version)}</p><h2>最近记录</h2><table><thead><tr><th>指标</th><th>数值</th><th>日期</th><th>来源</th></tr></thead><tbody>${observations || "<tr><td colspan='4'>暂无健康记录</td></tr>"}</tbody></table><h2>趋势与行动</h2><ul>${insights}</ul><p>${escapeHtml(data.weekly_review.summary)}</p><h2>来源与边界</h2><p>${escapeHtml(data.provenance.boundary)}</p><p class="notice">${escapeHtml(data.safety_notice)}</p></body></html>`);
      printWindow.document.close(); printWindow.focus();
      setTimeout(() => printWindow.print(), 250);
      setStatus("便携摘要已在打印窗口打开，可选择“保存为PDF”。");
    } catch { printWindow.close(); setStatus("暂时无法生成PDF摘要，请检查是否已允许摘要导出。"); }
    finally { setBusy(false); }
  }

  async function removeAll() {
    if (!window.confirm("确定删除这个档案下的全部健康报告、计划、复盘和理解检查吗？此操作无法撤销。")) return;
    setBusy(true); setStatus(null);
    try { const count = await deleteAllHealthData(user.id); onDataDeleted(); setStatus(`已删除 ${count} 条健康报告及相关计划。个人档案仍然保留。`); }
    catch { setStatus("删除没有完成，请稍后重试。"); }
    finally { setBusy(false); }
  }

  if (!preferences) return <main className="mx-auto max-w-5xl px-5 py-16"><div className="flex items-center gap-3 text-slate-600"><LoaderCircle className="animate-spin text-teal-600" />正在读取隐私设置…</div>{status && <p className="mt-4 text-rose-700">{status}</p>}</main>;

  return <main className="mx-auto max-w-5xl px-5 py-10">
    <div className="max-w-3xl"><h1 className="text-3xl font-bold text-slate-950">你的数据，由你决定</h1><p className="mt-3 leading-7 text-slate-600">查看CareAI会保存什么、AI会看到什么，并随时关闭处理、导出或删除记录。当前版本是本地课堂原型，不等同于生产级身份认证系统。</p></div>
    <section className="mt-8 grid gap-4 md:grid-cols-3">
      <FlowStep icon={<Database size={20} />} title="本地规则" body="原始指标先在后端由确定性规则处理。" />
      <FlowStep icon={<EyeOff size={20} />} title="最少AI数据" body="AI只接收规则已经确定的关注项，不接收姓名和完整档案。" />
      <FlowStep icon={<ShieldCheck size={20} />} title="用户控制" body="你可以关闭AI、停止保存、设置期限或删除全部记录。" />
    </section>
    <section className="mt-6 divide-y divide-slate-100 rounded-3xl border border-slate-200 bg-white px-6 shadow-sm sm:px-8">
      <ToggleRow title="允许受限AI解释" description="关闭后，CareAI仅用本地规则生成基础报告，不向外部模型发送关注项。" checked={preferences.ai_processing_enabled} onChange={(checked) => setPreferences({ ...preferences, ai_processing_enabled: checked })} />
      <ToggleRow title="保存报告与行动计划" description="关闭后，本次结果只显示在页面，不写入SQLite历史记录。" checked={preferences.save_reports} onChange={(checked) => setPreferences({ ...preferences, save_reports: checked })} />
      <ToggleRow title="允许导出便携摘要" description="允许本人下载CareAI摘要或FHIR结构演示文件。" checked={preferences.summary_export_enabled} onChange={(checked) => setPreferences({ ...preferences, summary_export_enabled: checked })} />
      <div className="flex flex-col gap-3 py-5 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-semibold text-slate-900">自动保留期限</h2><p className="mt-1 text-sm text-slate-500">超过期限的健康报告会在读取或更新设置时删除。</p></div><select value={preferences.retention_days} onChange={(event) => setPreferences({ ...preferences, retention_days: Number(event.target.value) })} className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-500/10"><option value={30}>30天</option><option value={90}>90天</option><option value={365}>1年</option><option value={0}>由我手动删除</option></select></div>
    </section>
    <div className="mt-5 flex flex-wrap items-center gap-3"><button disabled={busy} onClick={() => void save()} className="inline-flex items-center gap-2 rounded-xl bg-teal-600 px-5 py-3 font-semibold text-white hover:bg-teal-700 disabled:opacity-60"><Save size={17} />保存设置</button><button disabled={busy || !preferences.summary_export_enabled} onClick={() => void download("summary")} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40"><Download size={16} />下载摘要JSON</button><button disabled={busy || !preferences.summary_export_enabled} onClick={() => void printSummary()} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40"><Printer size={16} />打印/保存PDF</button><button disabled={busy || !preferences.summary_export_enabled} onClick={() => void download("fhir")} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40"><Download size={16} />FHIR演示导出</button></div>
    {status && <p role="status" className="mt-4 rounded-xl bg-teal-50 p-3 text-sm text-teal-900">{status}</p>}
    <section className="mt-9 border-t border-rose-100 pt-7"><h2 className="font-bold text-slate-900">删除健康数据</h2><p className="mt-2 text-sm leading-6 text-slate-600">删除全部报告、行动计划、每周复盘和理解检查；个人档案保留，方便重新开始。</p><button disabled={busy} onClick={() => void removeAll()} className="mt-4 inline-flex items-center gap-2 rounded-xl border border-rose-200 px-4 py-2.5 text-sm font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-60"><Trash2 size={16} />删除全部健康记录</button></section>
  </main>;
}

function FlowStep({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) { return <article className="rounded-2xl border border-teal-100 bg-teal-50/60 p-5"><span className="text-teal-700">{icon}</span><h2 className="mt-4 font-bold text-slate-900">{title}</h2><p className="mt-2 text-sm leading-6 text-slate-600">{body}</p></article>; }
function ToggleRow({ title, description, checked, onChange }: { title: string; description: string; checked: boolean; onChange: (checked: boolean) => void }) { return <label className="flex cursor-pointer items-center justify-between gap-5 py-5"><span><span className="block font-semibold text-slate-900">{title}</span><span className="mt-1 block text-sm leading-6 text-slate-500">{description}</span></span><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="size-5 shrink-0 accent-teal-600" /></label>; }
function escapeHtml(value: string) { return value.replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character] ?? character); }
