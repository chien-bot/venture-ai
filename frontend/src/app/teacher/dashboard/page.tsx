"use client";
import { useState, useEffect } from "react";
import { getDashboard, getHypergraphInsights } from "@/lib/api";
import { ClassSummary } from "@/lib/types";
import ScoreRadar from "@/components/ScoreRadar";
import { DashboardSkeleton } from "@/components/Skeleton";
import { useToast } from "@/components/Toast";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color: string }) {
  return (
    <div className="glass glass-hover rounded-2xl p-6 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-24 h-24 rounded-full pointer-events-none"
           style={{ background: `radial-gradient(circle, ${color}15 0%, transparent 70%)`, transform: "translate(30%, -30%)" }} />
      <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--text-muted)" }}>{label}</p>
      <p className="text-4xl font-bold mb-1" style={{ color }}>{value}</p>
      {sub && <p className="text-xs" style={{ color: "var(--text-muted)" }}>{sub}</p>}
    </div>
  );
}

export default function TeacherDashboard() {
  const [data, setData] = useState<ClassSummary | null>(null);
  const [hgInsights, setHgInsights] = useState<any>(null);
  const [loading, setLoading] = useState(true);
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

  return (
    <div className="h-full overflow-y-auto p-8" style={{ background: "var(--bg-base)" }}>
      <ToastContainer />
      <div className="max-w-6xl mx-auto animate-fadeInUp">

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold gradient-text">Mission Control</h1>
            <p className="text-sm mt-0.5" style={{ color: "var(--text-muted)" }}>班级创业项目实时监控面板</p>
          </div>
          <button
            onClick={handleExportExcel}
            className="btn-glow no-print flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm"
            style={{ background: "linear-gradient(135deg, #059669, #10b981)", borderColor: "rgba(16,185,129,0.5)" }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            导出 Excel
          </button>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <StatCard label="学生总数" value={data.total_students} sub="活跃用户" color="#6366f1" />
          <StatCard label="项目总数" value={data.total_projects} sub="创业项目" color="#22d3ee" />
          <StatCard label="高风险项目" value={data.high_risk_projects.length} sub="需要关注" color="#ef4444" />
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="glass rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="badge badge-blue">班级均值</span>
              <h3 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>能力雷达图</h3>
            </div>
            <ScoreRadar scores={data.avg_scores} />
          </div>

          <div className="glass rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="badge badge-red">共性错误</span>
              <h3 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>Top 5 问题</h3>
            </div>
            <div className="space-y-3">
              {data.top_mistakes.map((m) => (
                <div key={m.rank} className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5"
                       style={{
                         background: m.rank <= 2 ? "rgba(239,68,68,0.2)" : m.rank <= 4 ? "rgba(245,158,11,0.2)" : "rgba(99,102,241,0.15)",
                         color: m.rank <= 2 ? "#fca5a5" : m.rank <= 4 ? "#fcd34d" : "#a5b4fc",
                         border: `1px solid ${m.rank <= 2 ? "rgba(239,68,68,0.3)" : m.rank <= 4 ? "rgba(245,158,11,0.3)" : "rgba(99,102,241,0.25)"}`
                       }}>
                    {m.rank}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm" style={{ color: "var(--text-primary)" }}>{m.mistake}</p>
                    <div className="flex gap-2 mt-1 flex-wrap">
                      <span className="text-xs" style={{ color: "var(--text-muted)" }}>频率 {m.frequency}</span>
                      <span className="badge badge-purple" style={{ fontSize: "0.65rem" }}>{m.affected_rubric}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* High risk */}
        {data.high_risk_projects.length > 0 && (
          <div className="glass rounded-2xl p-6 mb-4"
               style={{ borderColor: "rgba(239,68,68,0.2)" }}>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-2 h-2 rounded-full" style={{ background: "#ef4444", boxShadow: "0 0 8px #ef4444" }} />
              <span className="badge badge-red">预警</span>
              <h3 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>高风险项目</h3>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {data.high_risk_projects.map((p) => (
                <div key={p.project_id} className="rounded-xl p-4"
                     style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)" }}>
                  <h4 className="text-sm font-semibold mb-1" style={{ color: "var(--text-primary)" }}>{p.name}</h4>
                  <p className="text-xs mb-3" style={{ color: "#fca5a5" }}>{p.risk}</p>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 rounded-full" style={{ background: "rgba(239,68,68,0.15)" }}>
                      <div className="h-1.5 rounded-full score-bar-fill"
                           style={{ width: `${(p.score / 10) * 100}%`, background: "#ef4444" }} />
                    </div>
                    <span className="text-xs font-bold" style={{ color: "#fca5a5" }}>{p.score}/10</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Suggestions */}
        <div className="glass rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <span className="badge badge-green">AI 建议</span>
            <h3 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>教学干预策略</h3>
          </div>
          <div className="space-y-2">
            {data.suggestions.map((s, i) => (
              <div key={i} className="flex items-start gap-3 px-4 py-3 rounded-xl"
                   style={{ background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.15)" }}>
                <span className="text-xs font-bold w-5 flex-shrink-0 mt-0.5" style={{ color: "#6ee7b7" }}>{i + 1}</span>
                <p className="text-sm" style={{ color: "var(--text-secondary)" }}>{s}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Hypergraph Insights Panel */}
        {hgInsights && (
          <>
            <div className="mt-6 mb-4 flex items-center gap-2">
              <div className="w-1.5 h-6 rounded-full" style={{ background: "linear-gradient(135deg, #6366f1, #a78bfa)" }} />
              <h2 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>超图案例库洞察</h2>
              <span className="badge badge-blue text-xs">{hgInsights.coverage?.total_projects || 0} 个竞赛案例</span>
            </div>

            <div className="grid grid-cols-3 gap-4 mb-4">
              <StatCard
                label="案例总数"
                value={hgInsights.coverage?.total_projects || 0}
                sub="竞赛项目"
                color="#6366f1"
              />
              <StatCard
                label="有护城河"
                value={`${hgInsights.coverage?.moat_pct || 0}%`}
                sub={`${hgInsights.coverage?.has_moat || 0} 个项目`}
                color="#10b981"
              />
              <StatCard
                label="有商业模式"
                value={`${hgInsights.coverage?.biz_pct || 0}%`}
                sub={`${hgInsights.coverage?.has_biz_model || 0} 个项目`}
                color="#22d3ee"
              />
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              {/* Tech Heatmap */}
              <div className="glass rounded-2xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <span className="badge badge-blue">技术热力图</span>
                  <h3 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>Top 技术分布</h3>
                </div>
                <div className="space-y-2">
                  {(hgInsights.tech_heatmap || []).slice(0, 10).map((t: any) => {
                    const maxCount = hgInsights.tech_heatmap?.[0]?.count || 1;
                    const pct = (t.count / maxCount) * 100;
                    return (
                      <div key={t.tech} className="flex items-center gap-3">
                        <span className="text-xs w-20 truncate" style={{ color: "var(--text-secondary)" }}>
                          {t.tech}
                        </span>
                        <div className="flex-1 h-4 rounded-full" style={{ background: "rgba(99,102,241,0.1)" }}>
                          <div
                            className="h-4 rounded-full transition-all"
                            style={{
                              width: `${pct}%`,
                              background: `linear-gradient(90deg, rgba(99,102,241,0.6), rgba(99,102,241,0.3))`,
                            }}
                          />
                        </div>
                        <span className="text-xs font-bold w-6 text-right" style={{ color: "#a5b4fc" }}>
                          {t.count}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Industry Distribution */}
              <div className="glass rounded-2xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <span className="badge badge-green">行业分布</span>
                  <h3 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>项目行业占比</h3>
                </div>
                <div className="space-y-2">
                  {(hgInsights.industry_distribution || []).map((ind: any) => {
                    const total = hgInsights.coverage?.total_projects || 1;
                    const pct = (ind.count / total) * 100;
                    return (
                      <div key={ind.industry} className="flex items-center gap-3">
                        <span className="text-xs w-20 truncate" style={{ color: "var(--text-secondary)" }}>
                          {ind.industry}
                        </span>
                        <div className="flex-1 h-4 rounded-full" style={{ background: "rgba(16,185,129,0.1)" }}>
                          <div
                            className="h-4 rounded-full transition-all"
                            style={{
                              width: `${pct}%`,
                              background: `linear-gradient(90deg, rgba(16,185,129,0.6), rgba(16,185,129,0.3))`,
                            }}
                          />
                        </div>
                        <span className="text-xs font-bold w-6 text-right" style={{ color: "#6ee7b7" }}>
                          {ind.count}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Risk Frequency */}
            {(hgInsights.risk_frequency || []).length > 0 && (
              <div className="glass rounded-2xl p-6 mb-4" style={{ borderColor: "rgba(239,68,68,0.15)" }}>
                <div className="flex items-center gap-2 mb-4">
                  <span className="badge badge-red">风险模式</span>
                  <h3 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>案例库常见风险</h3>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {(hgInsights.risk_frequency || []).map((r: any) => {
                    const sevColor = r.severity === "high" ? "#ef4444" : r.severity === "medium" ? "#f59e0b" : "#6366f1";
                    return (
                      <div key={r.risk} className="rounded-xl px-4 py-3"
                           style={{ background: `${sevColor}08`, border: `1px solid ${sevColor}20` }}>
                        <div className="flex items-center gap-2 mb-1">
                          <div className="w-2 h-2 rounded-full" style={{ background: sevColor }} />
                          <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                            {r.risk}
                          </span>
                        </div>
                        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                          影响 {r.affected_projects} 个项目 · {r.severity === "high" ? "高" : r.severity === "medium" ? "中" : "低"}风险
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Hypergraph-based Interventions */}
            {(hgInsights.interventions || []).length > 0 && (
              <div className="glass rounded-2xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <span className="badge badge-purple">超图洞察</span>
                  <h3 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>基于案例库的教学建议</h3>
                </div>
                <div className="space-y-2">
                  {hgInsights.interventions.map((s: string, i: number) => (
                    <div key={i} className="flex items-start gap-3 px-4 py-3 rounded-xl"
                         style={{ background: "rgba(167,139,250,0.06)", border: "1px solid rgba(167,139,250,0.15)" }}>
                      <span className="text-xs font-bold w-5 flex-shrink-0 mt-0.5" style={{ color: "#c4b5fd" }}>
                        {i + 1}
                      </span>
                      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>{s}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

      </div>
    </div>
  );
}
