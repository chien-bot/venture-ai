"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getStage3Export, listProjects, saveStage3Document,
  saveStage3DailyProgress, saveStage3Evidence, saveStage3UseRecord,
} from "@/lib/api";
import { Project } from "@/lib/types";

type Kind = "proposal" | "plan" | "slides" | "script" | "qa" | "stage_summary";
type Doc = { kind: Kind; version: number; basis_version: number | null; plan_version: number | null; content: string; source: string; note: string; created_at: string };
type Run = { run_id: string; flow: string; agent_version: string; status: string; started_at: string; source_hash: string };
type Overview = {
  gate: { approved: boolean; proposal_version: number | null; review: { decision: string; feedback: string } | null };
  documents: Record<Kind, Doc | null>;
  scores: Record<string, { total: number }>;
  flow_coverage: string[];
  missing: string[];
  ready_for_acceptance: boolean;
  final_review: { decision: string; feedback: string } | null;
};
type Export = Overview & { document_history: Doc[]; runs: Run[]; evidence_items: { id: number; label: string; claim: string; source_ref: string }[]; use_records: { id: number; flow: string; run_id: string; action: string }[] };

const KINDS: { value: Kind; label: string }[] = [
  { value: "proposal", label: "01 立项书" }, { value: "plan", label: "02 商业计划书" },
  { value: "slides", label: "03 路演 PPT 内容" }, { value: "script", label: "04 十分钟讲稿" },
  { value: "qa", label: "05 五分钟问答库" }, { value: "stage_summary", label: "06 阶段总结" },
];
const FLOW_LABELS: Record<string, string> = { F1: "F1 理论学习", F2: "F2 项目指导", F3: "F3 评审反馈" };
const box = "rounded-xl border border-white/10 bg-white/[0.035] p-5";
const input = "w-full rounded-lg border border-white/15 bg-[#101827] px-3 py-2 text-sm text-slate-100 outline-none focus:border-indigo-400";
const primary = "rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-40";

