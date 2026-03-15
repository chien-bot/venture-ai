"use client";
import { useState, useEffect } from "react";
import { getWeeklyReport } from "@/lib/api";
import { WeeklyReport as WeeklyReportType } from "@/lib/types";

const DIM_LABELS: Record<string, string> = {
  empathy: "痛点发现", ideation: "方案策划",
  business: "商业建模", execution: "资源杠杆", pitching: "路演表达",
};

interface Props {
  projectId: string;
}

export default function WeeklyReport({ projectId }: Props) {
  const [report, setReport] = useState<WeeklyReportType | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchReport = async () => {
    setLoading(true);
    try {
      const res = await getWeeklyReport(projectId);
      setReport(res);
      setLastUpdated(new Date());
    } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => {
    fetchReport();
  }, [projectId]);

  if (loading) return (
    <div className="flex items-center gap-2 py-8 justify-center">
      <div className="w-4 h-4 border-2 border-white/20 border-t-white/60 rounded-full animate-spin" />
      <span className="text-sm" style={{ color: "var(--text-muted)" }}>生成周报中...</span>
    </div>
  );
  if (!report) return null;

  return (
    <div className="glass-card p-4 rounded-xl space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>本周报告</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2 py-0.5 rounded-full"
                style={{ background: "rgba(99,102,241,0.15)", color: "#a5b4fc" }}>
            {report.week_start} ~ {report.week_end}
          </span>
          <button
            onClick={fetchReport}
            title="刷新周报"
            className="text-xs px-2 py-0.5 rounded-lg transition-all"
            style={{ background: "rgba(255,255,255,0.05)", border: "1px solid var(--border)", color: "var(--text-muted)" }}
          >
            ↻ 刷新
          </button>
        </div>
      </div>
      {lastUpdated && (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          最后更新：{lastUpdated.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}
        </p>
      )}

      {/* Stats */}
      <div className="flex gap-4">
        <div className="flex-1 p-3 rounded-lg text-center" style={{ background: "rgba(255,255,255,0.03)" }}>
          <p className="text-lg font-bold" style={{ color: "#6366f1" }}>{report.stats?.sessions ?? 0}</p>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>有效对话</p>
        </div>
        <div className="flex-1 p-3 rounded-lg text-center" style={{ background: "rgba(255,255,255,0.03)" }}>
          <p className="text-lg font-bold" style={{ color: "#22d3ee" }}>{report.stats?.messages ?? 0}</p>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>消息条数</p>
        </div>
      </div>

      {/* Highlights */}
      {(report.highlights?.length ?? 0) > 0 && (
        <div>
          <p className="text-xs font-medium mb-2" style={{ color: "var(--text-muted)" }}>亮点</p>
          <div className="space-y-1.5">
            {report.highlights.map((h, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-xs mt-0.5" style={{ color: "#10b981" }}>+</span>
                <span className="text-sm" style={{ color: "var(--text-secondary)" }}>{h}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Score changes */}
      {Object.keys(report.score_changes ?? {}).length > 0 && (
        <div>
          <p className="text-xs font-medium mb-2" style={{ color: "var(--text-muted)" }}>分数变化</p>
          <div className="space-y-1.5">
            {Object.entries(report.score_changes).map(([dim, change]) => (
              <div key={dim} className="flex items-center justify-between text-sm">
                <span style={{ color: "var(--text-secondary)" }}>{DIM_LABELS[dim] || dim}</span>
                <span style={{ color: change.delta > 0 ? "#10b981" : "#ef4444" }}>
                  {change.from} → {change.to} ({change.delta > 0 ? "+" : ""}{change.delta})
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action items */}
      {(report.action_items?.length ?? 0) > 0 && (
        <div>
          <p className="text-xs font-medium mb-2" style={{ color: "var(--text-muted)" }}>待办事项</p>
          <div className="space-y-1.5">
            {report.action_items.map((item, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-xs mt-0.5" style={{ color: "#f59e0b" }}>!</span>
                <span className="text-sm" style={{ color: "var(--text-secondary)" }}>{item}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
