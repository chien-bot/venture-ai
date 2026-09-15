"use client";

import { useCallback, useEffect, useState } from "react";
import { getStage3Overview, getStage3Ranking, listProjects, saveStage3FinalReview, saveStage3GateReview, saveStage3Score } from "@/lib/api";
import { Project } from "@/lib/types";

type Category = "project" | "agent" | "defense";
type Overview = {
  gate: { approved: boolean; proposal_version: number | null; review: { criteria: Record<string, boolean>; decision: string; feedback: string } | null };
  documents: Record<string, { version: number; source: string; content: string } | null>;
  scores: Record<string, { total: number; scores: Record<string, number>; feedback: string }>;
  flow_coverage: string[]; missing: string[]; ready_for_acceptance: boolean;
  final_review: { decision: string; feedback: string; current: boolean } | null;
};
type Ranking = { eligible_count: number; provisional_slots: number; finalists_scored: number; rows: { project_id: string; name: string; project_score: number; agent_score: number; ranking_score: number; rank: number; provisional_shortlist: boolean; defense_score: number | null; final_total: number | null; final_rank: number | null }[] };
const GATES: [string, string][] = [
  ["G1", "问题具体：用户、场景和问题可识别"], ["G2", "证据成立：来源可查，结论不过度"],
  ["G3", "边界透明：F/I/H/S 标注完整"], ["G4", "方案匹配：回应问题并说明边界"],
  ["G5", "价值可行：社会价值、创新和实施路径"], ["G6", "Agent 可追溯：V2 参与且运行可定位"],
];
const SCALES: Record<Category, [string, string, number][]> = {
  project: [["social_value", "社会价值", 20], ["evidence_process", "实践／证据过程", 20], ["innovation", "创新意义", 20], ["feasibility", "发展前景与可行性", 25], ["team_consistency", "团队协作与材料一致性", 15]],
  agent: [["three_flows", "三个流程综合覆盖", 20], ["traceability", "记录与版本可追溯", 20], ["effectiveness", "有效性与改进证据", 25], ["correctness", "正确性与证据安全", 20], ["human_boundary", "人机边界与反思", 15]],
  defense: [["narrative_time", "叙事与时间控制", 20], ["logic_consistency", "项目逻辑与材料一致", 20], ["answers", "问答与真实理解", 25], ["evidence_boundary", "证据边界与不确定性", 20], ["team_delivery", "团队协作与现场表现", 15]],
};
const box = "rounded-xl border border-white/10 bg-white/[0.035] p-5";
const input = "w-full rounded-lg border border-white/15 bg-[#101827] px-3 py-2 text-sm text-slate-100 outline-none focus:border-emerald-400";
const button = "rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-40";