export default function StageThreeStudentPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [data, setData] = useState<Export | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [kind, setKind] = useState<Kind>("proposal");
  const [content, setContent] = useState("");
  const [note, setNote] = useState("");
  const [timedSeconds, setTimedSeconds] = useState("");
  const [evidence, setEvidence] = useState({ label: "F", claim: "", source_ref: "", formula: "" });
  const [record, setRecord] = useState({ run_id: "", flow: "F2", task: "", material_kind: "proposal", material_version: "", action: "rewritten", reason: "", learning_check: "", issue_location: "", verification_run_id: "", result_kind: "", result_version: "", evidence_ref: "", effect_judgment: "" });
  const [progress, setProgress] = useState({ day: "1", goal: "", artifact: "", agent_evidence: "", risk_next: "" });

  const load = useCallback(async (id: string) => {
    if (!id) return;
    setError("");
    try { setData(await getStage3Export(id) as Export); }
    catch (err) { setError(err instanceof Error ? err.message : "读取失败"); }
  }, []);

  useEffect(() => {
    listProjects().then((res: { projects: Project[] }) => {
      setProjects(res.projects);
      const fromUrl = new URLSearchParams(window.location.search).get("project_id");
      const id = res.projects.find((p) => p.project_id === fromUrl)?.project_id || res.projects[0]?.project_id || "";
      setProjectId(id);
    }).catch((err: Error) => setError(err.message));
  }, []);
  useEffect(() => { if (projectId) void load(projectId); }, [projectId, load]);

  const act = async (fn: () => Promise<unknown>, success: string) => {
    setBusy(true); setError(""); setMessage("");
    try { await fn(); setMessage(success); await load(projectId); }
    catch (err) { setError(err instanceof Error ? err.message : "保存失败"); }
    finally { setBusy(false); }
  };

  const saveDoc = () => act(async () => {
    await saveStage3Document(projectId, {
      kind, content, source: "student", note,
      basis_version: kind === "proposal" ? null : data?.gate.proposal_version,
      plan_version: ["slides", "script", "qa"].includes(kind) ? data?.documents.plan?.version : null,
      timed_seconds: kind === "script" ? Number(timedSeconds) : null,
    });
    setContent(""); setNote(""); setTimedSeconds("");
  }, "已保存新版本；旧版本仍保留");

  const saveEvidence = () => act(async () => {
    await saveStage3Evidence(projectId, evidence);
    setEvidence({ label: "F", claim: "", source_ref: "", formula: "" });
  }, "证据台账已更新");

  const saveRecord = () => act(async () => {
    await saveStage3UseRecord(projectId, {
      ...record, material_version: Number(record.material_version),
      result_kind: record.result_kind || null,
      result_version: record.result_version ? Number(record.result_version) : null,
    });
    setRecord((current) => ({ ...current, run_id: "", task: "", reason: "", learning_check: "", issue_location: "", verification_run_id: "", evidence_ref: "", effect_judgment: "" }));
  }, "Agent 使用与人工修改记录已保存");

  const saveProgress = () => act(async () => {
    await saveStage3DailyProgress(projectId, { ...progress, day: Number(progress.day) });
    setProgress((current) => ({ ...current, goal: "", artifact: "", agent_evidence: "", risk_next: "" }));
  }, `D${progress.day} 进展已保存`);

  const download = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `${projectId}-stage3-evidence.json`; a.click();
    URL.revokeObjectURL(url);
  };

  const latest = data?.documents;
  const gate = data?.gate;
  const options = data?.document_history || [];
  return <div className="h-full overflow-y-auto bg-[#0b1120] p-6 text-slate-100">
    <div className="mx-auto max-w-5xl space-y-5 pb-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><p className="text-xs uppercase tracking-[0.2em] text-indigo-300">第三阶段 · D1—D9</p><h1 className="mt-1 text-2xl font-semibold">立项、成果与验收证据</h1><p className="mt-2 text-sm text-slate-400">每次修改保存新版本；Agent 草稿须经学生核验，教师独立判定通过。</p></div>
        <div className="flex gap-2"><select className={input} value={projectId} onChange={(e) => setProjectId(e.target.value)}><option value="">选择项目</option>{projects.map((p) => <option key={p.project_id} value={p.project_id}>{p.name}</option>)}</select><button className={primary} onClick={download} disabled={!data}>导出证据</button></div>
      </div>
      {error && <p role="alert" className="rounded-lg border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-200">{error}</p>}
      {message && <p role="status" className="rounded-lg border border-emerald-400/30 bg-emerald-400/10 p-3 text-sm text-emerald-200">{message}</p>}
      {!projectId && <div className={box}>先在「我的项目」创建项目。</div>}
      {projectId && <>
        <section className={box}>
          <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-lg font-semibold">立项闯关</h2><p className="text-sm text-slate-400">当前立项书 v{gate?.proposal_version ?? "—"} · {gate?.approved ? "教师已通过 G1–G6" : "待教师复审"}</p></div><span className={`rounded-full px-3 py-1 text-xs ${gate?.approved ? "bg-emerald-400/15 text-emerald-200" : "bg-amber-400/15 text-amber-200"}`}>{gate?.approved ? "已通过" : "未通过"}</span></div>
          {gate?.review?.feedback && <p className="mt-3 rounded-lg bg-white/5 p-3 text-sm">教师反馈：{gate.review.feedback}</p>}
          <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{KINDS.map((k) => <div key={k.value} className="rounded-lg border border-white/10 p-3 text-sm"><span className="text-slate-400">{k.label}</span><p className="mt-1">{latest?.[k.value] ? `v${latest[k.value]?.version} · ${latest[k.value]?.source === "student" ? "学生核验版" : "Agent 草稿"}` : "尚未保存"}</p></div>)}</div>
          {!!data?.missing.length && <div className="mt-4"><p className="text-sm font-medium text-amber-200">距离终局验收还缺：</p><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-400">{data.missing.map((m) => <li key={m}>{m}</li>)}</ul></div>}
        </section>

        <section className={box}><h2 className="text-lg font-semibold">保存材料版本</h2><p className="mt-1 text-sm text-slate-400">立项通过后才能保存正式材料。PPT、讲稿和问答库会绑定当前学生计划书版本。</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-[220px_1fr]"><select className={input} value={kind} onChange={(e) => { setKind(e.target.value as Kind); setContent(""); }} >{KINDS.map((k) => <option key={k.value} value={k.value}>{k.label}</option>)}</select><input className={input} value={note} onChange={(e) => setNote(e.target.value)} placeholder="本版修改说明：上一版—反馈—修改—验证" /></div>
          <textarea className={`${input} mt-3 min-h-52`} value={content} onChange={(e) => setContent(e.target.value)} placeholder="粘贴你核验和修改后的材料。关键数字请标 F/I/H/S，并在证据台账中记录来源或公式。" />
          {kind === "script" && <input className={`${input} mt-3 max-w-sm`} type="number" min={1} max={600} value={timedSeconds} onChange={(e) => setTimedSeconds(e.target.value)} placeholder="实际计时秒数（必须 ≤ 600）" />}
          <div className="mt-3 flex flex-wrap items-center gap-3"><button className={primary} disabled={busy || content.trim().length < 20} onClick={saveDoc}>保存为新版本</button>{latest?.[kind] && <button className="text-sm text-indigo-300 underline" onClick={() => { setContent(latest[kind]?.content || ""); setNote(`基于 v${latest[kind]?.version} 修改：`); }}>载入当前版修改</button>}</div>
          <div className="mt-4 max-h-44 overflow-y-auto text-xs text-slate-400">{options.filter((d) => d.kind === kind).map((d) => <div key={`${d.kind}-${d.version}`} className="flex justify-between border-t border-white/10 py-2"><span>v{d.version} · {d.source} · {d.note || "无修改说明"}</span><button className="text-indigo-300" onClick={() => { setContent(d.content); setNote(`基于 v${d.version} 修改：`); }}>查看/继续修改</button></div>)}</div>
        </section>

        <section className={box}><h2 className="text-lg font-semibold">F/I/H/S 证据台账</h2><p className="mt-1 text-sm text-slate-400">事实须有可定位来源；模拟资料只能标 S。数字请补来源或公式。</p><div className="mt-4 grid gap-3 sm:grid-cols-[100px_1fr]"><select className={input} value={evidence.label} onChange={(e) => setEvidence({ ...evidence, label: e.target.value })}>{["F", "I", "H", "S"].map((x) => <option key={x}>{x}</option>)}</select><input className={input} value={evidence.claim} onChange={(e) => setEvidence({ ...evidence, claim: e.target.value })} placeholder="主张或关键数字" /></div><div className="mt-3 grid gap-3 sm:grid-cols-2"><input className={input} value={evidence.source_ref} onChange={(e) => setEvidence({ ...evidence, source_ref: e.target.value })} placeholder="来源位置／模拟说明" /><input className={input} value={evidence.formula} onChange={(e) => setEvidence({ ...evidence, formula: e.target.value })} placeholder="计算公式或推断依据" /></div><button className={`${primary} mt-3`} disabled={busy || evidence.claim.trim().length < 4} onClick={saveEvidence}>添加证据</button><div className="mt-3 space-y-2">{data?.evidence_items.map((e) => <p key={e.id} className="text-sm text-slate-400"><span className="mr-2 text-indigo-300">E{e.id} [{e.label}]</span>{e.claim} <span className="text-slate-500">{e.source_ref}</span></p>)}</div></section>

        <section className={box}><h2 className="text-lg font-semibold">Agent 使用与人工处理</h2><p className="mt-1 text-sm text-slate-400">只接受本项目已完成的真实 run_id。F1 需理解检查；F3 需修改后再评分。</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2"><select className={input} value={record.flow} onChange={(e) => setRecord({ ...record, flow: e.target.value })}>{Object.entries(FLOW_LABELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select><select className={input} value={record.run_id} onChange={(e) => setRecord({ ...record, run_id: e.target.value })}><option value="">选择真实运行</option>{data?.runs.filter((r) => r.status === "completed").map((r) => <option key={r.run_id} value={r.run_id}>{r.run_id} · {r.flow}</option>)}</select><input className={input} value={record.task} onChange={(e) => setRecord({ ...record, task: e.target.value })} placeholder="该次运行的任务目标" /><select className={input} value={record.action} onChange={(e) => setRecord({ ...record, action: e.target.value })}>{[["adopted", "采纳"], ["rejected", "拒绝"], ["rewritten", "重写"], ["supplemented", "补充"]].map(([v, l]) => <option value={v} key={v}>{l}</option>)}</select><select className={input} value={`${record.material_kind}:${record.material_version}`} onChange={(e) => { const [material_kind, material_version] = e.target.value.split(":"); setRecord({ ...record, material_kind, material_version }); }}><option value="proposal:">选择输入材料版本</option>{options.map((d) => <option key={`in-${d.kind}-${d.version}`} value={`${d.kind}:${d.version}`}>{d.kind} v{d.version}</option>)}</select><select className={input} value={`${record.result_kind}:${record.result_version}`} onChange={(e) => { const [result_kind, result_version] = e.target.value.split(":"); setRecord({ ...record, result_kind, result_version }); }}><option value=":">选择修改后成果版本</option>{options.map((d) => <option key={`out-${d.kind}-${d.version}`} value={`${d.kind}:${d.version}`}>{d.kind} v{d.version}</option>)}</select></div>
          <textarea className={`${input} mt-3 min-h-20`} value={record.reason} onChange={(e) => setRecord({ ...record, reason: e.target.value })} placeholder="采纳／拒绝／改写了什么，为什么？请明确人工责任。" />
          {record.flow === "F1" && <textarea className={`${input} mt-3 min-h-20`} value={record.learning_check} onChange={(e) => setRecord({ ...record, learning_check: e.target.value })} placeholder="理解检查的题目、学生回答、错误及纠正" />}
          {record.flow === "F3" && <div className="mt-3 grid gap-3 sm:grid-cols-2"><input className={input} value={record.issue_location} onChange={(e) => setRecord({ ...record, issue_location: e.target.value })} placeholder="被评审材料的问题位置" /><select className={input} value={record.verification_run_id} onChange={(e) => setRecord({ ...record, verification_run_id: e.target.value })}><option value="">选择修改后的复验 run_id</option>{data?.runs.filter((r) => r.status === "completed" && r.flow === "grader" && r.run_id !== record.run_id).map((r) => <option key={r.run_id}>{r.run_id}</option>)}</select></div>}
          <div className="mt-3 grid gap-3 sm:grid-cols-2"><input className={input} value={record.evidence_ref} onChange={(e) => setRecord({ ...record, evidence_ref: e.target.value })} placeholder="原始输出、失败或人工修改记录的位置（必填）" /><input className={input} value={record.effect_judgment} onChange={(e) => setRecord({ ...record, effect_judgment: e.target.value })} placeholder="效果判断：节省时间、提升质量或引入风险" /></div><button className={`${primary} mt-3`} disabled={busy || !record.run_id || !record.material_version || record.task.trim().length < 8 || record.reason.trim().length < 8 || record.evidence_ref.trim().length < 4 || record.effect_judgment.trim().length < 8} onClick={saveRecord}>保存使用记录</button>
          <p className="mt-3 text-sm text-slate-400">已记录：{data?.use_records.map((r) => `${r.flow} ${r.run_id} (${r.action})`).join("；") || "暂无"}</p>
        </section>

        <section className={box}><h2 className="text-lg font-semibold">D1—D9 每日进展</h2><p className="mt-1 text-sm text-slate-400">记录当日目标、产物版本、Agent 证据和次日动作；同一天再次保存会保留最新状态。</p><div className="mt-4 grid gap-3 sm:grid-cols-2"><select className={input} value={progress.day} onChange={(e) => setProgress({ ...progress, day: e.target.value })}>{Array.from({ length: 9 }, (_, i) => <option key={i + 1} value={i + 1}>D{i + 1}</option>)}</select><input className={input} value={progress.goal} onChange={(e) => setProgress({ ...progress, goal: e.target.value })} placeholder="当天目标" /><input className={input} value={progress.artifact} onChange={(e) => setProgress({ ...progress, artifact: e.target.value })} placeholder="产物及版本" /><input className={input} value={progress.agent_evidence} onChange={(e) => setProgress({ ...progress, agent_evidence: e.target.value })} placeholder="Agent run_id／证据位置" /><input className={input} value={progress.risk_next} onChange={(e) => setProgress({ ...progress, risk_next: e.target.value })} placeholder="风险与次日动作" /></div><button className={`${primary} mt-3`} disabled={busy || [progress.goal, progress.artifact, progress.agent_evidence, progress.risk_next].some((x) => x.trim().length < 4)} onClick={saveProgress}>保存当日进展</button></section>
      </>}
    </div>
  </div>;
}
