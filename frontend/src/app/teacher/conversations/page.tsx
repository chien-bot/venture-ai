"use client";
import { useState, useEffect } from "react";
import { getTeacherProjects, getProjectConversations } from "@/lib/api";
import { Project } from "@/lib/types";

interface Message {
  role: "user" | "assistant";
  content: string;
  created_at?: string;
}

interface Session {
  session_id: string;
  agent_type: string;
  created_at: string;
  message_count: number;
  messages: Message[];
}

interface ConvData {
  project_id: string;
  project_name: string;
  owner_id: string;
  sessions: Session[];
  evidence_summary: {
    total: number;
    by_type: Record<string, number>;
    by_rubric: Record<string, number>;
    weak_claims: any[];
  } | null;
}

const EV_TYPE_COLORS: Record<string, string> = {
  DATA:   "#10b981",
  QUOTE:  "#6366f1",
  COMMIT: "#f59e0b",
  CLAIM:  "#ef4444",
};

const RUBRIC_LABELS: Record<string, string> = {
  R1: "痛点定义", R2: "用户证据", R3: "方案可行性",
  R4: "商业模式", R5: "市场竞争", R6: "财务逻辑",
  R7: "创新差异化", R8: "团队执行", R9: "表达材料",
};

export default function TeacherConversationsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [convData, setConvData] = useState<ConvData | null>(null);
  const [activeSession, setActiveSession] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [expandedSessions, setExpandedSessions] = useState<Set<string>>(new Set());

  useEffect(() => {
    getTeacherProjects()
      .then((r) => {
        setProjects(r.projects || []);
        if (r.projects?.length > 0) {
          setSelectedId(r.projects[0].project_id);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setLoading(true);
    setConvData(null);
    setActiveSession("");
    getProjectConversations(selectedId)
      .then((data) => {
        setConvData(data);
        if (data.sessions?.length > 0) {
          setActiveSession(data.sessions[0].session_id);
          setExpandedSessions(new Set([data.sessions[0].session_id]));
        }
      })
      .catch(() => setConvData(null))
      .finally(() => setLoading(false));
  }, [selectedId]);

  const toggleSession = (sid: string) => {
    setExpandedSessions((prev) => {
      const next = new Set(prev);
      if (next.has(sid)) next.delete(sid);
      else next.add(sid);
      return next;
    });
  };

  const activeSessionData = convData?.sessions.find((s) => s.session_id === activeSession);

  return (
    <div className="flex h-full" style={{ background: "var(--bg-base)" }}>

      {/* Left: project list */}
      <div className="w-64 flex-shrink-0 flex flex-col overflow-hidden"
           style={{ borderRight: "1px solid var(--border)", background: "rgba(8,13,26,0.8)" }}>
        <div className="px-4 py-3 flex-shrink-0"
             style={{ borderBottom: "1px solid var(--border)" }}>
          <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
            选择项目
          </p>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {projects.length === 0 ? (
            <p className="text-xs text-center py-8" style={{ color: "var(--text-muted)" }}>暂无项目</p>
          ) : projects.map((p) => (
            <button
              key={p.project_id}
              onClick={() => setSelectedId(p.project_id)}
              className="w-full text-left px-3 py-2.5 rounded-xl transition-all"
              style={{
                background: selectedId === p.project_id ? "rgba(99,102,241,0.12)" : "transparent",
                border: `1px solid ${selectedId === p.project_id ? "rgba(99,102,241,0.3)" : "transparent"}`,
              }}
            >
              <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{p.name}</p>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                {p.owner_id} · {p.industry || "未设置行业"}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Center: sessions + messages */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Header */}
        <div className="flex items-center gap-3 px-5 py-3 flex-shrink-0"
             style={{ borderBottom: "1px solid var(--border)", background: "rgba(8,13,26,0.9)" }}>
          <div className="w-8 h-8 rounded-xl flex items-center justify-center text-base flex-shrink-0"
               style={{ background: "rgba(16,185,129,0.12)", border: "1px solid rgba(16,185,129,0.25)" }}>
            💬
          </div>
          <div>
            <h1 className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
              {convData?.project_name || "选择项目查看对话"}
            </h1>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {convData ? `${convData.sessions.length} 个会话 · 学生 ${convData.owner_id}` : "教师查看学生对话记录"}
            </p>
          </div>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="text-3xl mb-3 opacity-40">⏳</div>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>加载中...</p>
            </div>
          </div>
        ) : !convData ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="text-4xl mb-3 opacity-30">💬</div>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>请从左侧选择项目</p>
            </div>
          </div>
        ) : convData.sessions.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="text-4xl mb-3 opacity-30">🗂</div>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>该项目暂无对话记录</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {/* Session list */}
            {convData.sessions.map((sess) => {
              const expanded = expandedSessions.has(sess.session_id);
              return (
                <div key={sess.session_id} className="rounded-2xl overflow-hidden"
                     style={{ border: "1px solid var(--border)", background: "rgba(255,255,255,0.02)" }}>
                  {/* Session header */}
                  <button
                    onClick={() => toggleSession(sess.session_id)}
                    className="w-full flex items-center gap-3 px-4 py-3 transition-all"
                    style={{
                      background: expanded ? "rgba(99,102,241,0.06)" : "transparent",
                      borderBottom: expanded ? "1px solid var(--border)" : "none",
                    }}
                  >
                    <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
                      {expanded ? "▼" : "▶"}
                    </span>
                    <div className="flex-1 text-left">
                      <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                        会话 #{sess.session_id.slice(-6)}
                      </span>
                      <span className="ml-3 text-xs" style={{ color: "var(--text-muted)" }}>
                        {sess.message_count} 条消息 · {sess.created_at?.slice(0, 10)} · {sess.agent_type}
                      </span>
                    </div>
                    <span className="badge badge-blue text-xs">{sess.message_count} msgs</span>
                  </button>

                  {/* Messages */}
                  {expanded && (
                    <div className="p-4 space-y-2 max-h-96 overflow-y-auto">
                      {sess.messages.map((msg, idx) => (
                        <div key={idx}
                             className={`flex gap-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                          {msg.role === "assistant" && (
                            <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs flex-shrink-0 mt-0.5"
                                 style={{ background: "rgba(99,102,241,0.2)", color: "#a5b4fc" }}>
                              AI
                            </div>
                          )}
                          <div className="max-w-[75%] px-3 py-2 rounded-xl text-sm"
                               style={{
                                 background: msg.role === "user"
                                   ? "linear-gradient(135deg, rgba(99,102,241,0.25), rgba(139,92,246,0.2))"
                                   : "rgba(255,255,255,0.04)",
                                 border: "1px solid rgba(255,255,255,0.06)",
                                 color: "var(--text-secondary)",
                                 whiteSpace: "pre-wrap",
                               }}>
                            {msg.content}
                          </div>
                          {msg.role === "user" && (
                            <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs flex-shrink-0 mt-0.5"
                                 style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)", color: "white" }}>
                              S
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Right: evidence summary */}
      {convData?.evidence_summary && (
        <div className="w-72 flex-shrink-0 flex flex-col overflow-hidden"
             style={{ borderLeft: "1px solid var(--border)", background: "rgba(8,13,26,0.6)" }}>
          <div className="px-4 py-3 flex-shrink-0"
               style={{ borderBottom: "1px solid var(--border)" }}>
            <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
              证据分析
            </p>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Total */}
            <div className="text-center py-3 rounded-xl"
                 style={{ background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.2)" }}>
              <p className="text-2xl font-bold gradient-text">{convData.evidence_summary.total}</p>
              <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>证据条目总数</p>
            </div>

            {/* By type */}
            <div>
              <p className="text-xs mb-2 font-medium" style={{ color: "var(--text-muted)" }}>证据类型分布</p>
              <div className="space-y-1.5">
                {Object.entries(convData.evidence_summary.by_type).map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between px-3 py-1.5 rounded-lg"
                       style={{ background: `${EV_TYPE_COLORS[type] || "#6366f1"}10`, border: `1px solid ${EV_TYPE_COLORS[type] || "#6366f1"}25` }}>
                    <span className="text-xs font-medium" style={{ color: EV_TYPE_COLORS[type] || "#6366f1" }}>{type}</span>
                    <span className="text-xs font-bold" style={{ color: "var(--text-primary)" }}>{count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* By rubric */}
            {Object.keys(convData.evidence_summary.by_rubric).length > 0 && (
              <div>
                <p className="text-xs mb-2 font-medium" style={{ color: "var(--text-muted)" }}>Rubric 覆盖</p>
                <div className="space-y-1.5">
                  {Object.entries(convData.evidence_summary.by_rubric).map(([rubric, count]) => {
                    const short = rubric.split("_")[0];
                    return (
                      <div key={rubric} className="flex items-center justify-between">
                        <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
                          {short} {RUBRIC_LABELS[short] || rubric}
                        </span>
                        <span className="badge badge-blue text-xs">{count}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Weak claims */}
            {convData.evidence_summary.weak_claims?.length > 0 && (
              <div>
                <p className="text-xs mb-2 font-medium" style={{ color: "#fcd34d" }}>
                  ⚠ 待补充证据的主张
                </p>
                <div className="space-y-1.5">
                  {convData.evidence_summary.weak_claims.slice(0, 5).map((claim: any, i: number) => (
                    <div key={i} className="px-3 py-2 rounded-lg text-xs"
                         style={{ background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.2)" }}>
                      <p className="mb-1" style={{ color: "#fcd34d" }}>第{claim.turn}轮</p>
                      <p style={{ color: "var(--text-secondary)" }}>{claim.text.slice(0, 60)}...</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
