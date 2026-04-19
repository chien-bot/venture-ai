"use client";
import { useState, useEffect } from "react";
import { getDashboard, getHypergraphInsights, getClassProfile } from "@/lib/api";
import { ClassSummary } from "@/lib/types";
import ScoreRadar from "@/components/ScoreRadar";
import { DashboardSkeleton } from "@/components/Skeleton";
import { useToast } from "@/components/Toast";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color: string }) {
  return (
    <div className="glass glass-hover rounded-xl p-4 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-16 h-16 rounded-full pointer-events-none"
           style={{ background: `radial-gradient(circle, ${color}18 0%, transparent 70%)`, transform: "translate(30%, -30%)" }} />
      <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>{label}</p>
      <p className="text-3xl font-bold mb-0.5" style={{ color }}>{value}</p>
      {sub && <p className="text-xs" style={{ color: "var(--text-muted)" }}>{sub}</p>}
    </div>
  );
}

type Tab = "class" | "hypergraph" | "profile";

export default function TeacherDashboard() {
  const [data, setData] = useState<ClassSummary | null>(null);
  const [hgInsights, setHgInsights] = useState<any>(null);
  const [classProfile, setClassProfile] = useState<any>(null);
  const [profileClassId, setProfileClassId] = useState<string>("");
  const [profileLoading, setProfileLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>("class");
  const { show, ToastContainer } = useToast();

  useEffect(() => {
    Promise.all([
      getDashboard().catch(() => null),
      getHypergraphInsights().catch(() => null),
    ]).then(([dashboard, insights]) => {
      if (dashboard) setData(dashboard);
      else show("加载数据失败，请刷新重试", "error");
      if (insights) setHgInsights(insights);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (activeTab !== "profile") return;
    setProfileLoading(true);
    getClassProfile(profileClassId)
      .then(setClassProfile)
      .catch(() => show("班级画像加载失败", "error"))
      .finally(() => setProfileLoading(false));
  }, [activeTab, profileClassId]);

  const handleExportExcel = async () => {
    try {
      const token = sessionStorage.getItem("token") || "";
      const res = await fetch(`${API_BASE}/api/teacher/export/excel`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "ventureai_class_report.xlsx";
      a.click();
      URL.revokeObjectURL(url);
      show("Excel 报告已下载", "success");
    } catch {
      show("导出失败，请重试", "error");
    }
  };

  if (loading) return <DashboardSkeleton />;

  if (!data) {
    return (
      <div className="flex items-center justify-center h-full" style={{ background: "var(--bg-base)" }}>
        <p style={{ color: "var(--text-muted)" }}>暂无数据</p>
      </div>
    );
  }

  const tabs: { key: Tab; label: string; badge?: string }[] = [
    { key: "class", label: "班级总览" },
    { key: "profile", label: "班级画像" },
    ...(hgInsights ? [{ key: "hypergraph" as Tab, label: "案例库洞察", badge: `${hgInsights.coverage?.total_projects || 0} 个案例` }] : []),
  ];

  return (
    <div className="h-full overflow-y-auto p-6" style={{ background: "var(--bg-base)" }}>
      <ToastContainer />
      <div className="max-w-5xl mx-auto animate-fadeInUp">

        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h1 className="text-xl font-bold gradient-text">Mission Control</h1>
            <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>班级创业项目监控面板</p>
          </div>
          <button
            onClick={handleExportExcel}
            className="btn-glow no-print flex items-center gap-2 px-4 py-2 rounded-xl text-xs"
            style={{ background: "linear-gradient(135deg, #059669, #10b981)", borderColor: "rgba(16,185,129,0.5)" }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            导出 Excel
          </button>
        </div>

        {/* Tabs */}
        {tabs.length > 1 && (
          <div className="flex gap-1 mb-5 p-1 rounded-xl w-fit"
               style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)" }}>
            {tabs.map((t) => (
              <button
                key={t.key}
                onClick={() => setActiveTab(t.key)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200"
                style={activeTab === t.key ? (
                  t.key === "hypergraph" ? {
                    background: "linear-gradient(135deg, rgba(99,102,241,0.3), rgba(99,102,241,0.15))",
                    color: "#a5b4fc",
                    border: "1px solid rgba(99,102,241,0.4)",
                  } : t.key === "profile" ? {
                    background: "linear-gradient(135deg, rgba(168,85,247,0.25), rgba(168,85,247,0.1))",
                    color: "#c4b5fd",
                    border: "1px solid rgba(168,85,247,0.4)",
                  } : {
                    background: "linear-gradient(135deg, rgba(34,211,238,0.25), rgba(34,211,238,0.1))",
                    color: "#67e8f9",
                    border: "1px solid rgba(34,211,238,0.35)",
                  }
                ) : { color: "var(--text-muted)" }}
              >
                {t.label}
                {t.badge && (
                  <span className="text-xs px-1.5 py-0.5 rounded-md"
                        style={{ background: "rgba(99,102,241,0.2)", color: "#a5b4fc", fontSize: "0.6rem" }}>
                    {t.badge}
                  </span>
                )}
              </button>
            ))}
          </div>
        )}

        {/* ── Tab: 班级总览 ── */}
        {activeTab === "class" && (
          <div className="space-y-4">

            {/* Stat cards */}
            <div className="grid grid-cols-3 gap-3">
              <StatCard label="学生总数" value={data.total_students} sub="活跃用户" color="#6366f1" />
              <StatCard label="项目总数" value={data.total_projects} sub="创业项目" color="#22d3ee" />
              <StatCard label="高风险项目" value={data.high_risk_projects.length} sub="需要关注" color="#ef4444" />
            </div>

            {/* Radar + Top Mistakes */}
            <div className="grid grid-cols-2 gap-4">
              <div className="glass rounded-2xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <span className="badge badge-blue">班级均值</span>
                  <h3 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>能力雷达图</h3>
                </div>
                <ScoreRadar scores={data.avg_scores} />
              </div>

              <div className="glass rounded-2xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <span className="badge badge-red">共性错误</span>
                  <h3 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>Top 5 问题</h3>
                </div>
                <div className="space-y-2.5">
                  {data.top_mistakes.map((m) => (
                    <div key={m.rank} className="flex items-center gap-3">
                      <div className="w-5 h-5 rounded-md flex items-center justify-center text-xs font-bold flex-shrink-0"
                           style={{
                             background: m.rank <= 2 ? "rgba(239,68,68,0.2)" : m.rank <= 4 ? "rgba(245,158,11,0.2)" : "rgba(99,102,241,0.15)",
                             color: m.rank <= 2 ? "#fca5a5" : m.rank <= 4 ? "#fcd34d" : "#a5b4fc",
                           }}>
                        {m.rank}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs" style={{ color: "var(--text-primary)" }}>{m.mistake}</p>
                        <div className="flex gap-2 mt-0.5">
                          <span className="text-xs" style={{ color: "var(--text-muted)" }}>{m.frequency}</span>
                          <span className="badge badge-purple" style={{ fontSize: "0.6rem" }}>{m.affected_rubric}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* High Risk + AI Suggestions — side by side */}
            <div className="grid grid-cols-2 gap-4">
              {/* High risk */}
              {data.high_risk_projects.length > 0 ? (
                <div className="glass rounded-2xl p-5" style={{ borderColor: "rgba(239,68,68,0.2)" }}>
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-1.5 h-1.5 rounded-full" style={{ background: "#ef4444", boxShadow: "0 0 6px #ef4444" }} />
                    <span className="badge badge-red">预警</span>
                    <h3 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>高风险项目</h3>
                  </div>
                  <div className="space-y-2">
                    {data.high_risk_projects.map((p) => (
                      <div key={p.project_id} className="flex items-center gap-3 rounded-xl px-3 py-2"
                           style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.15)" }}>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold truncate" style={{ color: "var(--text-primary)" }}>{p.name}</p>
                          <p className="text-xs truncate" style={{ color: "#fca5a5" }}>{p.risk}</p>
                        </div>
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          <div className="w-16 h-1 rounded-full" style={{ background: "rgba(239,68,68,0.15)" }}>
                            <div className="h-1 rounded-full" style={{ width: `${(p.score / 10) * 100}%`, background: "#ef4444" }} />
                          </div>
                          <span className="text-xs font-bold" style={{ color: "#fca5a5" }}>{p.score}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="glass rounded-2xl p-5 flex items-center justify-center"
                     style={{ borderColor: "rgba(16,185,129,0.2)" }}>
                  <p className="text-sm" style={{ color: "var(--text-muted)" }}>暂无高风险项目 ✓</p>
                </div>
              )}

              {/* AI Suggestions */}
              <div className="glass rounded-2xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <span className="badge badge-green">AI 建议</span>
                  <h3 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>教学干预策略</h3>
                </div>
                <div className="space-y-2">
                  {data.suggestions.map((s, i) => (
                    <div key={i} className="flex items-start gap-2 px-3 py-2 rounded-xl"
                         style={{ background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.12)" }}>
                      <span className="text-xs font-bold flex-shrink-0 mt-0.5" style={{ color: "#6ee7b7" }}>{i + 1}</span>
                      <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{s}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

          </div>
        )}

        {/* ── Tab: 案例库洞察 ── */}
        {activeTab === "hypergraph" && hgInsights && (
          <div className="space-y-4">

            {/* Coverage stat cards */}
            <div className="grid grid-cols-3 gap-3">
              <StatCard label="案例总数" value={hgInsights.coverage?.total_projects || 0} sub="竞赛项目" color="#6366f1" />
              <StatCard label="有护城河" value={`${hgInsights.coverage?.moat_pct || 0}%`}
                        sub={`${hgInsights.coverage?.has_moat || 0} 个项目`} color="#10b981" />
              <StatCard label="有商业模式" value={`${hgInsights.coverage?.biz_pct || 0}%`}
                        sub={`${hgInsights.coverage?.has_biz_model || 0} 个项目`} color="#22d3ee" />
            </div>

            {/* Tech Heatmap + Industry Distribution */}
            <div className="grid grid-cols-2 gap-4">
              <div className="glass rounded-2xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <span className="badge badge-blue">技术热力图</span>
                  <h3 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>Top 技术分布</h3>
                </div>
                <div className="space-y-1.5">
                  {(hgInsights.tech_heatmap || []).slice(0, 8).map((t: any) => {
                    const maxCount = hgInsights.tech_heatmap?.[0]?.count || 1;
                    const pct = (t.count / maxCount) * 100;
                    return (
                      <div key={t.tech} className="flex items-center gap-2">
                        <span className="text-xs w-20 truncate" style={{ color: "var(--text-secondary)" }}>{t.tech}</span>
                        <div className="flex-1 h-3 rounded-full" style={{ background: "rgba(99,102,241,0.1)" }}>
                          <div className="h-3 rounded-full transition-all"
                               style={{ width: `${pct}%`, background: "linear-gradient(90deg, rgba(99,102,241,0.6), rgba(99,102,241,0.3))" }} />
                        </div>
                        <span className="text-xs font-bold w-5 text-right" style={{ color: "#a5b4fc" }}>{t.count}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="glass rounded-2xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <span className="badge badge-green">行业分布</span>
                  <h3 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>项目行业占比</h3>
                </div>
                <div className="space-y-1.5">
                  {(hgInsights.industry_distribution || []).map((ind: any) => {
                    const total = hgInsights.coverage?.total_projects || 1;
                    const pct = (ind.count / total) * 100;
                    return (
                      <div key={ind.industry} className="flex items-center gap-2">
                        <span className="text-xs w-20 truncate" style={{ color: "var(--text-secondary)" }}>{ind.industry}</span>
                        <div className="flex-1 h-3 rounded-full" style={{ background: "rgba(16,185,129,0.1)" }}>
                          <div className="h-3 rounded-full transition-all"
                               style={{ width: `${pct}%`, background: "linear-gradient(90deg, rgba(16,185,129,0.6), rgba(16,185,129,0.3))" }} />
                        </div>
                        <span className="text-xs font-bold w-5 text-right" style={{ color: "#6ee7b7" }}>{ind.count}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Risk Frequency + Interventions */}
            {((hgInsights.risk_frequency || []).length > 0 || (hgInsights.interventions || []).length > 0) && (
              <div className="grid grid-cols-2 gap-4">
                {(hgInsights.risk_frequency || []).length > 0 && (
                  <div className="glass rounded-2xl p-5" style={{ borderColor: "rgba(239,68,68,0.15)" }}>
                    <div className="flex items-center gap-2 mb-3">
                      <span className="badge badge-red">风险模式</span>
                      <h3 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>案例库常见风险</h3>
                    </div>
                    <div className="space-y-2">
                      {(hgInsights.risk_frequency || []).map((r: any) => {
                        const sevColor = r.severity === "high" ? "#ef4444" : r.severity === "medium" ? "#f59e0b" : "#6366f1";
                        return (
                          <div key={r.risk} className="flex items-center gap-3 rounded-xl px-3 py-2"
                               style={{ background: `${sevColor}08`, border: `1px solid ${sevColor}20` }}>
                            <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: sevColor }} />
                            <span className="text-xs flex-1" style={{ color: "var(--text-primary)" }}>{r.risk}</span>
                            <span className="text-xs flex-shrink-0" style={{ color: "var(--text-muted)" }}>
                              {r.affected_projects} 个项目
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {(hgInsights.interventions || []).length > 0 && (
                  <div className="glass rounded-2xl p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="badge badge-purple">超图洞察</span>
                      <h3 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>教学建议</h3>
                    </div>
                    <div className="space-y-2">
                      {hgInsights.interventions.map((s: string, i: number) => (
                        <div key={i} className="flex items-start gap-2 px-3 py-2 rounded-xl"
                             style={{ background: "rgba(167,139,250,0.06)", border: "1px solid rgba(167,139,250,0.15)" }}>
                          <span className="text-xs font-bold flex-shrink-0 mt-0.5" style={{ color: "#c4b5fd" }}>{i + 1}</span>
                          <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{s}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

          </div>
        )}

        {/* ── Tab: 班级画像 ── */}
        {activeTab === "profile" && (
          <div className="space-y-4">
            {/* Class filter */}
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>筛选班级：</span>
              <button
                onClick={() => setProfileClassId("")}
                className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
                style={profileClassId === "" ? {
                  background: "rgba(168,85,247,0.2)", color: "#c4b5fd",
                  border: "1px solid rgba(168,85,247,0.4)",
                } : {
                  background: "rgba(255,255,255,0.04)", color: "var(--text-muted)",
                  border: "1px solid var(--border)",
                }}
              >全部</button>
              {(classProfile?.all_classes || []).map((c: string) => (
                <button
                  key={c}
                  onClick={() => setProfileClassId(c)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
                  style={profileClassId === c ? {
                    background: "rgba(168,85,247,0.2)", color: "#c4b5fd",
                    border: "1px solid rgba(168,85,247,0.4)",
                  } : {
                    background: "rgba(255,255,255,0.04)", color: "var(--text-muted)",
                    border: "1px solid var(--border)",
                  }}
                >{c}</button>
              ))}
            </div>

            {profileLoading && (
              <div className="text-center py-10" style={{ color: "var(--text-muted)" }}>加载中...</div>
            )}

            {!profileLoading && classProfile && (
              <>
                {/* Summary stats */}
                <div className="grid grid-cols-4 gap-3">
                  <StatCard label="学生总数" value={classProfile.student_count} sub={classProfile.class_id} color="#a855f7" />
                  <StatCard label="已评估" value={classProfile.scored_student_count} sub="有评分学生" color="#6366f1" />
                  <StatCard
                    label="班级最强"
                    value={classProfile.strongest_dim?.label || "--"}
                    sub={classProfile.strongest_dim ? `${classProfile.strongest_dim.score}/10` : ""}
                    color="#10b981"
                  />
                  <StatCard
                    label="班级最弱"
                    value={classProfile.weakest_dim?.label || "--"}
                    sub={classProfile.weakest_dim ? `${classProfile.weakest_dim.score}/10` : ""}
                    color="#ef4444"
                  />
                </div>

                {/* Class radar + distribution */}
                <div className="grid grid-cols-2 gap-4">
                  {/* Radar */}
                  <div className="glass rounded-xl p-5">
                    <p className="text-sm font-bold mb-3" style={{ color: "var(--text-primary)" }}>
                      班级五维能力雷达图
                    </p>
                    <div className="flex justify-center">
                      <ScoreRadar scores={classProfile.class_avg_scores} />
                    </div>
                    <div className="mt-4 space-y-2">
                      {Object.entries(classProfile.dim_labels || {}).map(([k, label]: any) => {
                        const v = classProfile.class_avg_scores?.[k] || 0;
                        const color = v >= 7 ? "#10b981" : v >= 5 ? "#f59e0b" : "#ef4444";
                        return (
                          <div key={k}>
                            <div className="flex justify-between text-xs mb-1">
                              <span style={{ color: "var(--text-secondary)" }}>{label}</span>
                              <span className="font-bold" style={{ color }}>{v.toFixed(1)}/10</span>
                            </div>
                            <div style={{ height: 6, borderRadius: 3, background: "rgba(255,255,255,0.06)" }}>
                              <div style={{
                                height: 6, borderRadius: 3, width: `${v * 10}%`,
                                background: color, transition: "width 0.6s ease",
                              }} />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Distribution */}
                  <div className="glass rounded-xl p-5">
                    <p className="text-sm font-bold mb-3" style={{ color: "var(--text-primary)" }}>
                      学生能力分布
                    </p>
                    {[
                      { key: "excellent", label: "优秀 (≥8分)", color: "#10b981", bg: "rgba(16,185,129,0.12)" },
                      { key: "good", label: "良好 (6-8分)", color: "#22d3ee", bg: "rgba(34,211,238,0.12)" },
                      { key: "pass", label: "合格 (4-6分)", color: "#f59e0b", bg: "rgba(245,158,11,0.12)" },
                      { key: "weak", label: "待提升 (<4分)", color: "#ef4444", bg: "rgba(239,68,68,0.12)" },
                    ].map(({ key, label, color, bg }) => {
                      const count = classProfile.distribution?.[key] || 0;
                      const total = classProfile.scored_student_count || 1;
                      const pct = Math.round((count / total) * 100);
                      return (
                        <div key={key} className="mb-3 p-3 rounded-lg" style={{ background: bg, border: `1px solid ${color}22` }}>
                          <div className="flex justify-between items-center mb-2">
                            <span className="text-xs font-semibold" style={{ color }}>{label}</span>
                            <span className="text-sm font-bold" style={{ color }}>{count} 人 ({pct}%)</span>
                          </div>
                          <div style={{ height: 6, borderRadius: 3, background: "rgba(255,255,255,0.06)" }}>
                            <div style={{ height: 6, borderRadius: 3, width: `${pct}%`, background: color }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Student list */}
                <div className="glass rounded-xl p-5">
                  <p className="text-sm font-bold mb-3" style={{ color: "var(--text-primary)" }}>
                    学生能力排行（按综合分降序）
                  </p>
                  {(classProfile.students || []).length === 0 ? (
                    <p className="text-xs text-center py-6" style={{ color: "var(--text-muted)" }}>暂无有评分的学生</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr style={{ borderBottom: "1px solid var(--border)" }}>
                            <th className="text-left py-2 px-2" style={{ color: "var(--text-muted)" }}>排名</th>
                            <th className="text-left py-2 px-2" style={{ color: "var(--text-muted)" }}>学生</th>
                            <th className="text-left py-2 px-2" style={{ color: "var(--text-muted)" }}>班级</th>
                            <th className="text-center py-2 px-2" style={{ color: "var(--text-muted)" }}>项目</th>
                            {Object.entries(classProfile.dim_labels || {}).map(([k, label]: any) => (
                              <th key={k} className="text-center py-2 px-2" style={{ color: "var(--text-muted)" }}>{label}</th>
                            ))}
                            <th className="text-center py-2 px-2" style={{ color: "var(--text-muted)" }}>综合</th>
                          </tr>
                        </thead>
                        <tbody>
                          {classProfile.students.map((s: any, i: number) => (
                            <tr key={s.user_id} style={{ borderBottom: "1px solid var(--border)" }}>
                              <td className="py-2 px-2">
                                <span className="font-bold" style={{ color: i < 3 ? "#c4b5fd" : "var(--text-muted)" }}>
                                  {i + 1}
                                </span>
                              </td>
                              <td className="py-2 px-2 font-semibold" style={{ color: "var(--text-primary)" }}>
                                {s.display_name}
                              </td>
                              <td className="py-2 px-2" style={{ color: "var(--text-muted)" }}>{s.class_id || "--"}</td>
                              <td className="text-center py-2 px-2" style={{ color: "var(--text-muted)" }}>{s.project_count}</td>
                              {Object.keys(classProfile.dim_labels || {}).map((k) => {
                                const v = s.scores?.[k] || 0;
                                const color = v >= 7 ? "#10b981" : v >= 5 ? "#f59e0b" : v > 0 ? "#ef4444" : "var(--text-muted)";
                                return <td key={k} className="text-center py-2 px-2 font-semibold" style={{ color }}>{v || "--"}</td>;
                              })}
                              <td className="text-center py-2 px-2 font-bold" style={{
                                color: s.overall >= 7 ? "#10b981" : s.overall >= 5 ? "#f59e0b" : "#ef4444"
                              }}>{s.overall}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
