"use client";
import { useState, useEffect, useRef } from "react";
import {
  listProjects, createProject,
  getTimeline, getBenchmark, checkPitch, analyzeInterview,
  getEvidenceDashboard,
} from "@/lib/api";
import { Project, User } from "@/lib/types";
import ScoreRadar from "@/components/ScoreRadar";
import TeamPanel from "@/components/TeamPanel";
import LearningPath from "@/components/LearningPath";
import WeeklyReport from "@/components/WeeklyReport";

// ── Constants ─────────────────────────────────────────────────
const STAGE_MAP: Record<string, { label: string; color: string }> = {
  discovery: { label: "痛点发现", color: "#6366f1" },
  ideation:  { label: "方案策划", color: "#22d3ee" },
  modeling:  { label: "商业建模", color: "#a78bfa" },
  execution: { label: "资源杠杆", color: "#f59e0b" },
  pitching:  { label: "路演表达", color: "#10b981" },
};

const DIMS = ["empathy", "ideation", "business", "execution", "pitching"] as const;
const DIM_LABELS: Record<string, string> = {
  empathy: "痛点发现", ideation: "方案策划",
  business: "商业建模", execution: "资源杠杆", pitching: "路演表达",
};

type TabId = "overview" | "timeline" | "benchmark" | "pitch" | "interview" | "evidence" | "learning" | "report" | "team";
const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: "overview",   label: "概览",     icon: "📋" },
  { id: "timeline",   label: "成长时间线", icon: "📈" },
  { id: "benchmark",  label: "对标分析",  icon: "🏆" },
  { id: "pitch",      label: "路演检查",  icon: "🎤" },
  { id: "interview",  label: "访谈解析",  icon: "🎙" },
  { id: "evidence",   label: "证据追踪",  icon: "🔍" },
  { id: "learning",   label: "学习路径",  icon: "🗺" },
  { id: "report",     label: "周报",     icon: "📰" },
  { id: "team",       label: "团队",     icon: "👥" },
];

function scoreColor(v: number) {
  if (v >= 7) return "#10b981";
  if (v >= 5) return "#f59e0b";
  return "#ef4444";
}
function scoreGrad(v: number) {
  if (v >= 7) return "linear-gradient(90deg,#10b981,#34d399)";
  if (v >= 5) return "linear-gradient(90deg,#f59e0b,#fbbf24)";
  return "linear-gradient(90deg,#ef4444,#f87171)";
}

