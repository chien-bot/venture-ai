"use client";
import { useState, useEffect } from "react";
import { getMyProfile, refreshMyProfile } from "@/lib/api";
import ScoreRadar from "@/components/ScoreRadar";

const DIM_LABELS: Record<string, { label: string; icon: string }> = {
  empathy:   { label: "同理心", icon: "💜" },
  ideation:  { label: "创意力", icon: "💡" },
  business:  { label: "商业力", icon: "💰" },
  execution: { label: "执行力", icon: "🚀" },
  logic:     { label: "逻辑表达", icon: "🧠" },
};

const STAGE_MAP: Record<string, { label: string; color: string }> = {
  discovery: { label: "痛点发现", color: "#6366f1" },
  ideation:  { label: "方案策划", color: "#22d3ee" },
  modeling:  { label: "商业建模", color: "#a78bfa" },
  execution: { label: "资源杠杆", color: "#f59e0b" },
  pitching:  { label: "路演表达", color: "#10b981" },
};

function scoreColor(score: number) {
  if (score >= 7) return { color: "#6ee7b7", bg: "rgba(16,185,129,0.12)", bar: "#10b981" };
  if (score >= 5) return { color: "#fcd34d", bg: "rgba(245,158,11,0.12)", bar: "#f59e0b" };
  return { color: "#fca5a5", bg: "rgba(239,68,68,0.12)", bar: "#ef4444" };
}