export default function StageThreeTeacherPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [data, setData] = useState<Overview | null>(null);
  const [ranking, setRanking] = useState<Ranking | null>(null);
  const [criteria, setCriteria] = useState<Record<string, boolean>>(Object.fromEntries(GATES.map(([key]) => [key, false])));
  const [gateFeedback, setGateFeedback] = useState("");
  const [category, setCategory] = useState<Category>("project");
  const [scores, setScores] = useState<Record<string, number>>({});
  const [scoreFeedback, setScoreFeedback] = useState("");
  const [finalDecision, setFinalDecision] = useState("fail");
  const [redline, setRedline] = useState(false);
  const [finalFeedback, setFinalFeedback] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async (id: string) => {
    if (!id) return;
    try {
      const overview = await getStage3Overview(id) as Overview;
      setData(overview);
      if (overview.gate.review) {
        setCriteria(overview.gate.review.criteria);
        setGateFeedback(overview.gate.review.feedback || "");
      } else {
        setCriteria(Object.fromEntries(GATES.map(([key]) => [key, false])));
        setGateFeedback("");
      }
      setRanking(await getStage3Ranking() as Ranking);
    }
    catch (err) { setError(err instanceof Error ? err.message : "读取失败"); }
  }, []);
  useEffect(() => {
    listProjects().then((res: { projects: Project[] }) => {
      setProjects(res.projects);
      const fromUrl = new URLSearchParams(window.location.search).get("project_id");
      setProjectId(res.projects.find((p) => p.project_id === fromUrl)?.project_id || res.projects[0]?.project_id || "");
    }).catch((err: Error) => setError(err.message));
  }, []);
  useEffect(() => { if (projectId) void load(projectId); }, [projectId, load]);
  useEffect(() => {
    setScores(data?.scores[category]?.scores || {});
    setScoreFeedback(data?.scores[category]?.feedback || "");
  }, [category, data]);

  const act = async (fn: () => Promise<unknown>, success: string) => {
    setBusy(true); setError(""); setMessage("");
    try { await fn(); setMessage(success); await load(projectId); }
    catch (err) { setError(err instanceof Error ? err.message : "提交失败"); }
    finally { setBusy(false); }
  };
  const submitGate = (decision: "approved" | "revise") => act(
    () => saveStage3GateReview(projectId, { proposal_version: data?.gate.proposal_version, criteria, decision, feedback: gateFeedback }),
    decision === "approved" ? "立项通过已记录" : "退回与反馈已记录",
  );
  const submitScore = () => act(
    () => saveStage3Score(projectId, { category, scores, feedback: scoreFeedback }),
    "独立100分评审已保存，历史评分仍保留",
  );
  const submitFinal = () => act(
    () => saveStage3FinalReview(projectId, { decision: finalDecision, redline, feedback: finalFeedback }),
    "教师终局结论已保存",
  );

  const currentScale = SCALES[category];
  const total = currentScale.reduce((sum, [key]) => sum + (scores[key] ?? 0), 0);
  return <div className="h-full overflow-y-auto bg-[#0b1120] p-6 text-slate-100"><div className="mx-auto max-w-5xl space-y-5 pb-12">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs uppercase tracking-[0.2em] text-emerald-300">教师 · 第三阶段</p><h1 className="mt-1 text-2xl font-semibold">立项复审与终局验收</h1><p className="mt-2 text-sm text-slate-400">Agent 分数只作参考；下列门槛与评分由教师独立确认。</p></div><select className={input} value={projectId} onChange={(e) => setProjectId(e.target.value)}><option value="">选择项目</option>{projects.map((p) => <option key={p.project_id} value={p.project_id}>{p.name}</option>)}</select></div>
    {error && <p role="alert" className="rounded-lg border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-200">{error}</p>}
    {message && <p role="status" className="rounded-lg border border-emerald-400/30 bg-emerald-400/10 p-3 text-sm text-emerald-200">{message}</p>}
    {projectId && <>
      <section className={box}><h2 className="text-lg font-semibold">G1–G6 立项闯关</h2><p className="mt-1 text-sm text-slate-400">当前立项书 v{data?.gate.proposal_version ?? "—"} · {data?.gate.approved ? "已通过" : "未通过"}。学生更新立项书后，旧版通过结论自动失效。</p>
        {data?.documents.proposal && <details className="mt-3 rounded-lg border border-white/10 p-3"><summary className="cursor-pointer text-sm text-emerald-200">查看学生立项书 v{data.documents.proposal.version}</summary><pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap text-sm text-slate-300">{data.documents.proposal.content}</pre></details>}
        <div className="mt-4 grid gap-2 sm:grid-cols-2">{GATES.map(([key, label]) => <label key={key} className="flex items-start gap-2 rounded-lg border border-white/10 p-3 text-sm"><input type="checkbox" checked={!!criteria[key]} onChange={(e) => setCriteria({ ...criteria, [key]: e.target.checked })} className="mt-1" /><span><strong className="text-emerald-300">{key}</strong> {label}</span></label>)}</div>
        <textarea className={`${input} mt-3 min-h-20`} value={gateFeedback} onChange={(e) => setGateFeedback(e.target.value)} placeholder="具体反馈：上一版问题、需修改的内容及复审依据" /><div className="mt-3 flex gap-2"><button className={button} disabled={busy || !data?.gate.proposal_version || !GATES.every(([key]) => criteria[key]) || gateFeedback.trim().length < 8} onClick={() => submitGate("approved")}>全部达到，立项通过</button><button className="rounded-lg border border-amber-400/40 px-4 py-2 text-sm text-amber-200 disabled:opacity-40" disabled={busy || !data?.gate.proposal_version || gateFeedback.trim().length < 8} onClick={() => submitGate("revise")}>修改后再审</button></div>
      </section>

      <section className={box}><h2 className="text-lg font-semibold">两张独立100分表与答辩表</h2><div className="mt-3 flex gap-2">{(["project", "agent", "defense"] as Category[]).map((cat) => <button key={cat} onClick={() => setCategory(cat)} className={`rounded-lg px-3 py-2 text-sm ${category === cat ? "bg-emerald-500/20 text-emerald-200" : "bg-white/5 text-slate-400"}`}>{cat === "project" ? "项目成果" : cat === "agent" ? "Agent效果" : "现场答辩"}</button>)}</div>
        <div className="mt-4 space-y-3">{currentScale.map(([key, label, max]) => <label key={key} className="grid items-center gap-2 sm:grid-cols-[1fr_130px]"><span className="text-sm">{label} <span className="text-slate-500">/{max}</span></span><input className={input} type="number" min={0} max={max} value={scores[key] ?? ""} onChange={(e) => setScores({ ...scores, [key]: Number(e.target.value) })} /></label>)}</div>
        <p className="mt-4 text-sm">本表合计：<strong>{total}/100</strong> · {total >= 60 ? "达到60分" : "未达60分"}</p><textarea className={`${input} mt-3 min-h-20`} value={scoreFeedback} onChange={(e) => setScoreFeedback(e.target.value)} placeholder="评分依据、证据位置和首要改进建议" /><button className={`${button} mt-3`} disabled={busy || !data?.gate.approved || currentScale.some(([key]) => scores[key] === undefined) || scoreFeedback.trim().length < 8} onClick={submitScore}>保存本表评分</button>
        <div className="mt-4 grid gap-2 sm:grid-cols-3">{(["project", "agent", "defense"] as Category[]).map((cat) => <p key={cat} className="rounded-lg bg-white/5 p-3 text-sm">{cat}：{data?.scores[cat]?.total ?? "未评分"}/100</p>)}</div>
      </section>

      <section className={box}><h2 className="text-lg font-semibold">终局结论</h2><p className="mt-1 text-sm text-slate-400">立项通过、项目与 Agent 各≥60、材料完整、三流程可追溯且无红线，才可判定通过。</p>{!!data?.missing.length && <ul className="mt-3 list-disc pl-5 text-sm text-amber-200">{data.missing.map((m) => <li key={m}>{m}</li>)}</ul>}
        <div className="mt-4 flex flex-wrap gap-3"><select className={`${input} max-w-48`} value={finalDecision} onChange={(e) => setFinalDecision(e.target.value)}><option value="pass">通过</option><option value="conditional">有条件通过</option><option value="fail">不通过</option></select><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={redline} onChange={(e) => setRedline(e.target.checked)} />触发诚信／安全红线</label></div><textarea className={`${input} mt-3 min-h-20`} value={finalFeedback} onChange={(e) => setFinalFeedback(e.target.value)} placeholder="终局反馈或24小时非核心整改项" /><button className={`${button} mt-3`} disabled={busy || finalFeedback.trim().length < 8} onClick={submitFinal}>保存教师结论</button>{data?.final_review && <p className="mt-3 text-sm text-slate-400">{data.final_review.current ? "当前结论" : "历史结论（材料改版后已失效）"}：{data.final_review.decision} · {data.final_review.feedback}</p>}</section>

      <section className={box}><h2 className="text-lg font-semibold">D8 初评与 D9 最终排序</h2><p className="mt-1 text-sm text-slate-400">双门槛通过者按项目与 Agent 平均分暂列前50%；入围组完成答辩后按三项总分形成最终名次。</p><div className="mt-3 overflow-x-auto"><table className="w-full text-left text-sm"><thead className="text-slate-400"><tr><th className="p-2">初排名</th><th className="p-2">项目</th><th className="p-2">项目</th><th className="p-2">Agent</th><th className="p-2">D8分</th><th className="p-2">暂列</th><th className="p-2">答辩</th><th className="p-2">300分总分</th><th className="p-2">最终名次</th></tr></thead><tbody>{ranking?.rows.map((r) => <tr key={r.project_id} className="border-t border-white/10"><td className="p-2">{r.rank}</td><td className="p-2">{r.name}</td><td className="p-2">{r.project_score}</td><td className="p-2">{r.agent_score}</td><td className="p-2">{r.ranking_score}</td><td className="p-2">{r.provisional_shortlist ? "入围" : "未入围"}</td><td className="p-2">{r.defense_score ?? "待答辩"}</td><td className="p-2">{r.final_total ?? "—"}</td><td className="p-2">{r.final_rank ?? "—"}</td></tr>)}</tbody></table></div><p className="mt-2 text-xs text-slate-500">有效项目 {ranking?.eligible_count ?? 0} 个，暂列名额 {ranking?.provisional_slots ?? 0} 个，已录入答辩分 {ranking?.finalists_scored ?? 0} 个；最终仍由教师确认。</p></section>
    </>}
  </div></div>;
}
