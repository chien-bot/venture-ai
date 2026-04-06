"use client";
import { useState, useEffect } from "react";
import { getTeacherProjects, getProjectConversations, createAnnotation, getProjectAnnotations, createIntervention, getInterventions, deleteIntervention } from "@/lib/api";
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

interface Annotation {
  id: number;
  session_id: string;
  message_idx: number;
  action: string;
  note_text: string;
  created_at: string;
}

interface Intervention {
  intervention_id: string;
  trigger_keyword: string;
  instruction: string;
  priority: number;
  active: number;
  created_at: string;
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

const ACTION_STYLE: Record<string, { icon: string; color: string; bg: string }> = {
  like:    { icon: "👍", color: "#6ee7b7", bg: "rgba(16,185,129,0.12)" },
  dislike: { icon: "👎", color: "#fca5a5", bg: "rgba(239,68,68,0.12)" },
  note:    { icon: "📝", color: "#a5b4fc", bg: "rgba(99,102,241,0.12)" },
};

export default function TeacherConversationsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [convData, setConvData] = useState<ConvData | null>(null);
  const [loading, setLoading] = useState(false);
  const [expandedSessions, setExpandedSessions] = useState<Set<string>>(new Set());

  // Annotations
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [noteInput, setNoteInput] = useState<{ sessionId: string; msgIdx: number } | null>(null);
  const [noteText, setNoteText] = useState("");

  // Interventions
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [newTrigger, setNewTrigger] = useState("");
  const [newInstruction, setNewInstruction] = useState("");
  const [showInterventionForm, setShowInterventionForm] = useState(false);

