"use client";
import { useState, useEffect } from "react";
import { getKnowledgeCoverage } from "@/lib/api";

interface KnowledgeCoverage {
  total_concepts: number;
  covered_count: number;
  not_covered_count: number;
  coverage_rate: number;
  covered_concepts: string[];
  not_covered_concepts: string[];
  top_concepts: Array<{ concept: string; count: number; student_count: number; project_count: number }>;
  project_coverage: Array<{ project_id: string; covered_concepts: string[]; coverage_rate: number }>;
}

export default function KnowledgeCoveragePage() {
  const [data, setData] = useState<KnowledgeCoverage | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getKnowledgeCoverage()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center h-full" style={{ background: "var(--bg-base)" }}>
        <div className="text-center">
          <div className="text-3xl mb-3 opacity-40">🧠</div>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>分析知识覆盖情况...</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex-1 flex items-center justify-center h-full" style={{ background: "var(--bg-base)" }}>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>加载失败，请确认后端正在运行</p>
      </div>
    );
  }

  const coverageColor = data.coverage_rate >= 70 ? "#10b981" : data.coverage_rate >= 40 ? "#f59e0b" : "#ef4444";

  return (
    <div className="h-full overflow-y-auto px-6 py-6" style={{ background: "var(--bg-base)" }}>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-xl font-bold gradient-text mb-1">知识覆盖汇总</h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          统计全班学生通过 AI 辅导员学习到的创业概念覆盖情况
        </p>
      </div>

      {/* Overview cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: "概念总数", value: data.total_concepts, color: "#6366f1" },
          { label: "已覆盖概念", value: data.covered_count, color: "#10b981" },
          { label: "未覆盖概念", value: data.not_covered_count, color: "#ef4444" },
          { label: "覆盖率", value: `${data.coverage_rate}%`, color: coverageColor },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-2xl p-4 text-center"
               style={{ background: `${color}0d`, border: `1px solid ${color}25` }}>
            <p className="text-2xl font-bold" style={{ color }}>{value}</p>
            <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>{label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Top concepts */}
        <div className="rounded-2xl p-5" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
          <h2 className="text-sm font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
            最常讲解的概念 (Top 15)
          </h2>
          {data.top_concepts.length === 0 ? (
            <p className="text-xs text-center py-8" style={{ color: "var(--text-muted)" }}>
              暂无数据，等待学生与 AI 辅导员对话后自动统计
            </p>
          ) : (
            <div className="space-y-2">
              {data.top_concepts.map((item, i) => (
                <div key={item.concept} className="flex items-center gap-3">
                  <span className="text-xs font-bold w-5 text-right flex-shrink-0"
                        style={{ color: "var(--text-muted)" }}>{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="text-xs font-medium truncate" style={{ color: "var(--text-primary)" }}>
                        {item.concept}
                      </span>
                      <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                          {item.student_count} 人
                        </span>
                        <span className="text-xs font-bold" style={{ color: "#a5b4fc" }}>
                          {item.count} 次
                        </span>
                      </div>
                    </div>
                    <div className="h-1 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                      <div className="h-1 rounded-full"
                           style={{ width: `${Math.min(item.count / (data.top_concepts[0]?.count || 1) * 100, 100)}%`,
                                    background: "linear-gradient(90deg, #6366f1, #a78bfa)" }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Covered / Not covered */}
        <div className="space-y-4">
          <div className="rounded-2xl p-5" style={{ background: "rgba(16,185,129,0.05)", border: "1px solid rgba(16,185,129,0.2)" }}>
            <h2 className="text-sm font-semibold mb-3" style={{ color: "#10b981" }}>
              已覆盖概念 ({data.covered_concepts.length})
            </h2>
            <div className="flex flex-wrap gap-1.5">
              {data.covered_concepts.map((c) => (
                <span key={c} className="text-xs px-2 py-1 rounded-lg"
                      style={{ background: "rgba(16,185,129,0.12)", color: "#6ee7b7", border: "1px solid rgba(16,185,129,0.2)" }}>
                  {c}
                </span>
              ))}
              {data.covered_concepts.length === 0 && (
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>暂无已覆盖概念</p>
              )}
            </div>
          </div>

          <div className="rounded-2xl p-5" style={{ background: "rgba(239,68,68,0.05)", border: "1px solid rgba(239,68,68,0.2)" }}>
            <h2 className="text-sm font-semibold mb-3" style={{ color: "#ef4444" }}>
              待覆盖概念 ({data.not_covered_concepts.length})
            </h2>
            <div className="flex flex-wrap gap-1.5">
              {data.not_covered_concepts.map((c) => (
                <span key={c} className="text-xs px-2 py-1 rounded-lg"
                      style={{ background: "rgba(239,68,68,0.08)", color: "#fca5a5", border: "1px solid rgba(239,68,68,0.2)" }}>
                  {c}
                </span>
              ))}
            </div>
            {data.not_covered_concepts.length > 0 && (
              <p className="text-xs mt-3" style={{ color: "var(--text-muted)" }}>
                建议：在课堂或学生对话中主动引导涉及上述概念
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Project coverage breakdown */}
      {data.project_coverage.length > 0 && (
        <div className="mt-6 rounded-2xl p-5" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
          <h2 className="text-sm font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
            各项目知识覆盖明细
          </h2>
          <div className="space-y-3">
            {data.project_coverage
              .sort((a, b) => b.coverage_rate - a.coverage_rate)
              .map((proj) => (
              <div key={proj.project_id} className="rounded-xl p-3"
                   style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
                    项目 {proj.project_id.slice(-8)}
                  </span>
                  <span className="text-xs font-bold"
                        style={{ color: proj.coverage_rate >= 50 ? "#6ee7b7" : "#fcd34d" }}>
                    {proj.coverage_rate}%
                  </span>
                </div>
                <div className="h-1.5 rounded-full mb-2" style={{ background: "rgba(255,255,255,0.06)" }}>
                  <div className="h-1.5 rounded-full"
                       style={{ width: `${proj.coverage_rate}%`,
                                background: proj.coverage_rate >= 50 ? "linear-gradient(90deg, #10b981, #34d399)" : "linear-gradient(90deg, #f59e0b, #fbbf24)" }} />
                </div>
                <div className="flex flex-wrap gap-1">
                  {proj.covered_concepts.map((c) => (
                    <span key={c} className="text-xs px-1.5 py-0.5 rounded"
                          style={{ background: "rgba(99,102,241,0.1)", color: "#a5b4fc" }}>
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