// ── Mini SVG line chart ─────────────────────────────────────
function SparkLine({ values, color }: { values: number[]; color: string }) {
  if (values.length < 2) return <span className="text-xs" style={{ color: "var(--text-muted)" }}>数据不足</span>;
  const W = 120, H = 36, pad = 4;
  const max = Math.max(...values, 10);
  const pts = values.map((v, i) => {
    const x = pad + (i / (values.length - 1)) * (W - pad * 2);
    const y = H - pad - ((v / max) * (H - pad * 2));
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg width={W} height={H} style={{ overflow: "visible" }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
      {values.map((v, i) => {
        const x = pad + (i / (values.length - 1)) * (W - pad * 2);
        const y = H - pad - ((v / max) * (H - pad * 2));
        return <circle key={i} cx={x} cy={y} r="3" fill={color} />;
      })}
    </svg>
  );
}

// ── F6: Auto Diagnosis Summary ───────────────────────────────
function generateDiagnosisSummary(project: Project, timeline: any): string {
  const scores = (project.scores as any) || {};
  const dims = ["empathy", "ideation", "business", "execution", "pitching"] as const;
  const labels: Record<string, string> = {
    empathy: "痛点发现", ideation: "方案策划",
    business: "商业建模", execution: "资源杠杆", pitching: "路演表达",
  };

  // Detect stagnation: 2+ consecutive snapshots with no change in a dimension
  if (timeline?.snapshots?.length >= 2) {
    const snaps = timeline.snapshots;
    let worstDim = "";
    let worstRounds = 0;
    for (const dim of dims) {
      let noChange = 0;
      for (let i = snaps.length - 1; i > 0; i--) {
        const curr = snaps[i].scores?.[dim] ?? 0;
        const prev = snaps[i - 1].scores?.[dim] ?? 0;
        if (curr === prev) noChange++;
        else break;
      }
      if (noChange >= 2 && noChange > worstRounds) {
        worstDim = dim;
        worstRounds = noChange;
      }
    }
    if (worstDim) {
      return `「${labels[worstDim]}」已连续 ${worstRounds} 轮无进展，建议本次对话重点讨论相关问题。`;
    }
  }

  // Top diagnosis warning
  if (project.diagnosis?.length > 0) {
    return `检测到待解决问题「${project.diagnosis[0]}」，建议下次对话优先处理。`;
  }

  // Lowest dimension score
  const scored = dims.filter((d) => scores[d] > 0);
  if (scored.length > 0) {
    const lowest = scored.reduce((a, b) => scores[a] < scores[b] ? a : b);
    if (scores[lowest] < 5) {
      return `「${labels[lowest]}」得分偏低（${scores[lowest]}/10），建议与 AI 教练重点讨论。`;
    }
  }

  // No scores yet
  if (!scored.length) {
    return "项目尚未开始评估，建议前往「AI 教练」进行首次对话。";
  }

  return "项目整体进展良好，继续保持！";
}

// ── Main Page ────────────────────────────────────────────────
export default function ProjectsPage() {
  const [projects, setProjects]     = useState<Project[]>([]);
  const [selected, setSelected]     = useState<Project | null>(null);
  const [activeTab, setActiveTab]   = useState<TabId>("overview");
  const [reportKey, setReportKey]   = useState(0);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm]             = useState({ name: "", industry: "", description: "" });
  const [sidebarWidth, setSidebarWidth] = useState(256);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const isDragging = useRef(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(0);

  const onDragStart = (e: React.MouseEvent) => {
    isDragging.current = true;
    dragStartX.current = e.clientX;
    dragStartWidth.current = sidebarWidth;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  };

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!isDragging.current) return;
      const delta = e.clientX - dragStartX.current;
      const newWidth = Math.max(160, Math.min(400, dragStartWidth.current + delta));
      setSidebarWidth(newWidth);
    };
    const onUp = () => {
      isDragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => { window.removeEventListener("mousemove", onMove); window.removeEventListener("mouseup", onUp); };
  }, []);

  // Tab data
  const [timeline, setTimeline]     = useState<any>(null);
  const [benchmark, setBenchmark]   = useState<any>(null);
  const [pitchResult, setPitchResult] = useState<any>(null);
  const [pitchOutline, setPitchOutline] = useState("");
  const [pitchLoading, setPitchLoading] = useState(false);
  const [interviewResult, setInterviewResult] = useState<any>(null);
  const [interviewText, setInterviewText]     = useState("");
  const [interviewLoading, setInterviewLoading] = useState(false);
  const [evidence, setEvidence]     = useState<any>(null);

  useEffect(() => { loadProjects(); }, []);

  useEffect(() => {
    if (!selected) return;
    setTimeline(null); setBenchmark(null); setPitchResult(null); setInterviewResult(null); setEvidence(null);
    // Always load timeline for overview diagnosis summary (F6)
    loadTimeline();
    if (activeTab === "benchmark") loadBenchmark();
    if (activeTab === "evidence")  loadEvidence();
  }, [selected, activeTab]);

  const loadProjects = async () => {
    try { const r = await listProjects(); setProjects(r.projects); } catch {}
  };
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createProject(form.name, form.industry, form.description);
      setShowCreate(false); setForm({ name: "", industry: "", description: "" });
      loadProjects();
    } catch {}
  };
  const loadTimeline  = async () => { if (!selected) return; try { setTimeline(await getTimeline(selected.project_id)); } catch {} };
  const loadBenchmark = async () => { if (!selected) return; try { setBenchmark(await getBenchmark(selected.project_id)); } catch {} };
  const loadEvidence  = async () => { if (!selected) return; try { setEvidence(await getEvidenceDashboard(selected.project_id)); } catch {} };
  const handlePitchCheck = async () => {
    if (!pitchOutline.trim() || !selected) return;
    setPitchLoading(true);
    try { setPitchResult(await checkPitch(selected.project_id, pitchOutline)); } catch {} finally { setPitchLoading(false); }
  };
  const handleInterviewAnalyze = async () => {
    if (!interviewText.trim() || !selected) return;
    setInterviewLoading(true);
    try { setInterviewResult(await analyzeInterview(selected.project_id, interviewText)); } catch {} finally { setInterviewLoading(false); }
  };

  const stageMeta = selected ? (STAGE_MAP[selected.stage] || { label: selected.stage, color: "#6366f1" }) : null;

  return (
    <div className="flex h-full" style={{ background: "var(--bg-base)" }}>

      {/* ── Left: project list ─────────────────────────────── */}
      <div className="flex-shrink-0 flex flex-col overflow-hidden transition-all"
           style={{
             width: sidebarCollapsed ? 0 : sidebarWidth,
             minWidth: sidebarCollapsed ? 0 : 160,
             borderRight: sidebarCollapsed ? "none" : "1px solid var(--border)",
             background: "rgba(8,13,26,0.8)",
             overflow: "hidden",
           }}>
        <div className="px-4 py-3 flex items-center justify-between flex-shrink-0"
             style={{ borderBottom: "1px solid var(--border)" }}>
          <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>我的项目</p>
          <div className="flex gap-1.5">
            <button onClick={loadProjects} className="text-xs px-2 py-1 rounded-lg transition-all"
                    style={{ color: "var(--text-muted)", background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)" }}>↻</button>
            <button onClick={() => setShowCreate(true)} className="btn-glow text-xs px-2 py-1 rounded-lg">+ 新建</button>
          </div>
        </div>

        {showCreate && (
          <form onSubmit={handleCreate} className="p-3 space-y-2 flex-shrink-0"
                style={{ borderBottom: "1px solid var(--border)", background: "rgba(99,102,241,0.04)" }}>
            {[
              { key: "name", placeholder: "项目名称 *" },
              { key: "industry", placeholder: "行业领域" },
            ].map(({ key, placeholder }) => (
              <input key={key} type="text" placeholder={placeholder} required={key === "name"}
                     value={(form as any)[key]}
                     onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                     className="w-full px-3 py-1.5 rounded-lg text-xs outline-none"
                     style={{ background: "rgba(255,255,255,0.06)", border: "1px solid var(--border)", color: "var(--text-primary)" }} />
            ))}
            <textarea placeholder="简要描述" rows={2} value={form.description}
                      onChange={(e) => setForm({ ...form, description: e.target.value })}
                      className="w-full px-3 py-1.5 rounded-lg text-xs outline-none resize-none"
                      style={{ background: "rgba(255,255,255,0.06)", border: "1px solid var(--border)", color: "var(--text-primary)" }} />
            <div className="flex gap-2">
              <button type="submit" className="btn-glow text-xs px-3 py-1.5 rounded-lg flex-1">创建</button>
              <button type="button" onClick={() => setShowCreate(false)}
                      className="text-xs px-3 py-1.5 rounded-lg"
                      style={{ color: "var(--text-muted)", background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)" }}>取消</button>
            </div>
          </form>
        )}

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {projects.length === 0 ? (
            <div className="text-center py-10">
              <div className="text-3xl mb-2 opacity-30">📋</div>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>暂无项目</p>
            </div>
          ) : projects.map((proj) => {
            const sm = STAGE_MAP[proj.stage] || { label: proj.stage, color: "#6366f1" };
            const isActive = selected?.project_id === proj.project_id;
            return (
              <button key={proj.project_id} onClick={() => { setSelected(proj); setActiveTab("overview"); }}
                      className="w-full text-left px-3 py-2.5 rounded-xl transition-all"
                      style={{
                        background: isActive ? "rgba(99,102,241,0.12)" : "transparent",
                        border: `1px solid ${isActive ? "rgba(99,102,241,0.3)" : "transparent"}`,
                      }}>
                <div className="flex items-center justify-between mb-1">
                  <p className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>{proj.name}</p>
                  <span className="text-xs px-1.5 py-0.5 rounded-full flex-shrink-0 ml-1"
                        style={{ background: `${sm.color}18`, color: sm.color, border: `1px solid ${sm.color}30`, fontSize: "0.6rem" }}>
                    {sm.label}
                  </span>
                </div>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>{proj.industry || "未设置行业"}</p>
                {proj.diagnosis?.length > 0 && (
                  <p className="text-xs mt-1" style={{ color: "#fcd34d" }}>⚠ {proj.diagnosis.length} 个待解决问题</p>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Drag handle + collapse button ─────────────────── */}
      <div
        style={{ width: 4, flexShrink: 0, cursor: "col-resize", background: "transparent", position: "relative" }}
        onMouseDown={sidebarCollapsed ? undefined : onDragStart}
      >
        <div style={{
          position: "absolute", top: "50%", left: "50%",
          transform: "translate(-50%, -50%)",
          zIndex: 10,
        }}>
          <button
            onClick={() => setSidebarCollapsed(c => !c)}
            style={{
              width: 16, height: 32, borderRadius: 8,
              background: "rgba(255,255,255,0.08)",
              border: "1px solid var(--border)",
              color: "var(--text-muted)",
              cursor: "pointer", fontSize: 10, display: "flex",
              alignItems: "center", justifyContent: "center",
            }}
          >
            {sidebarCollapsed ? "›" : "‹"}
          </button>
        </div>
      </div>

      {/* ── Right: detail ─────────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {!selected ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="text-5xl mb-4 opacity-20">📋</div>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>从左侧选择项目查看详情</p>
            </div>
          </div>
        ) : (
          <>
            {/* Project header */}
            <div className="flex items-center gap-4 px-6 py-3 flex-shrink-0"
                 style={{ borderBottom: "1px solid var(--border)", background: "rgba(8,13,26,0.9)" }}>
              <div>
                <h1 className="text-base font-bold gradient-text">{selected.name}</h1>
                <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                  {selected.industry} · {selected.description?.slice(0, 40) || "暂无描述"}
                </p>
              </div>
              {stageMeta && (
                <span className="px-3 py-1 rounded-xl text-xs font-medium"
                      style={{ background: `${stageMeta.color}18`, color: stageMeta.color, border: `1px solid ${stageMeta.color}30` }}>
                  {stageMeta.label}
                </span>
              )}
              <button onClick={() => window.print()} className="ml-auto text-xs px-3 py-1.5 rounded-lg no-print transition-all"
                      style={{ color: "var(--text-muted)", background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)" }}>
                ⎙ 打印报告
              </button>
            </div>

            {/* Tabs */}
            <div className="flex flex-wrap gap-2 px-4 py-3 flex-shrink-0"
                 style={{ borderBottom: "1px solid var(--border)" }}>
              {TABS.map((tab) => (
                <button key={tab.id} onClick={() => { setActiveTab(tab.id); if (tab.id === "report") setReportKey(k => k + 1); }}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
                        style={{
                          background: activeTab === tab.id ? "rgba(99,102,241,0.15)" : "rgba(255,255,255,0.04)",
                          border: `1px solid ${activeTab === tab.id ? "rgba(99,102,241,0.4)" : "var(--border)"}`,
                          color: activeTab === tab.id ? "#a5b4fc" : "var(--text-muted)",
                          boxShadow: activeTab === tab.id ? "0 0 12px rgba(99,102,241,0.15)" : "none",
                        }}>
                  <span>{tab.icon}</span>{tab.label}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div className="flex-1 overflow-y-auto p-6">

              {/* ── OVERVIEW ── */}
              {activeTab === "overview" && (
                <div className="space-y-6 animate-fadeInUp">
                  {/* F6: Auto Diagnosis Summary Banner */}
                  {(() => {
                    const summary = generateDiagnosisSummary(selected, timeline);
                    const isGood = summary.includes("良好");
                    return (
                      <div className="rounded-xl px-5 py-4 flex items-start gap-3"
                           style={{
                             background: isGood ? "rgba(16,185,129,0.06)" : "rgba(99,102,241,0.08)",
                             border: `1px solid ${isGood ? "rgba(16,185,129,0.2)" : "rgba(99,102,241,0.25)"}`,
                           }}>
                        <span style={{ fontSize: "1.1rem" }}>{isGood ? "✅" : "💡"}</span>
                        <div>
                          <p className="text-xs font-semibold mb-1" style={{ color: isGood ? "#6ee7b7" : "#a5b4fc" }}>AI 诊断摘要</p>
                          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>{summary}</p>
                        </div>
                      </div>
                    );
                  })()}
                  {selected.scores && Object.values(selected.scores).some(v => v > 0) ? (
                    <div className="grid grid-cols-2 gap-5">
                      <div className="rounded-2xl p-6" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                        <p className="text-xs font-semibold mb-4" style={{ color: "var(--text-muted)" }}>能力评估雷达图</p>
                        <ScoreRadar scores={selected.scores} />
                      </div>
                      <div className="rounded-2xl p-6" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                        <p className="text-xs font-semibold mb-4" style={{ color: "var(--text-muted)" }}>各维度得分</p>
                        <div className="space-y-4">
                        {DIMS.map((d) => {
                          const v = (selected.scores as any)?.[d] || 0;
                          return (
                            <div key={d}>
                              <div className="flex justify-between mb-1.5">
                                <span className="text-xs" style={{ color: "var(--text-secondary)" }}>{DIM_LABELS[d]}</span>
                                <span className="text-xs font-bold" style={{ color: scoreColor(v) }}>{v} / 10</span>
                              </div>
                              <div className="h-2 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                                <div className="h-2 rounded-full" style={{ width: `${v * 10}%`, background: scoreGrad(v) }} />
                              </div>
                            </div>
                          );
                        })}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-12 rounded-2xl" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                      <div className="text-4xl mb-3 opacity-30">💬</div>
                      <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>暂无评估数据</p>
                      <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>先去「AI 教练」对话，评分数据将自动同步</p>
                    </div>
                  )}

                  {selected.diagnosis?.length > 0 && (
                    <div className="rounded-2xl p-6" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                      <p className="text-xs font-semibold mb-4" style={{ color: "var(--text-muted)" }}>诊断发现</p>
                      <div className="space-y-2.5">
                        {selected.diagnosis.map((d, i) => (
                          <div key={i} className="flex gap-3 px-4 py-3 rounded-xl text-sm"
                               style={{ background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.2)" }}>
                            <span style={{ color: "#fcd34d" }}>⚠</span>
                            <span style={{ color: "var(--text-secondary)" }}>{d}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ── TIMELINE ── */}
              {activeTab === "timeline" && (
                <div className="space-y-6 animate-fadeInUp">
                  <div className="rounded-2xl p-6" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                    <div className="flex items-center justify-between mb-4">
                      <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>成长时间线</p>
                      {timeline && <span className="badge badge-blue text-xs">{timeline.total_rounds} 轮对话记录</span>}
                    </div>

                    {!timeline ? (
                      <div className="text-center py-10">
                        <div className="text-3xl mb-2 opacity-30">📈</div>
                        <p className="text-xs" style={{ color: "var(--text-muted)" }}>加载中...</p>
                      </div>
                    ) : timeline.total_rounds === 0 ? (
                      <div className="text-center py-10">
                        <div className="text-3xl mb-2 opacity-30">📈</div>
                        <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>暂无记录</p>
                        <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>与 AI 教练对话后，得分变化将在此展示</p>
                      </div>
                    ) : (
                      <>
                        {/* Sparklines per dimension */}
                        <div className="space-y-4 mb-6">
                          {DIMS.map((d) => {
                            const vals = timeline.series?.[d] || [];
                            const latest = vals[vals.length - 1] || 0;
                            const trendInfo = timeline.trend?.[d];
                            return (
                              <div key={d} className="flex items-center gap-4">
                                <span className="text-xs w-16 flex-shrink-0" style={{ color: "var(--text-secondary)" }}>{DIM_LABELS[d]}</span>
                                <SparkLine values={vals} color={scoreColor(latest)} />
                                <span className="text-xs font-bold w-6" style={{ color: scoreColor(latest) }}>{latest}</span>
                                {trendInfo && (
                                  <span className="text-xs" style={{
                                    color: trendInfo.direction === "up" ? "#10b981" : trendInfo.direction === "down" ? "#ef4444" : "var(--text-muted)"
                                  }}>
                                    {trendInfo.direction === "up" ? `↑ +${trendInfo.delta}` : trendInfo.direction === "down" ? `↓ ${trendInfo.delta}` : "─ 持平"}
                                  </span>
                                )}
                              </div>
                            );
                          })}
                        </div>

                        {/* Snapshot table */}
                        <div>
                          <p className="text-xs font-semibold mb-3" style={{ color: "var(--text-muted)" }}>历史快照</p>
                          <div className="space-y-2">
                            {timeline.snapshots.map((snap: any, i: number) => (
                              <div key={i} className="flex items-center gap-3 px-3 py-2 rounded-xl"
                                   style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)" }}>
                                <span className="text-xs font-bold w-12 flex-shrink-0" style={{ color: "#a5b4fc" }}>
                                  第{snap.round_num}轮
                                </span>
                                <div className="flex gap-2 flex-1 flex-wrap">
                                  {DIMS.map((d) => {
                                    const v = snap.scores?.[d] || 0;
                                    return (
                                      <span key={d} className="text-xs px-1.5 py-0.5 rounded"
                                            style={{ background: `${scoreColor(v)}18`, color: scoreColor(v) }}>
                                        {DIM_LABELS[d].slice(0, 2)} {v}
                                      </span>
                                    );
                                  })}
                                </div>
                                <span className="text-xs flex-shrink-0" style={{ color: "var(--text-muted)" }}>
                                  {snap.created_at?.slice(5, 16)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* ── BENCHMARK ── */}
              {activeTab === "benchmark" && (
                <div className="space-y-6 animate-fadeInUp">
                  <div className="rounded-2xl p-6" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                    <div className="flex items-center justify-between mb-4">
                      <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>班级匿名对标</p>
                      {benchmark && <span className="badge badge-purple text-xs">{benchmark.class_size} 个项目参与对标</span>}
                    </div>

                    {!benchmark ? (
                      <div className="text-center py-10">
                        <div className="text-3xl mb-2 opacity-30">🏆</div>
                        <p className="text-xs" style={{ color: "var(--text-muted)" }}>加载中...</p>
                      </div>
                    ) : !benchmark.benchmark || Object.keys(benchmark.benchmark).length === 0 ? (
                      <div className="text-center py-10">
                        <div className="text-3xl mb-2 opacity-30">🏆</div>
                        <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>暂无对标数据</p>
                        <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>班级需要有更多项目完成评分后才能对标</p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {DIMS.map((d) => {
                          const bm = benchmark.benchmark?.[d];
                          if (!bm) return null;
                          const STATUS_MAP: Record<string, { label: string; color: string }> = {
                            top20:     { label: "前20%", color: "#10b981" },
                            above_avg: { label: "高于平均", color: "#6366f1" },
                            below_avg: { label: "低于平均", color: "#ef4444" },
                          };
                          const st = STATUS_MAP[bm.status] || { label: "", color: "#6366f1" };
                          return (
                            <div key={d} className="rounded-xl p-4" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)" }}>
                              <div className="flex items-center justify-between mb-3">
                                <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{DIM_LABELS[d]}</span>
                                <span className="badge text-xs px-2 py-0.5 rounded-lg"
                                      style={{ background: `${st.color}18`, color: st.color, border: `1px solid ${st.color}30` }}>
                                  {st.label}
                                </span>
                              </div>
                              {/* Score bar comparison */}
                              <div className="space-y-2">
                                {[
                                  { label: "我的得分", val: bm.my_score, color: scoreColor(bm.my_score) },
                                  { label: "班级平均", val: bm.class_avg, color: "#6366f1" },
                                  { label: "前20%线", val: bm.top20_threshold, color: "#10b981" },
                                ].map(({ label, val, color }) => (
                                  <div key={label}>
                                    <div className="flex justify-between mb-0.5">
                                      <span className="text-xs" style={{ color: "var(--text-muted)" }}>{label}</span>
                                      <span className="text-xs font-bold" style={{ color }}>{val}</span>
                                    </div>
                                    <div className="h-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                                      <div className="h-1.5 rounded-full transition-all"
                                           style={{ width: `${val * 10}%`, background: color, opacity: label === "我的得分" ? 1 : 0.4 }} />
                                    </div>
                                  </div>
                                ))}
                              </div>
                              <p className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>
                                班级排名 <span className="font-bold" style={{ color: "var(--text-primary)" }}>#{bm.rank}</span> / {bm.total}
                                &nbsp;·&nbsp;超过 <span className="font-bold" style={{ color: scoreColor(bm.percentile / 10) }}>{bm.percentile}%</span> 的项目
                              </p>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* ── 超图竞赛案例对标 ── */}
                  {benchmark && (benchmark.hypergraph?.similar_cases?.length > 0 || benchmark.hypergraph?.risk_patterns?.length > 0) && (
                    <div className="rounded-2xl p-6" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                      <p className="text-xs font-semibold mb-4" style={{ color: "var(--text-muted)" }}>
                        超图竞赛案例对标（82个真实竞赛项目）
                      </p>

                      {/* Similar cases */}
                      {benchmark.hypergraph.similar_cases?.length > 0 && (
                        <div className="mb-4">
                          <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>同行业/同技术竞赛案例</p>
                          <div className="space-y-2">
                            {benchmark.hypergraph.similar_cases.slice(0, 3).map((c: any, i: number) => (
                              <div key={i} className="rounded-xl p-3" style={{ background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.15)" }}>
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="text-xs font-bold" style={{ color: "#a5b4fc" }}>{c.name || c.project}</span>
                                  <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: "rgba(99,102,241,0.15)", color: "#c4b5fd", fontSize: "0.65rem" }}>{c.industry}</span>
                                </div>
                                {c.success_factors?.length > 0 && (
                                  <p className="text-xs" style={{ color: "#6ee7b7" }}>✅ {c.success_factors.slice(0, 2).join("；")}</p>
                                )}
                                {c.failure_risks?.length > 0 && (
                                  <p className="text-xs mt-0.5" style={{ color: "#fca5a5" }}>⚠ {c.failure_risks.slice(0, 1).join("；")}</p>
                                )}
                                {c.moat?.length > 0 && (
                                  <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>壁垒：{c.moat.slice(0, 2).join("、")}</p>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Risk patterns */}
                      {benchmark.hypergraph.risk_patterns?.length > 0 && (
                        <div>
                          <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>超图风险模式提示</p>
                          <div className="space-y-1.5">
                            {benchmark.hypergraph.risk_patterns.slice(0, 3).map((r: any, i: number) => {
                              const sev = r.severity === "high" ? { color: "#ef4444", bg: "rgba(239,68,68,0.06)" }
                                        : r.severity === "medium" ? { color: "#f59e0b", bg: "rgba(245,158,11,0.06)" }
                                        : { color: "#6366f1", bg: "rgba(99,102,241,0.06)" };
                              return (
                                <div key={i} className="rounded-lg px-3 py-2" style={{ background: sev.bg, border: `1px solid ${sev.color}25` }}>
                                  <span className="text-xs font-medium" style={{ color: sev.color }}>{r.risk}</span>
                                  {r.note && <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>{r.note}</p>}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* ── AI 对标洞察 ── */}
                  {benchmark?.ai_insight && Object.keys(benchmark.ai_insight).length > 0 && (
                    <div className="rounded-2xl p-6" style={{ background: "rgba(99,102,241,0.05)", border: "1px solid rgba(99,102,241,0.2)" }}>
                      <p className="text-xs font-semibold mb-3" style={{ color: "#a5b4fc" }}>AI 对标洞察</p>
                      {benchmark.ai_insight.summary && (
                        <p className="text-sm mb-4" style={{ color: "var(--text-primary)" }}>{benchmark.ai_insight.summary}</p>
                      )}
                      <div className="grid grid-cols-2 gap-3">
                        {benchmark.ai_insight.gaps?.length > 0 && (
                          <div className="rounded-xl p-3" style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.15)" }}>
                            <p className="text-xs font-semibold mb-2" style={{ color: "#fca5a5" }}>待提升差距</p>
                            {benchmark.ai_insight.gaps.map((g: string, i: number) => (
                              <p key={i} className="text-xs mb-1" style={{ color: "var(--text-secondary)" }}>• {g}</p>
                            ))}
                          </div>
                        )}
                        {benchmark.ai_insight.learnings?.length > 0 && (
                          <div className="rounded-xl p-3" style={{ background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.15)" }}>
                            <p className="text-xs font-semibold mb-2" style={{ color: "#6ee7b7" }}>可借鉴要素</p>
                            {benchmark.ai_insight.learnings.map((l: string, i: number) => (
                              <p key={i} className="text-xs mb-1" style={{ color: "var(--text-secondary)" }}>• {l}</p>
                            ))}
                          </div>
                        )}
                      </div>
                      {benchmark.ai_insight.suggestion && (
                        <div className="mt-3 rounded-xl p-3" style={{ background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.2)" }}>
                          <p className="text-xs font-semibold mb-1" style={{ color: "#fcd34d" }}>改进建议</p>
                          <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{benchmark.ai_insight.suggestion}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* ── PITCH CHECK ── */}
              {activeTab === "pitch" && (
                <div className="space-y-6 animate-fadeInUp">
                  <div className="rounded-2xl p-6" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                    <p className="text-xs font-semibold mb-1" style={{ color: "var(--text-muted)" }}>Pitch Deck 结构检查器</p>
                    <p className="text-xs mb-4" style={{ color: "var(--text-muted)" }}>
                      粘贴你的路演大纲（标题 + 要点），AI 自动检测 7 大模块是否完整
                    </p>
                    <textarea
                      rows={8}
                      placeholder={"示例：\n第1页：问题\n- 大学生找工作需要投递50+份简历\n- 平均响应率不到5%\n\n第2页：我们的解决方案\n- AI简历优化平台..."}
                      value={pitchOutline}
                      onChange={(e) => setPitchOutline(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl text-sm resize-none outline-none"
                      style={{
                        background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)",
                        color: "var(--text-primary)", fontFamily: "monospace",
                      }}
                    />
                    <button onClick={handlePitchCheck} disabled={pitchLoading || !pitchOutline.trim()}
                            className="mt-3 btn-glow px-5 py-2 rounded-xl text-sm font-medium disabled:opacity-40">
                      {pitchLoading ? "检查中..." : "🎤 开始结构检查"}
                    </button>
                  </div>

                  {pitchResult && (
                    <div className="rounded-2xl p-6 animate-fadeInUp" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                      {/* Summary */}
                      <div className="flex items-center gap-4 mb-5 p-4 rounded-xl"
                           style={{ background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.2)" }}>
                        <div className="text-center">
                          <p className="text-2xl font-bold gradient-text">{pitchResult.summary?.covered_count}/{pitchResult.summary?.total}</p>
                          <p className="text-xs" style={{ color: "var(--text-muted)" }}>模块已覆盖</p>
                        </div>
                        <div className="text-center">
                          <p className="text-2xl font-bold" style={{ color: scoreColor(pitchResult.summary?.avg_score) }}>
                            {pitchResult.summary?.avg_score}
                          </p>
                          <p className="text-xs" style={{ color: "var(--text-muted)" }}>平均分</p>
                        </div>
                        <div className="flex-1">
                          <span className="badge text-sm px-3 py-1" style={{
                            background: pitchResult.summary?.overall_grade === "优秀" ? "rgba(16,185,129,0.12)" : "rgba(245,158,11,0.12)",
                            color: pitchResult.summary?.overall_grade === "优秀" ? "#10b981" : "#f59e0b",
                            border: `1px solid ${pitchResult.summary?.overall_grade === "优秀" ? "rgba(16,185,129,0.3)" : "rgba(245,158,11,0.3)"}`,
                          }}>
                            {pitchResult.summary?.overall_grade}
                          </span>
                          {pitchResult.summary?.h14_triggered && (
                            <p className="text-xs mt-1" style={{ color: "#ef4444" }}>⚠ 触发 H14：路演叙事断裂</p>
                          )}
                        </div>
                      </div>

                      {/* Per-section results */}
                      <div className="grid grid-cols-1 gap-3">
                        {[
                          { id: "problem",  name: "问题定义" },
                          { id: "solution", name: "解决方案" },
                          { id: "market",   name: "市场规模" },
                          { id: "model",    name: "商业模式" },
                          { id: "team",     name: "团队介绍" },
                          { id: "traction", name: "牵引力数据" },
                          { id: "ask",      name: "融资需求" },
                        ].map(({ id, name }) => {
                          const s = pitchResult.result?.[id];
                          if (!s) return null;
                          return (
                            <div key={id} className="flex items-start gap-3 px-4 py-3 rounded-xl"
                                 style={{
                                   background: s.covered ? "rgba(16,185,129,0.04)" : "rgba(239,68,68,0.04)",
                                   border: `1px solid ${s.covered ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)"}`,
                                 }}>
                              <span style={{ color: s.covered ? "#10b981" : "#ef4444", fontSize: "1rem" }}>
                                {s.covered ? "✓" : "✗"}
                              </span>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-0.5">
                                  <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{name}</span>
                                  {s.covered && (
                                    <span className="text-xs font-bold" style={{ color: scoreColor(s.score) }}>{s.score}/10</span>
                                  )}
                                </div>
                                <p className="text-xs" style={{ color: "var(--text-muted)" }}>{s.tip}</p>
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      {pitchResult.summary?.missing_sections?.length > 0 && (
                        <div className="mt-4 px-4 py-3 rounded-xl"
                             style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)" }}>
                          <p className="text-xs font-medium mb-1" style={{ color: "#fca5a5" }}>缺失模块：</p>
                          <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
                            {pitchResult.summary.missing_sections.join("、")}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* ── INTERVIEW ANALYZE ── */}
              {activeTab === "interview" && (
                <div className="space-y-6 animate-fadeInUp">
                  <div className="rounded-2xl p-6" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                    <p className="text-xs font-semibold mb-1" style={{ color: "var(--text-muted)" }}>用户访谈报告解析器</p>
                    <p className="text-xs mb-4" style={{ color: "var(--text-muted)" }}>
                      粘贴访谈对话记录，AI 自动提取 JTBD、痛点、支付意愿，生成 R1/R2 证据
                    </p>
                    <textarea
                      rows={10}
                      placeholder={"示例：\n访谈对象：张同学，大三，计算机专业\n\n问：你平时找实习遇到最大的困难是什么？\n答：主要是简历投出去没有回音，也不知道怎么改。\n\n问：如果有一个AI帮你优化简历，你愿意付费吗？\n答：如果真的有用的话，50-100块一个月还可以接受..."}
                      value={interviewText}
                      onChange={(e) => setInterviewText(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl text-sm resize-none outline-none"
                      style={{
                        background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)",
                        color: "var(--text-primary)", fontFamily: "monospace",
                      }}
                    />
                    <button onClick={handleInterviewAnalyze} disabled={interviewLoading || !interviewText.trim()}
                            className="mt-3 btn-glow px-5 py-2 rounded-xl text-sm font-medium disabled:opacity-40">
                      {interviewLoading ? "解析中..." : "🎙 开始解析访谈"}
                    </button>
                  </div>

                  {interviewResult?.result && (
                    <div className="space-y-4 animate-fadeInUp">
                      {/* Summary */}
                      <div className="rounded-2xl p-4" style={{ background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.2)" }}>
                        <p className="text-xs font-semibold mb-2" style={{ color: "var(--text-muted)" }}>核心发现</p>
                        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>{interviewResult.result.summary}</p>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        {/* JTBD Statements */}
                        <div className="rounded-2xl p-4" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                          <p className="text-xs font-semibold mb-3" style={{ color: "var(--text-muted)" }}>JTBD 语句</p>
                          <div className="space-y-2">
                            {(interviewResult.result.jtbd_statements || []).map((s: string, i: number) => (
                              <div key={i} className="px-3 py-2 rounded-lg text-xs"
                                   style={{ background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.2)", color: "var(--text-secondary)" }}>
                                {s}
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Pain Points */}
                        <div className="rounded-2xl p-4" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                          <p className="text-xs font-semibold mb-3" style={{ color: "var(--text-muted)" }}>痛点提取</p>
                          <div className="space-y-2">
                            {(interviewResult.result.pain_points || []).map((p: any, i: number) => (
                              <div key={i} className="px-3 py-2 rounded-lg"
                                   style={{ background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.2)" }}>
                                <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{p.description}</p>
                                <div className="flex gap-2 mt-1">
                                  <span className="text-xs" style={{ color: "#fcd34d" }}>频率：{p.frequency}</span>
                                  <span className="text-xs" style={{ color: "#fcd34d" }}>强度：{p.intensity}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>

                      {/* Payment Willingness */}
                      {interviewResult.result.payment_willingness && (
                        <div className="rounded-2xl p-4" style={{
                          background: interviewResult.result.payment_willingness.willing ? "rgba(16,185,129,0.06)" : "rgba(239,68,68,0.06)",
                          border: `1px solid ${interviewResult.result.payment_willingness.willing ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)"}`,
                        }}>
                          <div className="flex items-center gap-2 mb-2">
                            <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>支付意愿</p>
                            <span className="badge text-xs" style={{
                              background: interviewResult.result.payment_willingness.willing ? "rgba(16,185,129,0.12)" : "rgba(239,68,68,0.12)",
                              color: interviewResult.result.payment_willingness.willing ? "#10b981" : "#ef4444",
                            }}>
                              {interviewResult.result.payment_willingness.willing ? "✓ 有支付意愿" : "✗ 无明确支付意愿"}
                            </span>
                            {interviewResult.result.payment_willingness.price_range !== "未明确" && (
                              <span className="text-xs font-bold" style={{ color: "#10b981" }}>
                                {interviewResult.result.payment_willingness.price_range}
                              </span>
                            )}
                          </div>
                          <p className="text-xs italic" style={{ color: "var(--text-muted)" }}>
                            「{interviewResult.result.payment_willingness.evidence_quote}」
                          </p>
                        </div>
                      )}

                      {/* Rubric Evidence */}
                      {interviewResult.result.rubric_evidence && (
                        <div className="rounded-2xl p-4" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                          <p className="text-xs font-semibold mb-3" style={{ color: "var(--text-muted)" }}>Rubric 证据生成</p>
                          <div className="space-y-2">
                            {Object.entries(interviewResult.result.rubric_evidence).map(([rubric, evidence]) => (
                              <div key={rubric} className="flex gap-3 items-start">
                                <span className="badge badge-blue text-xs flex-shrink-0 mt-0.5">{rubric}</span>
                                <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{evidence as string}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Key Quotes */}
                      {interviewResult.result.key_quotes?.length > 0 && (
                        <div className="rounded-2xl p-4" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                          <p className="text-xs font-semibold mb-3" style={{ color: "var(--text-muted)" }}>关键引语</p>
                          <div className="space-y-3">
                            {interviewResult.result.key_quotes.map((q: any, i: number) => (
                              <div key={i}>
                                <p className="text-xs italic px-3 py-2 rounded-lg mb-1"
                                   style={{ background: "rgba(255,255,255,0.03)", color: "var(--text-secondary)", borderLeft: "2px solid #6366f1" }}>
                                  「{q.quote}」
                                </p>
                                <p className="text-xs ml-3" style={{ color: "var(--text-muted)" }}>→ {q.insight}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* ── EVIDENCE DASHBOARD (F4) ── */}
              {activeTab === "evidence" && (
                <div className="space-y-6 animate-fadeInUp">
                  <div className="rounded-2xl p-6" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                    <div className="flex items-center justify-between mb-4">
                      <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>证据追踪仪表盘</p>
                      {evidence && evidence.total > 0 && (
                        <span className="badge badge-blue text-xs">{evidence.total} 条证据</span>
                      )}
                    </div>

                    {!evidence ? (
                      <div className="text-center py-10">
                        <div className="text-3xl mb-2 opacity-30">🔍</div>
                        <p className="text-xs" style={{ color: "var(--text-muted)" }}>加载中...</p>
                      </div>
                    ) : evidence.total === 0 ? (
                      <div className="text-center py-10">
                        <div className="text-3xl mb-2 opacity-30">🔍</div>
                        <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>暂无证据记录</p>
                        <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>与 AI 教练对话后，证据将自动提取</p>
                      </div>
                    ) : (
                      <>
                        {/* Evidence type counters */}
                        <div className="grid grid-cols-4 gap-3 mb-5">
                          {[
                            { type: "DATA",   label: "数据支撑", color: "#10b981" },
                            { type: "QUOTE",  label: "引用来源", color: "#6366f1" },
                            { type: "CLAIM",  label: "待验证主张", color: "#f59e0b" },
                            { type: "COMMIT", label: "承诺计划", color: "#22d3ee" },
                          ].map(({ type, label, color }) => (
                            <div key={type} className="text-center rounded-xl py-3"
                                 style={{ background: `${color}10`, border: `1px solid ${color}25` }}>
                              <p className="text-xl font-bold" style={{ color }}>{evidence.by_type?.[type] || 0}</p>
                              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>{label}</p>
                            </div>
                          ))}
                        </div>

                        {/* Weak claims warning */}
                        {evidence.weak_claims?.length > 0 && (
                          <div className="mb-4 rounded-xl p-4"
                               style={{ background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.25)" }}>
                            <p className="text-xs font-semibold mb-2" style={{ color: "#fbbf24" }}>
                              ⚠ {evidence.weak_claims.length} 个主张缺乏数据支撑
                            </p>
                            <div className="space-y-1.5">
                              {evidence.weak_claims.slice(0, 4).map((c: any, i: number) => (
                                <div key={i} className="flex gap-2 items-start">
                                  <span className="text-xs px-1.5 py-0.5 rounded flex-shrink-0"
                                        style={{ background: "rgba(245,158,11,0.12)", color: "#fcd34d", fontSize: "0.6rem" }}>
                                    第{c.turn}轮
                                  </span>
                                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>{c.text?.slice(0, 60)}...</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Per-rubric breakdown */}
                        <div>
                          <p className="text-xs font-semibold mb-3" style={{ color: "var(--text-muted)" }}>各维度证据分布</p>
                          <div className="space-y-2">
                            {Object.entries(evidence.by_rubric || {}).map(([rubric, count]) => {
                              const RUBRIC_CN: Record<string, string> = {
                                R1_pain_point: "R1 痛点", R2_user_evidence: "R2 用户证据",
                                R3_solution: "R3 方案", R4_business_model: "R4 商业模式",
                                R5_market: "R5 市场", R6_finance: "R6 财务",
                                R7_innovation: "R7 创新", R8_execution: "R8 执行",
                                R9_pitch: "R9 路演",
                              };
                              const cnt = count as number;
                              return (
                                <div key={rubric} className="flex items-center gap-3">
                                  <span className="text-xs w-24 flex-shrink-0" style={{ color: "var(--text-secondary)" }}>
                                    {RUBRIC_CN[rubric] || rubric}
                                  </span>
                                  <div className="flex-1 h-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                                    <div className="h-1.5 rounded-full"
                                         style={{ width: `${Math.min(cnt * 15, 100)}%`, background: "linear-gradient(90deg,#6366f1,#a5b4fc)" }} />
                                  </div>
                                  <span className="text-xs w-6 text-right" style={{ color: "#a5b4fc" }}>{cnt}</span>
                                </div>
                              );
                            })}
                          </div>
                        </div>

                        {/* Recent evidence list */}
                        {evidence.evidence_list?.length > 0 && (
                          <div className="mt-4">
                            <p className="text-xs font-semibold mb-3" style={{ color: "var(--text-muted)" }}>最近证据</p>
                            <div className="space-y-2">
                              {evidence.evidence_list.slice(0, 8).map((ev: any, i: number) => {
                                const TYPE_COLORS: Record<string, string> = {
                                  DATA: "#10b981", QUOTE: "#6366f1", CLAIM: "#f59e0b", COMMIT: "#22d3ee",
                                };
                                return (
                                  <div key={i} className="flex gap-2 items-start px-3 py-2 rounded-xl"
                                       style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                                    <span className="text-xs px-1.5 py-0.5 rounded flex-shrink-0 font-bold"
                                          style={{ background: `${TYPE_COLORS[ev.ev_type]}15`, color: TYPE_COLORS[ev.ev_type], fontSize: "0.6rem" }}>
                                      {ev.ev_type}
                                    </span>
                                    <p className="text-xs flex-1" style={{ color: "var(--text-secondary)" }}>{ev.text?.slice(0, 80)}</p>
                                    <span className="text-xs flex-shrink-0" style={{ color: "var(--text-muted)" }}>第{ev.turn}轮</span>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </div>

                  {/* ── 超图 Rubric 节点覆盖图 ── */}
                  {evidence && evidence.hypergraph_nodes?.length > 0 && (
                    <div className="rounded-2xl p-6" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                      <p className="text-xs font-semibold mb-3" style={{ color: "var(--text-muted)" }}>超图知识节点覆盖</p>
                      <div className="grid grid-cols-3 gap-2">
                        {evidence.hypergraph_nodes.map((node: any) => {
                          const covered = node.status === "covered";
                          return (
                            <div key={node.rubric} className="rounded-xl p-2.5"
                                 style={{
                                   background: covered ? "rgba(16,185,129,0.06)" : "rgba(239,68,68,0.04)",
                                   border: `1px solid ${covered ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.15)"}`,
                                 }}>
                              <div className="flex items-center gap-1.5 mb-1">
                                <span className="text-xs" style={{ fontSize: "0.7rem" }}>{covered ? "✅" : "○"}</span>
                                <span className="text-xs font-medium truncate" style={{ color: covered ? "#6ee7b7" : "var(--text-muted)" }}>
                                  {node.concept}
                                </span>
                              </div>
                              {covered && (
                                <p className="text-xs" style={{ color: "#a5b4fc", fontSize: "0.65rem" }}>{node.evidence_count} 条证据</p>
                              )}
                              {node.related_concepts?.length > 0 && (
                                <p className="text-xs mt-0.5 truncate" style={{ color: "var(--text-muted)", fontSize: "0.62rem" }}>
                                  关联：{node.related_concepts.slice(0, 2).join("、")}
                                </p>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* ── AI 证据质量分析 ── */}
                  {evidence?.ai_analysis && (
                    <div className="rounded-2xl p-6" style={{ background: "rgba(99,102,241,0.05)", border: "1px solid rgba(99,102,241,0.2)" }}>
                      <div className="flex items-center justify-between mb-3">
                        <p className="text-xs font-semibold" style={{ color: "#a5b4fc" }}>AI 证据质量分析</p>
                        <div className="flex items-center gap-2">
                          <span className="text-lg font-bold" style={{ color: scoreColor(evidence.ai_analysis.quality_score) }}>
                            {evidence.ai_analysis.quality_score}/10
                          </span>
                          <span className="text-xs px-2 py-0.5 rounded-lg"
                                style={{
                                  background: evidence.ai_analysis.quality_label === "充分" ? "rgba(16,185,129,0.12)"
                                            : evidence.ai_analysis.quality_label === "一般" ? "rgba(245,158,11,0.12)"
                                            : "rgba(239,68,68,0.12)",
                                  color: evidence.ai_analysis.quality_label === "充分" ? "#10b981"
                                       : evidence.ai_analysis.quality_label === "一般" ? "#f59e0b"
                                       : "#ef4444",
                                }}>
                            {evidence.ai_analysis.quality_label}
                          </span>
                        </div>
                      </div>

                      {evidence.ai_analysis.summary && (
                        <p className="text-sm mb-3" style={{ color: "var(--text-primary)" }}>{evidence.ai_analysis.summary}</p>
                      )}

                      {evidence.ai_analysis.hypergraph_comparison && (
                        <p className="text-xs mb-3 px-3 py-2 rounded-lg" style={{ background: "rgba(99,102,241,0.08)", color: "#c4b5fd" }}>
                          超图对比：{evidence.ai_analysis.hypergraph_comparison}
                        </p>
                      )}

                      <div className="grid grid-cols-2 gap-3 mb-3">
                        {evidence.ai_analysis.strengths?.length > 0 && (
                          <div className="rounded-xl p-3" style={{ background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.15)" }}>
                            <p className="text-xs font-semibold mb-1.5" style={{ color: "#6ee7b7" }}>优势</p>
                            {evidence.ai_analysis.strengths.map((s: string, i: number) => (
                              <p key={i} className="text-xs mb-1" style={{ color: "var(--text-secondary)" }}>✅ {s}</p>
                            ))}
                          </div>
                        )}
                        {evidence.ai_analysis.weak_dimensions?.length > 0 && (
                          <div className="rounded-xl p-3" style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.15)" }}>
                            <p className="text-xs font-semibold mb-1.5" style={{ color: "#fca5a5" }}>待补强维度</p>
                            {evidence.ai_analysis.weak_dimensions.map((d: string, i: number) => (
                              <p key={i} className="text-xs mb-1" style={{ color: "var(--text-secondary)" }}>○ {d}</p>
                            ))}
                          </div>
                        )}
                      </div>

                      {evidence.ai_analysis.next_actions?.length > 0 && (
                        <div className="rounded-xl p-3" style={{ background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.2)" }}>
                          <p className="text-xs font-semibold mb-2" style={{ color: "#fcd34d" }}>下一步行动</p>
                          {evidence.ai_analysis.next_actions.map((a: string, i: number) => (
                            <p key={i} className="text-xs mb-1" style={{ color: "var(--text-secondary)" }}>{i + 1}. {a}</p>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* F5-adv: Learning Path tab */}
              {activeTab === "learning" && selected && (
                <div className="animate-fadeInUp">
                  <LearningPath projectId={selected.project_id} />
                </div>
              )}

              {/* F2-adv: Weekly Report tab */}
              {activeTab === "report" && selected && (
                <div className="animate-fadeInUp">
                  <WeeklyReport key={reportKey} projectId={selected.project_id} />
                </div>
              )}

              {/* F6-adv: Team tab */}
              {activeTab === "team" && selected && (
                <div className="animate-fadeInUp">
                  <TeamPanel
                    projectId={selected.project_id}
                    isOwner={true}
                  />
                </div>
              )}

            </div>
          </>
        )}
      </div>
    </div>
  );
}