  useEffect(() => {
    getTeacherProjects()
      .then((r) => {
        setProjects(r.projects || []);
        if (r.projects?.length > 0) setSelectedId(r.projects[0].project_id);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setLoading(true);
    setConvData(null);
    setAnnotations([]);
    setInterventions([]);
    Promise.all([
      getProjectConversations(selectedId),
      getProjectAnnotations(selectedId).catch(() => ({ annotations: [] })),
      getInterventions(selectedId).catch(() => ({ interventions: [] })),
    ]).then(([conv, ann, intv]) => {
      setConvData(conv);
      setAnnotations(ann.annotations || []);
      setInterventions(intv.interventions || []);
      if (conv.sessions?.length > 0) {
        setExpandedSessions(new Set([conv.sessions[0].session_id]));
      }
    }).catch(() => setConvData(null))
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

  const handleAnnotate = async (sessionId: string, msgIdx: number, action: string) => {
    try {
      await createAnnotation(selectedId, sessionId, msgIdx, action);
      const res = await getProjectAnnotations(selectedId);
      setAnnotations(res.annotations || []);
    } catch {}
  };

  const handleAddNote = async () => {
    if (!noteInput || !noteText.trim()) return;
    try {
      await createAnnotation(selectedId, noteInput.sessionId, noteInput.msgIdx, "note", noteText.trim());
      const res = await getProjectAnnotations(selectedId);
      setAnnotations(res.annotations || []);
      setNoteInput(null);
      setNoteText("");
    } catch {}
  };

  const handleAddIntervention = async () => {
    if (!newTrigger.trim() || !newInstruction.trim()) return;
    try {
      await createIntervention(selectedId, newTrigger.trim(), newInstruction.trim());
      const res = await getInterventions(selectedId);
      setInterventions(res.interventions || []);
      setNewTrigger("");
      setNewInstruction("");
      setShowInterventionForm(false);
    } catch {}
  };

  const handleDeleteIntervention = async (id: string) => {
    try {
      await deleteIntervention(id);
      setInterventions((prev) => prev.filter((i) => i.intervention_id !== id));
    } catch {}
  };

  const getAnnotationsForMsg = (sessionId: string, msgIdx: number) =>
    annotations.filter((a) => a.session_id === sessionId && a.message_idx === msgIdx);

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
                {p.industry || "未设置行业"}
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
          <div className="flex-1">
            <h1 className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
              {convData?.project_name || "选择项目查看对话"}
            </h1>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {convData ? `${convData.sessions.length} 个会话` : "教师查看学生对话记录"}
            </p>
          </div>
          {annotations.length > 0 && (
            <span className="text-xs px-2 py-1 rounded-lg"
                  style={{ background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.2)", color: "#a5b4fc" }}>
              {annotations.length} 条标注
            </span>
          )}
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>加载中...</p>
          </div>
        ) : !convData ? (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>请从左侧选择项目</p>
          </div>
        ) : convData.sessions.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>该项目暂无对话记录</p>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
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
                  </button>

                  {/* Messages with annotation buttons */}
                  {expanded && (
                    <div className="p-4 space-y-2 max-h-[500px] overflow-y-auto">
                      {sess.messages.map((msg, idx) => {
                        const msgAnnotations = getAnnotationsForMsg(sess.session_id, idx);
                        return (
                          <div key={idx} className="group relative">
                            <div className={`flex gap-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                              {msg.role === "assistant" && (
                                <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs flex-shrink-0 mt-0.5"
                                     style={{ background: "rgba(99,102,241,0.2)", color: "#a5b4fc" }}>
                                  AI
                                </div>
                              )}
                              <div className="max-w-[75%] relative">
                                <div className="px-3 py-2 rounded-xl text-sm"
                                     style={{
                                       background: msg.role === "user"
                                         ? "linear-gradient(135deg, rgba(99,102,241,0.25), rgba(139,92,246,0.2))"
                                         : "rgba(255,255,255,0.04)",
                                       border: msgAnnotations.length > 0
                                         ? "1px solid rgba(99,102,241,0.4)"
                                         : "1px solid rgba(255,255,255,0.06)",
                                       color: "var(--text-secondary)",
                                       whiteSpace: "pre-wrap",
                                     }}>
                                  {msg.content}
                                </div>

                                {/* Annotation action buttons — show on hover, bottom of bubble */}
                                <div className="flex gap-1 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                  <button onClick={() => handleAnnotate(sess.session_id, idx, "like")}
                                          className="h-5 px-1.5 rounded-md flex items-center justify-center text-xs transition-all"
                                          style={{ background: "rgba(16,185,129,0.1)", color: "#6ee7b7" }}
                                          title="标记为好">
                                    👍
                                  </button>
                                  <button onClick={() => handleAnnotate(sess.session_id, idx, "dislike")}
                                          className="h-5 px-1.5 rounded-md flex items-center justify-center text-xs transition-all"
                                          style={{ background: "rgba(239,68,68,0.1)", color: "#fca5a5" }}
                                          title="标记问题">
                                    👎
                                  </button>
                                  <button onClick={() => { setNoteInput({ sessionId: sess.session_id, msgIdx: idx }); setNoteText(""); }}
                                          className="h-5 px-1.5 rounded-md flex items-center justify-center text-xs transition-all"
                                          style={{ background: "rgba(99,102,241,0.1)", color: "#a5b4fc" }}
                                          title="添加批注">
                                    📝 批注
                                  </button>
                                </div>

                                {/* Existing annotations on this message */}
                                {msgAnnotations.length > 0 && (
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {msgAnnotations.map((a, ai) => {
                                      const s = ACTION_STYLE[a.action] || ACTION_STYLE.note;
                                      return (
                                        <span key={ai} className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-xs"
                                              style={{ background: s.bg, color: s.color }}>
                                          <span>{s.icon}</span>
                                          {a.note_text && <span>{a.note_text.slice(0, 30)}{a.note_text.length > 30 ? "..." : ""}</span>}
                                        </span>
                                      );
                                    })}
                                  </div>
                                )}

                                {/* Note input form */}
                                {noteInput?.sessionId === sess.session_id && noteInput?.msgIdx === idx && (
                                  <div className="mt-2 flex gap-2">
                                    <input
                                      value={noteText}
                                      onChange={(e) => setNoteText(e.target.value)}
                                      placeholder="输入批注..."
                                      autoFocus
                                      className="flex-1 px-2 py-1.5 rounded-lg text-xs outline-none"
                                      style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(99,102,241,0.3)", color: "var(--text-primary)" }}
                                      onKeyDown={(e) => { if (e.key === "Enter") handleAddNote(); if (e.key === "Escape") setNoteInput(null); }}
                                    />
                                    <button onClick={handleAddNote}
                                            className="px-2 py-1.5 rounded-lg text-xs"
                                            style={{ background: "rgba(99,102,241,0.2)", color: "#a5b4fc" }}>
                                      保存
                                    </button>
                                    <button onClick={() => setNoteInput(null)}
                                            className="px-2 py-1.5 rounded-lg text-xs"
                                            style={{ color: "var(--text-muted)" }}>
                                      取消
                                    </button>
                                  </div>
                                )}
                              </div>
                              {msg.role === "user" && (
                                <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs flex-shrink-0 mt-0.5"
                                     style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)", color: "white" }}>
                                  S
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Right sidebar: evidence + interventions */}
      <div className="w-72 flex-shrink-0 flex flex-col overflow-hidden"
           style={{ borderLeft: "1px solid var(--border)", background: "rgba(8,13,26,0.6)" }}>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">

          {/* Intervention rules */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                教师干预规则
              </p>
              <button onClick={() => setShowInterventionForm(!showInterventionForm)}
                      className="text-xs px-2 py-0.5 rounded-md transition-all"
                      style={{ background: "rgba(99,102,241,0.1)", color: "#a5b4fc", border: "1px solid rgba(99,102,241,0.2)" }}>
                {showInterventionForm ? "取消" : "+ 新增"}
              </button>
            </div>
            <p className="text-xs mb-3" style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>
              当学生消息中出现触发词时，AI 教练将自动注入你的指导意见
            </p>

            {showInterventionForm && (
              <div className="space-y-2 mb-3 p-3 rounded-xl"
                   style={{ background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.2)" }}>
                <input
                  value={newTrigger}
                  onChange={(e) => setNewTrigger(e.target.value)}
                  placeholder="触发关键词（如：商业模式）"
                  className="w-full px-2.5 py-1.5 rounded-lg text-xs outline-none"
                  style={{ background: "rgba(255,255,255,0.05)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                />
                <textarea
                  value={newInstruction}
                  onChange={(e) => setNewInstruction(e.target.value)}
                  placeholder="注入的指导意见（如：引导学生关注收入来源多元化）"
                  rows={2}
                  className="w-full px-2.5 py-1.5 rounded-lg text-xs outline-none resize-none"
                  style={{ background: "rgba(255,255,255,0.05)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                />
                <button onClick={handleAddIntervention}
                        disabled={!newTrigger.trim() || !newInstruction.trim()}
                        className="w-full py-1.5 rounded-lg text-xs btn-glow disabled:opacity-40">
                  保存干预规则
                </button>
              </div>
            )}

            {interventions.length === 0 && !showInterventionForm && (
              <p className="text-xs text-center py-3" style={{ color: "var(--text-muted)" }}>暂无干预规则</p>
            )}
            <div className="space-y-1.5">
              {interventions.map((intv) => (
                <div key={intv.intervention_id} className="group px-3 py-2 rounded-xl relative"
                     style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="text-xs px-1.5 py-0.5 rounded-md font-medium"
                          style={{ background: "rgba(245,158,11,0.15)", color: "#fcd34d" }}>
                      {intv.trigger_keyword}
                    </span>
                  </div>
                  <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
                    {intv.instruction.slice(0, 60)}{intv.instruction.length > 60 ? "..." : ""}
                  </p>
                  <button
                    onClick={() => handleDeleteIntervention(intv.intervention_id)}
                    className="absolute top-1.5 right-1.5 w-5 h-5 flex items-center justify-center rounded text-xs opacity-0 group-hover:opacity-100 transition-opacity"
                    style={{ color: "#fca5a5", background: "rgba(239,68,68,0.1)" }}
                    title="删除规则">
                    &times;
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Divider */}
          <div style={{ borderTop: "1px solid var(--border)" }} />

          {/* Evidence summary */}
          {convData?.evidence_summary && (
            <>
              <div className="flex items-center gap-2 mb-1">
                <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                  证据分析
                </p>
              </div>
              <div className="text-center py-3 rounded-xl"
                   style={{ background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.2)" }}>
                <p className="text-2xl font-bold gradient-text">{convData.evidence_summary.total}</p>
                <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>证据条目总数</p>
              </div>

              {/* By type */}
              <div>
                <p className="text-xs mb-2 font-medium" style={{ color: "var(--text-muted)" }}>证据类型</p>
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
                    待补充证据
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
            </>
          )}
        </div>
      </div>
    </div>
  );
}
