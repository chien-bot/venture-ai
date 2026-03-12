"use client";
import { useState, useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { startDefense, sendDefenseMessage, listProjects } from "@/lib/api";
import { ChatMessage, Project } from "@/lib/types";
import ChatWindow from "@/components/ChatWindow";

const INVESTOR_STYLES = [
  { key: "aggressive", label: "犀利型", icon: "🔥", desc: "直接、毫不客气，专门戳破幻想" },
  { key: "analytical", label: "数据型", icon: "📊", desc: "极其重视数据和逻辑，追问指标" },
  { key: "strategic", label: "战略型", icon: "🎯", desc: "关注大格局、行业趋势、退出策略" },
];

function DefenseContent() {
  const searchParams = useSearchParams();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState(searchParams.get("project_id") || "");
  const [investorStyle, setInvestorStyle] = useState("aggressive");
  const [totalQuestions, setTotalQuestions] = useState(7);
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentRound, setCurrentRound] = useState(0);
  const [started, setStarted] = useState(false);
  const [report, setReport] = useState<any>(null);

  useEffect(() => {
    listProjects().then((r) => {
      const projs = r.projects || [];
      setProjects(projs);
      if (!selectedProjectId && projs.length > 0) {
        setSelectedProjectId(projs[0].project_id);
      }
    }).catch(() => {});
  }, []);

  const handleStart = async () => {
    if (!selectedProjectId) return;
    try {
      const res = await startDefense(selectedProjectId, investorStyle, totalQuestions);
      setSessionId(res.session_id);
      setMessages([{ role: "assistant", content: res.greeting }]);
      setCurrentRound(0);
      setStarted(true);
      setReport(null);
    } catch {
      setMessages([{ role: "assistant", content: "启动答辩失败，请检查后端服务。" }]);
    }
  };

  const handleSend = async (msg: string) => {
    if (report) return; // Defense is over
    const nextRound = currentRound + 1;
    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    setLoading(true);
    try {
      const res = await sendDefenseMessage(
        sessionId, selectedProjectId, msg,
        investorStyle, nextRound, totalQuestions,
      );
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
      setCurrentRound(nextRound);
      if (res.report) {
        setReport(res.report);
      }
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "网络错误，请重试。" }]);
    } finally {
      setLoading(false);
    }
  };

  const selectedProject = projects.find((p) => p.project_id === selectedProjectId);
  const styleInfo = INVESTOR_STYLES.find((s) => s.key === investorStyle) || INVESTOR_STYLES[0];

  // Setup screen
  if (!started) {
    return (
      <div className="flex items-center justify-center h-full" style={{ background: "var(--bg-base)" }}>
        <div className="w-full max-w-lg p-8 rounded-2xl" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)" }}>
          <div className="text-center mb-6">
            <div className="text-4xl mb-3">🎤</div>
            <h1 className="text-xl font-bold gradient-text mb-1">模拟投资人答辩</h1>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              AI 将扮演投资人，对你的项目进行模拟答辩
            </p>
          </div>

          {/* Project selection */}
          <div className="mb-5">
            <label className="text-xs font-medium mb-2 block" style={{ color: "var(--text-secondary)" }}>选择项目</label>
            <select value={selectedProjectId} onChange={(e) => setSelectedProjectId(e.target.value)}
              className="w-full text-sm px-3 py-2.5 rounded-xl outline-none"
              style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)", color: "var(--text-primary)" }}>
              <option value="">请选择项目</option>
              {projects.map((p) => (<option key={p.project_id} value={p.project_id}>{p.name}</option>))}
            </select>
          </div>

          {/* Investor style */}
          <div className="mb-5">
            <label className="text-xs font-medium mb-2 block" style={{ color: "var(--text-secondary)" }}>投资人风格</label>
            <div className="space-y-2">
              {INVESTOR_STYLES.map((style) => (
                <button key={style.key}
                  onClick={() => setInvestorStyle(style.key)}
                  className="w-full text-left px-4 py-3 rounded-xl transition-all flex items-center gap-3"
                  style={{
                    background: investorStyle === style.key ? "rgba(99,102,241,0.12)" : "rgba(255,255,255,0.02)",
                    border: `1px solid ${investorStyle === style.key ? "rgba(99,102,241,0.4)" : "var(--border)"}`,
                  }}>
                  <span className="text-xl">{style.icon}</span>
                  <div>
                    <div className="text-sm font-medium" style={{ color: investorStyle === style.key ? "#a5b4fc" : "var(--text-primary)" }}>
                      {style.label}
                    </div>
                    <div className="text-xs" style={{ color: "var(--text-muted)" }}>{style.desc}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Question count */}
          <div className="mb-6">
            <label className="text-xs font-medium mb-2 block" style={{ color: "var(--text-secondary)" }}>提问轮数</label>
            <div className="flex gap-2">
              {[5, 7, 10].map((n) => (
                <button key={n} onClick={() => setTotalQuestions(n)}
                  className="flex-1 text-sm py-2 rounded-xl transition-all"
                  style={{
                    background: totalQuestions === n ? "rgba(99,102,241,0.12)" : "rgba(255,255,255,0.02)",
                    border: `1px solid ${totalQuestions === n ? "rgba(99,102,241,0.4)" : "var(--border)"}`,
                    color: totalQuestions === n ? "#a5b4fc" : "var(--text-muted)",
                  }}>
                  {n} 轮
                </button>
              ))}
            </div>
          </div>

          <button onClick={handleStart} disabled={!selectedProjectId}
            className="w-full py-3 rounded-xl font-medium btn-glow disabled:opacity-30 disabled:cursor-not-allowed">
            开始答辩
          </button>
        </div>
      </div>
    );
  }

  // Defense in progress
  return (
    <div className="flex h-full" style={{ background: "var(--bg-base)" }}>
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="flex items-center px-4 py-2.5 gap-3 flex-shrink-0"
             style={{ borderBottom: "1px solid var(--border)", background: "rgba(8,13,26,0.9)" }}>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl"
               style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.25)" }}>
            <span className="text-sm">{styleInfo.icon}</span>
            <span className="text-sm font-semibold" style={{ color: "#fca5a5" }}>
              {styleInfo.label}投资人
            </span>
          </div>
          <span className="badge badge-amber">
            第 {currentRound}/{totalQuestions} 轮
          </span>
          {selectedProject && (
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              项目：{selectedProject.name}
            </span>
          )}
          {report && (
            <span className="badge badge-green ml-auto">答辩已结束</span>
          )}
          {!report && (
            <button onClick={() => { setStarted(false); setReport(null); setMessages([]); setCurrentRound(0); }}
              className="ml-auto text-xs px-3 py-1.5 rounded-lg transition-all"
              style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)", color: "var(--text-muted)" }}>
              退出答辩
            </button>
          )}
        </div>
        <ChatWindow messages={messages} onSend={handleSend} loading={loading} agentLabel="投资人" />
      </div>

      {/* Report sidebar */}
      <div className="w-80 flex flex-col flex-shrink-0 overflow-y-auto p-4"
           style={{ borderLeft: "1px solid var(--border)", background: "rgba(8,13,26,0.6)" }}>
        {report ? (
          <>
            <p className="text-xs font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>答辩评估报告</p>

            {/* Overall score */}
            <div className="text-center mb-5 py-4 rounded-xl" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)" }}>
              <div className="text-3xl font-bold gradient-text">{report.overall_score}</div>
              <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>总分 / 100</div>
            </div>

            {/* Dimension scores */}
            <div className="space-y-3 mb-5">
              {report.dimensions && Object.entries(report.dimensions).map(([key, dim]: [string, any]) => {
                const labels: Record<string, string> = {
                  pain_point: "痛点验证", solution: "解决方案", market: "市场分析",
                  business_model: "商业模式", team_execution: "团队执行", presentation: "表达能力",
                };
                const score = dim.score || 0;
                const color = score >= 7 ? "#6ee7b7" : score >= 5 ? "#fcd34d" : "#fca5a5";
                return (
                  <div key={key}>
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs" style={{ color: "var(--text-secondary)" }}>{labels[key] || key}</span>
                      <span className="text-xs font-bold" style={{ color }}>{score}/10</span>
                    </div>
                    <div className="h-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                      <div className="h-1.5 rounded-full transition-all" style={{ width: `${score * 10}%`, background: color }} />
                    </div>
                    {dim.comment && (
                      <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>{dim.comment}</p>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Strengths */}
            {report.strengths?.length > 0 && (
              <div className="mb-4">
                <p className="text-xs font-medium mb-2" style={{ color: "#6ee7b7" }}>优势</p>
                <div className="space-y-1">
                  {report.strengths.map((s: string, i: number) => (
                    <div key={i} className="text-xs px-3 py-2 rounded-lg"
                         style={{ background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.2)", color: "var(--text-secondary)" }}>
                      {s}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Weaknesses */}
            {report.weaknesses?.length > 0 && (
              <div className="mb-4">
                <p className="text-xs font-medium mb-2" style={{ color: "#fca5a5" }}>不足</p>
                <div className="space-y-1">
                  {report.weaknesses.map((w: string, i: number) => (
                    <div key={i} className="text-xs px-3 py-2 rounded-lg"
                         style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", color: "var(--text-secondary)" }}>
                      {w}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Advice */}
            {report.advice?.length > 0 && (
              <div className="mb-4">
                <p className="text-xs font-medium mb-2" style={{ color: "#a5b4fc" }}>改进建议</p>
                <div className="space-y-1">
                  {report.advice.map((a: string, i: number) => (
                    <div key={i} className="text-xs px-3 py-2 rounded-lg"
                         style={{ background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.2)", color: "var(--text-secondary)" }}>
                      {a}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <button onClick={() => { setStarted(false); setReport(null); setMessages([]); setCurrentRound(0); }}
              className="w-full text-xs py-2.5 rounded-xl btn-glow mt-2">
              重新答辩
            </button>
          </>
        ) : (
          <>
            <p className="text-xs font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>答辩进度</p>
            <div className="space-y-2 mb-5">
              {Array.from({ length: totalQuestions }, (_, i) => {
                const round = i + 1;
                const done = round <= currentRound;
                const active = round === currentRound + 1;
                return (
                  <div key={round} className="flex items-center gap-3 px-3 py-2 rounded-lg"
                       style={{
                         background: active ? "rgba(99,102,241,0.08)" : done ? "rgba(16,185,129,0.06)" : "transparent",
                         border: `1px solid ${active ? "rgba(99,102,241,0.3)" : done ? "rgba(16,185,129,0.2)" : "var(--border)"}`,
                       }}>
                    <div className="w-5 h-5 rounded-full flex items-center justify-center text-xs flex-shrink-0"
                         style={{
                           background: done ? "rgba(16,185,129,0.2)" : active ? "rgba(99,102,241,0.2)" : "rgba(255,255,255,0.05)",
                           color: done ? "#6ee7b7" : active ? "#a5b4fc" : "var(--text-muted)",
                         }}>
                      {done ? "✓" : round}
                    </div>
                    <span className="text-xs" style={{ color: done ? "#6ee7b7" : active ? "#a5b4fc" : "var(--text-muted)" }}>
                      {round <= 2 ? "痛点验证" : round <= 4 ? "竞争壁垒" : round <= 6 ? "商业模式" : "落地能力"}
                    </span>
                  </div>
                );
              })}
            </div>

            <div className="rounded-xl px-4 py-3 space-y-1" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)" }}>
              <p className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>答辩技巧</p>
              {[
                "用数据说话，不要空泛",
                "正面回答问题，不要回避",
                "承认不足比强行辩解好",
                "准备好竞品分析和差异化",
              ].map((t, i) => (
                <p key={t} className="text-xs" style={{ color: "var(--text-muted)" }}>
                  <span style={{ color: "#f59e0b" }}>{i + 1}.</span> {t}
                </p>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function DefensePage() {
  return (
    <Suspense fallback={<div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>加载中...</div>}>
      <DefenseContent />
    </Suspense>
  );
}
