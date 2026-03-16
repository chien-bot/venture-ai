"use client";
import { useState, useEffect } from "react";
import { getAllWeeklyReports } from "@/lib/api";
import { WeeklyReport } from "@/lib/types";

const DIM_LABELS: Record<string, string> = {
  empathy: "痛点发现", ideation: "方案策划",
  business: "商业建模", execution: "资源杠杆", pitching: "路演表达",
};

export default function TeacherReportsPage() {
  const [reports, setReports] = useState<WeeklyReport[]>([]);
  const [weekRange, setWeekRange] = useState({ start: "", end: "" });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async (weekStart?: string) => {
    setLoading(true);
    try {
      const res = await getAllWeeklyReports(weekStart);
      setReports(res.reports || []);
      setWeekRange({ start: res.week_start || "", end: res.week_end || "" });
    } catch { /* ignore */ }
    setLoading(false);
  };

  const totalSessions = reports.reduce((sum, r) => sum + (r.stats?.sessions || 0), 0);
  const totalMessages = reports.reduce((sum, r) => sum + (r.stats?.messages || 0), 0);
  const activeProjects = reports.filter(r => (r.stats?.sessions || 0) > 0).length;

  return (
    <div className="h-full p-6 overflow-y-auto" style={{ background: "var(--bg-base)" }}>
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold gradient-text">周报汇总</h1>
          <span className="text-xs px-3 py-1 rounded-full"
                style={{ background: "rgba(16,185,129,0.15)", color: "#6ee7b7" }}>
            {weekRange.start} ~ {weekRange.end}
          </span>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "项目总数", value: reports.length, color: "#6366f1" },
            { label: "活跃项目", value: activeProjects, color: "#10b981" },
            { label: "对话总数", value: totalSessions, color: "#22d3ee" },
            { label: "消息总数", value: totalMessages, color: "#f59e0b" },
          ].map(card => (
            <div key={card.label} className="glass-card p-4 rounded-xl text-center">
              <p className="text-2xl font-bold" style={{ color: card.color }}>{card.value}</p>
              <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>{card.label}</p>
            </div>
          ))}
        </div>

        {loading ? (
          <div className="text-sm text-center py-8" style={{ color: "var(--text-muted)" }}>加载中...</div>
        ) : reports.length === 0 ? (
          <div className="glass-card p-8 rounded-xl text-center">
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>本周暂无报告数据</p>
          </div>
        ) : (
          <div className="space-y-4">
            {reports.map((report, idx) => (
              <div key={report.project_id || idx} className="glass-card p-5 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                    {report.project_name || report.project_id}
                  </h3>
                  <div className="flex gap-3">
                    <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {report.stats?.sessions ?? 0} 次对话
                    </span>
                    <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {report.stats?.messages ?? 0} 条消息
                    </span>
                  </div>
                </div>

                {/* Highlights */}
                {report.highlights.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {report.highlights.map((h, i) => (
                      <span key={i} className="text-xs px-2 py-1 rounded-full"
                            style={{ background: "rgba(99,102,241,0.1)", color: "#a5b4fc" }}>
                        {h}
                      </span>
                    ))}
                  </div>
                )}

                {/* Score changes */}
                {Object.keys(report.score_changes).length > 0 && (
                  <div className="flex gap-3 flex-wrap">
                    {Object.entries(report.score_changes).map(([dim, change]) => (
                      <div key={dim} className="flex items-center gap-1 text-xs">
                        <span style={{ color: "var(--text-muted)" }}>{DIM_LABELS[dim] || dim}:</span>
                        <span style={{ color: change.delta > 0 ? "#10b981" : "#ef4444" }}>
                          {change.delta > 0 ? "+" : ""}{change.delta}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Action items */}
                {report.action_items.length > 0 && (
                  <div className="space-y-1">
                    {report.action_items.map((item, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <span className="text-xs mt-0.5" style={{ color: "#f59e0b" }}>!</span>
                        <span className="text-xs" style={{ color: "var(--text-secondary)" }}>{item}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