export default function StudentProfilePage() {
  const [profileData, setProfileData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [expandedProject, setExpandedProject] = useState<string>("");

  useEffect(() => {
    getMyProfile()
      .then((data) => setProfileData(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      const data = await refreshMyProfile();
      setProfileData(data);
    } catch {
      // swallow; keep stale data
    } finally {
      setRefreshing(false);
    }
  }

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-muted)" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 36, marginBottom: 16, opacity: 0.5 }}>🔄</div>
          <p style={{ fontSize: 14 }}>加载个人画像中...</p>
        </div>
      </div>
    );
  }

  if (!profileData || profileData.message) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-muted)" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.4 }}>📊</div>
          <p style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>暂无个人画像</p>
          <p style={{ fontSize: 13 }}>{profileData?.message || "请先创建项目并与AI教练对话"}</p>
        </div>
      </div>
    );
  }

  const { user, projects, overall_profile } = profileData;

  return (
    <div style={{ padding: "28px 32px", maxWidth: 1100, margin: "0 auto", overflowY: "auto", height: "100%" }}>
      {/* Header */}
      <div style={{ marginBottom: 28, display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
            个人能力画像
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 6 }}>
            {user.display_name || user.username} {user.class_id ? `· ${user.class_id}` : ""} · 共 {projects.length} 个项目
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          style={{
            padding: "8px 14px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            background: refreshing ? "rgba(99,102,241,0.12)" : "rgba(255,255,255,0.04)",
            color: refreshing ? "#a5b4fc" : "var(--text-secondary)",
            fontSize: 12,
            fontWeight: 600,
            cursor: refreshing ? "wait" : "pointer",
            whiteSpace: "nowrap",
          }}
          title="基于最新对话与上传资料重新评估。每次重评会消耗 LLM tokens。"
        >
          {refreshing ? "🔄 重新评估中..." : "🔄 重新评估"}
        </button>
      </div>

      {/* Overall Profile */}
      {overall_profile && (
        <div style={{
          background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)",
          borderRadius: 16, padding: 24, marginBottom: 28,
        }}>
          <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", marginBottom: 20 }}>
            综合能力评估
          </p>
          <div style={{ display: "flex", gap: 32, alignItems: "flex-start", flexWrap: "wrap" }}>
            {/* Radar Chart */}
            <div style={{ flex: "0 0 200px" }}>
              <ScoreRadar scores={{ ...overall_profile, pitching: overall_profile.logic || overall_profile.pitching || 0 }} />
            </div>
            {/* Dimension Bars */}
            <div style={{ flex: 1, minWidth: 280 }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                {Object.entries(DIM_LABELS).map(([key, dim]) => {
                  const val = overall_profile[key] || 0;
                  const sc = scoreColor(val);
                  return (
                    <div key={key}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                        <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                          {dim.icon} {dim.label}
                        </span>
                        <span style={{ fontSize: 14, fontWeight: 700, color: sc.color }}>{val}/10</span>
                      </div>
                      <div style={{ height: 8, borderRadius: 4, background: "rgba(255,255,255,0.06)" }}>
                        <div style={{
                          height: 8, borderRadius: 4, width: `${val * 10}%`,
                          background: `linear-gradient(90deg, ${sc.bar}, ${sc.color})`,
                          transition: "width 0.6s ease",
                        }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Projects */}
      <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", marginBottom: 16 }}>
        各项目画像
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {projects.map((proj: any) => {
          const isExpanded = expandedProject === proj.project_id;
          const cap = proj.capability_profile;
          const stageInfo = STAGE_MAP[proj.stage] || STAGE_MAP.discovery;

          return (
            <div key={proj.project_id} style={{
              background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)",
              borderRadius: 14, overflow: "hidden", transition: "all 0.2s",
            }}>
              {/* Project Header */}
              <button
                onClick={() => setExpandedProject(isExpanded ? "" : proj.project_id)}
                style={{
                  width: "100%", padding: "16px 20px", background: "none", border: "none",
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  cursor: "pointer", color: "var(--text-primary)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <span style={{ fontSize: 16 }}>📋</span>
                  <div style={{ textAlign: "left" }}>
                    <p style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>{proj.project_name || "未命名项目"}</p>
                    <p style={{ fontSize: 11, color: "var(--text-muted)", margin: "4px 0 0" }}>
                      {proj.industry || "未分类"} · {proj.session_count} 次对话
                      {proj.profile_updated_at && (
                        <span style={{ marginLeft: 8, opacity: 0.7 }}>
                          · 评估于 {proj.profile_updated_at.replace("T", " ").slice(0, 16)}
                        </span>
                      )}
                    </p>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{
                    fontSize: 11, padding: "3px 10px", borderRadius: 8,
                    background: `${stageInfo.color}18`, color: stageInfo.color,
                    fontWeight: 600,
                  }}>{stageInfo.label}</span>
                  <span style={{ fontSize: 14, color: "var(--text-muted)", transition: "transform 0.2s", transform: isExpanded ? "rotate(180deg)" : "rotate(0)" }}>
                    ▼
                  </span>
                </div>
              </button>

              {/* Expanded Content */}
              {isExpanded && cap && (
                <div style={{ padding: "0 20px 20px", borderTop: "1px solid var(--border)" }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: 14, marginTop: 16 }}>
                    {Object.entries(DIM_LABELS).map(([key, dim]) => {
                      const dimData = cap[key];
                      if (!dimData) return null;
                      const val = dimData.score || 0;
                      const sc = scoreColor(val);
                      return (
                        <div key={key} style={{
                          padding: "12px 16px", borderRadius: 10,
                          background: sc.bg, border: `1px solid ${sc.bar}22`,
                        }}>
                          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                            <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                              {dim.icon} {dim.label}
                            </span>
                            <span style={{ fontSize: 15, fontWeight: 700, color: sc.color }}>{val}/10</span>
                          </div>
                          {dimData.evidence && (
                            <p style={{ fontSize: 12, color: "#10b981", margin: "4px 0", lineHeight: 1.5 }}>
                              <strong>证据：</strong>{dimData.evidence}
                            </p>
                          )}
                          {dimData.suggestion && (
                            <p style={{ fontSize: 12, color: "#f59e0b", margin: "4px 0", lineHeight: 1.5 }}>
                              <strong>建议：</strong>{dimData.suggestion}
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                  {cap.overall_comment && (
                    <div style={{
                      marginTop: 14, padding: "12px 16px", borderRadius: 10,
                      background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.2)",
                    }}>
                      <p style={{ fontSize: 12, color: "#a5b4fc", fontWeight: 600, marginBottom: 4 }}>综合评价</p>
                      <p style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>{cap.overall_comment}</p>
                    </div>
                  )}
                </div>
              )}

              {/* No profile yet */}
              {isExpanded && !cap && (
                <div style={{ padding: "20px", textAlign: "center", borderTop: "1px solid var(--border)" }}>
                  <p style={{ fontSize: 12, color: "var(--text-muted)" }}>暂无能力画像数据，请先与AI教练对话</p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
