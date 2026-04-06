"use client";
import { useState, useEffect, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { startChat, sendMessage, sendMessageStream, listProjects, createProject, submitRating, getLatestSession, uploadFile, getMySessions, getChatHistory, deleteSession, getIntakeSchema, submitIntake } from "@/lib/api";
import { ChatMessage, Scores, Project } from "@/lib/types";
import ChatWindow from "@/components/ChatWindow";
import ScoreRadar from "@/components/ScoreRadar";
import RubricRadar from "@/components/RubricRadar";
import LearningPath from "@/components/LearningPath";

const STAGE_MAP: Record<string, { label: string; color: string }> = {
  discovery: { label: "痛点发现", color: "#6366f1" },
  ideation:  { label: "方案策划", color: "#22d3ee" },
  modeling:  { label: "商业建模", color: "#a78bfa" },
  execution: { label: "资源杠杆", color: "#f59e0b" },
  pitching:  { label: "路演表达", color: "#10b981" },
};

const SCORE_LABELS: Record<string, string> = {
  empathy: "痛点发现", ideation: "方案策划",
  business: "商业建模", execution: "资源杠杆", pitching: "路演表达",
};

const INTENT_META: Record<string, { label: string; icon: string; badgeClass: string }> = {
  coach:       { label: "项目教练",  icon: "🎯", badgeClass: "badge-blue" },
  tutor:       { label: "概念辅导",  icon: "📚", badgeClass: "badge-purple" },
  competition: { label: "竞赛评分",  icon: "🏆", badgeClass: "badge-amber" },
  grader:      { label: "批改评估",  icon: "📝", badgeClass: "badge-red" },
  hybrid:      { label: "混合模式",  icon: "⚡", badgeClass: "badge-green" },
};

const RUBRIC_NAMES: Record<string, string> = {
  R1: "痛点定义", R2: "用户证据", R3: "方案可行性",
  R4: "商业模式", R5: "市场竞争", R6: "财务逻辑",
  R7: "创新差异化", R8: "团队执行", R9: "表达材料",
  R10: "合规与社会责任", R11: "增长与规模化",
};

const RUBRIC_MAX = 5;

function scoreGradient(v: number) {
  if (v >= 4) return "linear-gradient(90deg, #10b981, #34d399)";
  if (v >= 3) return "linear-gradient(90deg, #f59e0b, #fbbf24)";
  return "linear-gradient(90deg, #ef4444, #f87171)";
}

function scoreTextColor(v: number) {
  if (v >= 4) return "#6ee7b7";
  if (v >= 3) return "#fcd34d";
  return "#fca5a5";
}

export default function StudentChatPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pendingQuery = useRef<string | null>(searchParams.get("q"));

  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [scores, setScores] = useState<Scores | null>(null);
  const [stage, setStage] = useState("discovery");
  const [diagnosis, setDiagnosis] = useState<string[]>([]);
  const [rubricScores, setRubricScores] = useState<Record<string, number> | null>(null);
  const [intent, setIntent] = useState<string>("coach");
  const [selectedAgentType, setSelectedAgentType] = useState<string>("auto");
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [ratingValue, setRatingValue] = useState(0);
  const [ratingComment, setRatingComment] = useState("");
  const [ratingSubmitted, setRatingSubmitted] = useState(false);
  const [knowledgeRecs, setKnowledgeRecs] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const [rubricFull, setRubricFull] = useState<Record<string, {score: number; evidence: string; suggestion: string}> | null>(null);
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectIndustry, setNewProjectIndustry] = useState("");
  const [newProjectDesc, setNewProjectDesc] = useState("");
  const [creatingProject, setCreatingProject] = useState(false);
  // Track if we've already auto-created a project for this session
  const autoCreatedRef = useRef(false);
  // Prevent concurrent/duplicate initChat calls
  const initLockRef = useRef(false);
  // Chat history sidebar
  const [historySessions, setHistorySessions] = useState<any[]>([]);
  const [historyCollapsed, setHistoryCollapsed] = useState(false);
  const [activeSessionProject, setActiveSessionProject] = useState<{name: string; industry?: string} | null>(null);
  // Intake form (前置采集层)
  const [showIntakeForm, setShowIntakeForm] = useState(false);
  const [intakeSchema, setIntakeSchema] = useState<any[]>([]);
  const [intakeData, setIntakeData] = useState<Record<string, string>>({});
  const [intakeSubmitting, setIntakeSubmitting] = useState(false);
  const [intakeGaps, setIntakeGaps] = useState<any[]>([]);

  const handleFileUpload = async (file: File) => {
    if (!file || !selectedProjectId) return;
    setUploading(true);
    try {
      const res = await uploadFile(file, selectedProjectId, sessionId);
      setUploadedFiles(prev => [...prev, res.filename]);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: `已上传文件「${res.filename}」(${res.file_type})，提取了 ${res.extracted_text_preview?.length || 0} 字文本内容。后续对话中 AI 将参考此文件。`,
      }]);
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "文件上传失败，请重试。" }]);
    }
    setUploading(false);
  };

  const exportChat = () => {
    const text = messages
      .map((m) => `[${m.role === "user" ? "我" : "AI"}]\n${m.content}`)
      .join("\n\n---\n\n");
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ventureai_chat_${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const initChat = async (projectId = selectedProjectId, agentType = selectedAgentType): Promise<void> => {
    if (initLockRef.current) return;
    initLockRef.current = true;
    try {
      const res = await startChat(agentType, projectId);
      setSessionId(res.session_id);
      setMessages([{ role: "assistant", content: res.greeting }]);
      setScores(null); setDiagnosis([]); setStage("discovery");
      setRubricScores(null); setRubricFull(null); setIntent("coach");
      refreshHistory();
      // Show intake form only once per project (tracked via localStorage)
      if (projectId) {
        const doneKey = `intake_done_${projectId}`;
        if (!localStorage.getItem(doneKey)) {
          try {
            const schema = await getIntakeSchema();
            if (schema.groups?.length > 0) {
              setIntakeSchema(schema.groups);
              setIntakeData({});
              setIntakeGaps([]);
              setShowIntakeForm(true);
            }
          } catch { /* intake schema fetch failed, skip form */ }
        }
      }
    } catch {
      setMessages([{ role: "assistant", content: "连接失败，请检查后端服务是否已启动。" }]);
    } finally {
      initLockRef.current = false;
    }
  };

  const handleIntakeSubmit = async () => {
    if (!sessionId) return;
    setIntakeSubmitting(true);
    try {
      const res = await submitIntake(sessionId, selectedProjectId, intakeData);
      if (res.student_summary) {
        setMessages([
          { role: "assistant", content: res.student_summary },
        ]);
      }
      setIntakeGaps(res.gaps || []);
      setShowIntakeForm(false);
      if (selectedProjectId) localStorage.setItem(`intake_done_${selectedProjectId}`, "1");
    } catch {
      setShowIntakeForm(false);
    }
    setIntakeSubmitting(false);
  };

  const handleIntakeSkip = () => {
    setShowIntakeForm(false);
    setIntakeData({});
    if (selectedProjectId) localStorage.setItem(`intake_done_${selectedProjectId}`, "1");
  };

  const restoreOrInit = async (pid: string) => {
    if (pid) {
      try {
        const res = await getLatestSession(pid);
        // Only restore if it's a coach/auto session, not a defense session
        if (res.exists && res.messages?.length > 0 && res.agent_type !== "defense") {
          setSessionId(res.session_id);
          setMessages(res.messages.map((m: any) => ({ role: m.role, content: m.content })));
          if (res.scores) setScores(res.scores);
          if (res.stage) setStage(res.stage);
          if (res.diagnosis) setDiagnosis(res.diagnosis);
          setRatingSubmitted(false); setRatingValue(0);
          return;
        }
      } catch {}
    }
    await initChat(pid);
  };

  useEffect(() => {
    refreshHistory();
  }, []);

  // Re-initialize chat when ?mode= changes in URL (but skip on initial load)
  const initialModeRef = useRef<string | null>(null);
  const initDoneRef = useRef(false);
  useEffect(() => {
    const urlMode = searchParams.get("mode");
    // Only re-init if mode actually changed (not on initial load)
    if (initDoneRef.current && initialModeRef.current !== null && initialModeRef.current !== urlMode) {
      setSelectedAgentType(urlMode || "auto");
      initChat(selectedProjectId, urlMode || "auto");
    }
    initialModeRef.current = urlMode;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams.get("mode")]);

  useEffect(() => {
    // Read ?mode= from URL and set agent type
    const urlMode = searchParams.get("mode");
    if (urlMode) setSelectedAgentType(urlMode);

    listProjects().then((r) => {
      const projs = r.projects || [];
      setProjects(projs);
      const urlPid = searchParams.get("project_id");
      const firstPid = urlPid || (projs.length > 0 ? projs[0].project_id : "");
      if (firstPid) {
        setSelectedProjectId(firstPid);
        if (!urlPid) router.replace(`/student/chat?project_id=${firstPid}${urlMode ? `&mode=${urlMode}` : ""}`);
        restoreOrInit(firstPid).then(() => {
          initDoneRef.current = true;
          if (pendingQuery.current) {
            const q = pendingQuery.current;
            pendingQuery.current = null;
            setTimeout(() => handleSend(q), 400);
          }
        });
      } else {
        initChat("").then(() => {
          initDoneRef.current = true;
          if (pendingQuery.current) {
            const q = pendingQuery.current;
            pendingQuery.current = null;
            setTimeout(() => handleSend(q), 400);
          }
        });
      }
    }).catch(() => { initChat(""); initDoneRef.current = true; });
  }, []);

  const handleProjectChange = async (pid: string) => {
    setSelectedProjectId(pid);
    router.replace(`/student/chat?project_id=${pid}`);
    restoreOrInit(pid);
  };

  const handleNewSession = async () => {
    await initChat(selectedProjectId);
    await refreshHistory();
  };

  const refreshHistory = async () => {
    try {
      const res = await getMySessions();
      setHistorySessions(res.sessions || []);
    } catch {}
  };

  const handleDeleteSession = async (e: React.MouseEvent, sid: string) => {
    e.stopPropagation();
    if (!confirm("确定要删除这条对话吗？")) return;
    try {
      await deleteSession(sid);
      if (sid === sessionId) await handleNewSession();
      else await refreshHistory();
    } catch (err: any) {
      alert("删除失败：" + (err?.message || "未知错误"));
    }
  };

  const handleLoadSession = async (session: any) => {
    try {
      const [res, projRes] = await Promise.all([
        getChatHistory(session.session_id),
        listProjects(),
      ]);
      const freshProjects = projRes.projects || [];
      setProjects(freshProjects);
      setSessionId(session.session_id);
      setMessages((res.messages || []).map((m: any) => ({ role: m.role, content: m.content })));
      if (session.project_id) setSelectedProjectId(session.project_id);
      setActiveSessionProject(session.project_name ? { name: session.project_name } : null);
      // Restore scores and rubric from project
      setScores(res.scores || null);
      setDiagnosis(res.diagnosis || []);
      setStage(res.stage || "discovery");
      setRubricFull(res.rubric_full || null);
      // If rubric_full exists, set intent to grader; otherwise use agent_type
      const agentType = res.agent_type || "coach";
      if (res.rubric_full && Object.keys(res.rubric_full).length > 0) {
        setIntent("grader");
      } else {
        setIntent(agentType);
      }
    } catch {}
  };

  const handleSend = async (msg: string) => {
    const currentAgentType = searchParams.get("mode") || selectedAgentType || "auto";
    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    setLoading(true);
    // Add empty assistant message that we'll stream into
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);
    try {
      await sendMessageStream(
        sessionId,
        selectedProjectId,
        msg,
        currentAgentType,
        // onToken: append text chunk to the last assistant message
        (token) => {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.role === "assistant") {
              const newContent = (last.content + token)
                .replace(/<!--\s*(?:SCORES|RUBRIC_FULL|RUBRIC|CAPABILITY_PROFILE)\s*:[\s\S]*?-->/gi, '')
                .replace(/<!--\s*(?:SCORES|RUBRIC_FULL|RUBRIC|CAPABILITY_PROFILE)\s*:[\s\S]*/gi, '');
              updated[updated.length - 1] = { ...last, content: newContent };
            }
            return updated;
          });
        },
        // onMeta: intent info arrives before tokens
        (meta) => {
          if (meta.intent) setIntent(meta.intent);
        },
        // onDone: final scores/stage/diagnosis/fix_tasks
        (done) => {
          if (done.scores) setScores(done.scores);
          if (done.stage) setStage(done.stage);
          if (done.diagnosis) setDiagnosis(done.diagnosis);
          if (done.rubric_scores) setRubricScores(done.rubric_scores);
          if (done.rubric_full) setRubricFull(done.rubric_full);
          // Attach fix_tasks to the last assistant message
          if (done.fix_tasks?.length) {
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last && last.role === "assistant") {
                updated[updated.length - 1] = { ...last, fix_tasks: done.fix_tasks };
              }
              return updated;
            });
          }
        },
      );
    } catch {
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last && last.role === "assistant" && !last.content) {
          updated[updated.length - 1] = { ...last, content: "抱歉，出现了网络错误，请检查连接后重试。" };
        } else {
          updated.push({ role: "assistant", content: "抱歉，出现了网络错误，请检查连接后重试。" });
        }
        return updated;
      });
    } finally {
      setLoading(false);
      refreshHistory();
      // After first AI reply with no project selected, try to auto-infer project
      if (!selectedProjectId) {
        setMessages((prev) => {
          // Trigger auto-infer with latest messages snapshot
          autoInferAndCreateProject(prev);
          return prev;
        });
      }
    }
  };

  const handleSubmitRating = async () => {
    if (!ratingValue || !sessionId) return;
    try {
      await submitRating(sessionId, selectedProjectId, ratingValue, ratingComment);
      setRatingSubmitted(true);
    } catch {}
  };

  const handleKnowledgeRec = (query: string) => {
    handleSend(query);
    setKnowledgeRecs([]);
  };

  // Create a new project and switch to it
  const handleCreateProject = async (name: string, industry: string, desc: string) => {
    if (!name.trim()) return;
    setCreatingProject(true);
    try {
      const proj = await createProject(name.trim(), industry.trim(), desc.trim());
      const refreshed = await listProjects();
      setProjects(refreshed.projects || []);
      setSelectedProjectId(proj.project_id);
      setShowNewProjectModal(false);
      setNewProjectName(""); setNewProjectIndustry(""); setNewProjectDesc("");
      await initChat(proj.project_id);
    } catch {
      // silently fail — user can retry
    }
    setCreatingProject(false);
  };

  // AI auto-infer: extract project name + industry from first 2-3 messages
  const autoInferAndCreateProject = async (msgs: { role: string; content: string }[]) => {
    if (autoCreatedRef.current || selectedProjectId) return;
    const userMsgs = msgs.filter((m) => m.role === "user").slice(0, 3);
    if (userMsgs.length < 1) return;
    autoCreatedRef.current = true; // prevent double-trigger

    const combined = userMsgs.map((m) => m.content).join(" ");
    // Simple heuristic extraction — backend will also do real extraction
    // Send a lightweight request to backend to parse project info
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/projects/auto-infer`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${sessionStorage.getItem("token") || ""}`,
        },
        body: JSON.stringify({ text: combined }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.name) {
          // Auto-create the project silently
          const proj = await createProject(data.name, data.industry || "", data.description || "");
          const refreshed = await listProjects();
          setProjects(refreshed.projects || []);
          setSelectedProjectId(proj.project_id);
          // Bind the current session to the new project
          if (sessionId) {
            await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/chat/bind-session`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${sessionStorage.getItem("token") || ""}`,
              },
              body: JSON.stringify({ session_id: sessionId, project_id: proj.project_id }),
            });
          }
          // Show a notice in chat
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: `🎉 已为你自动创建项目「${data.name}」（行业：${data.industry || "待定"}）。你可以在「我的项目」中查看和管理。` },
          ]);
        }
      }
    } catch {
      // auto-infer failed silently, user can create manually
      autoCreatedRef.current = false;
    }
  };

  const selectedProject = projects.find((p) => p.project_id === selectedProjectId) || activeSessionProject;
  const currentMeta = INTENT_META[intent] ?? INTENT_META.coach;
  const stageKeys = Object.keys(STAGE_MAP);
  const stageIdx = stageKeys.indexOf(stage);

  return (
    <div className="flex h-full overflow-hidden" style={{ background: "var(--bg-base)" }}>

      {/* ── History Sidebar ── */}
      <div className={`flex flex-col flex-shrink-0 overflow-hidden transition-all duration-200 ${historyCollapsed ? "w-0" : "w-56"}`}
           style={{ borderRight: historyCollapsed ? "none" : "1px solid var(--border)", background: "rgba(8,13,26,0.85)" }}>
        {!historyCollapsed && (
          <>
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2.5 flex-shrink-0"
                 style={{ borderBottom: "1px solid var(--border)" }}>
              <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                对话历史
              </p>
              <div className="flex items-center gap-1">
                <button onClick={handleNewSession} title="新建对话"
                        className="w-6 h-6 flex items-center justify-center rounded-md text-xs transition-all"
                        style={{ color: "var(--text-muted)", background: "rgba(255,255,255,0.04)" }}
                        onMouseEnter={e => { (e.target as HTMLElement).style.background = "rgba(99,102,241,0.2)"; (e.target as HTMLElement).style.color = "#a5b4fc"; }}
                        onMouseLeave={e => { (e.target as HTMLElement).style.background = "rgba(255,255,255,0.04)"; (e.target as HTMLElement).style.color = "var(--text-muted)"; }}>
                  +
                </button>
                <button onClick={() => setHistoryCollapsed(true)} title="收起"
                        className="w-6 h-6 flex items-center justify-center rounded-md text-xs transition-all"
                        style={{ color: "var(--text-muted)", background: "rgba(255,255,255,0.04)" }}
                        onMouseEnter={e => { (e.target as HTMLElement).style.background = "rgba(255,255,255,0.08)"; }}
                        onMouseLeave={e => { (e.target as HTMLElement).style.background = "rgba(255,255,255,0.04)"; }}>
                  &lsaquo;
                </button>
              </div>
            </div>
            {/* Session list */}
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {historySessions.length === 0 && (
                <p className="text-xs text-center py-6" style={{ color: "var(--text-muted)" }}>暂无历史对话</p>
              )}
              {historySessions.map((s) => {
                const isActive = s.session_id === sessionId;
                const agentMeta = INTENT_META[s.agent_type] || INTENT_META.coach;
                const timeStr = s.created_at ? new Date(s.created_at).toLocaleDateString("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "";
                return (
                  <div key={s.session_id}
                       onClick={() => handleLoadSession(s)}
                       className="group rounded-lg px-2.5 py-2 cursor-pointer transition-all duration-150 relative"
                       style={{
                         background: isActive ? "rgba(99,102,241,0.12)" : "transparent",
                         border: `1px solid ${isActive ? "rgba(99,102,241,0.3)" : "transparent"}`,
                       }}
                       onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.03)"; }}
                       onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLElement).style.background = "transparent"; }}>
                    <div className="flex items-start gap-1.5">
                      <span className="text-xs flex-shrink-0 mt-0.5">{agentMeta.icon}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium truncate"
                           style={{ color: isActive ? "#a5b4fc" : "var(--text-primary)" }}>
                          {s.preview || "新对话"}
                        </p>
                        <div className="flex items-center gap-1 mt-0.5">
                          {s.project_name && (
                            <span className="text-xs truncate" style={{ color: "var(--text-muted)", fontSize: "0.65rem", maxWidth: "80px" }}>
                              {s.project_name}
                            </span>
                          )}
                          <span className="text-xs" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>
                            {s.message_count || 0}条
                          </span>
                        </div>
                        <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>
                          {timeStr}
                        </p>
                      </div>
                    </div>
                    {/* Delete button */}
                    <button
                      onClick={(e) => handleDeleteSession(e, s.session_id)}
                      className="absolute top-1.5 right-1.5 w-5 h-5 flex items-center justify-center rounded text-xs opacity-0 group-hover:opacity-100 transition-opacity"
                      style={{ color: "#fca5a5", background: "rgba(239,68,68,0.1)" }}
                      title="删除对话"
                    >
                      &times;
                    </button>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
      {/* Collapse toggle (when collapsed) */}
      {historyCollapsed && (
        <button onClick={() => setHistoryCollapsed(false)} title="展开对话历史"
                className="flex-shrink-0 w-6 h-full flex items-center justify-center transition-all"
                style={{ background: "rgba(8,13,26,0.6)", borderRight: "1px solid var(--border)", color: "var(--text-muted)" }}
                onMouseEnter={e => { (e.target as HTMLElement).style.background = "rgba(99,102,241,0.08)"; }}
                onMouseLeave={e => { (e.target as HTMLElement).style.background = "rgba(8,13,26,0.6)"; }}>
          <span style={{ fontSize: "0.7rem" }}>&rsaquo;</span>
        </button>
      )}

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        {/* Current project indicator bar */}
        <div className="flex items-center gap-2 px-4 py-2 flex-shrink-0"
             style={{ borderBottom: "1px solid var(--border)", background: "rgba(8,13,26,0.9)" }}>
          {selectedProject ? (
            <>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>当前项目：</span>
              <span className="text-xs font-semibold" style={{ color: "#a5b4fc" }}>{selectedProject.name}</span>
              <span className="text-xs ml-1" style={{ color: "var(--text-muted)" }}>
                · {selectedProject.industry || "未设置行业"}
              </span>
            </>
          ) : (
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              未选择项目 — 输入 <code className="px-1 py-0.5 rounded text-xs" style={{ background: "rgba(99,102,241,0.15)", color: "#a5b4fc" }}>/</code> 快速切换或创建项目
            </span>
          )}
          <div className="ml-auto flex items-center gap-1.5">
            {/* Agent mode selector */}
            {(["auto","coach","tutor","competition","grader"] as const).map((mode) => {
              const meta = mode === "auto"
                ? { label: "自动", icon: "🤖" }
                : INTENT_META[mode] ?? { label: mode, icon: "" };
              const active = selectedAgentType === mode;
              return (
                <button
                  key={mode}
                  onClick={async () => {
                    setSelectedAgentType(mode);
                    await initChat(selectedProjectId, mode);
                  }}
                  className="text-xs px-2 py-1 rounded-lg transition-all"
                  style={{
                    background: active ? "rgba(99,102,241,0.25)" : "rgba(255,255,255,0.04)",
                    border: `1px solid ${active ? "rgba(99,102,241,0.5)" : "var(--border)"}`,
                    color: active ? "#a5b4fc" : "var(--text-muted)",
                  }}
                >
                  {meta.icon} {meta.label}
                </button>
              );
            })}
            <button
              onClick={() => setShowNewProjectModal(true)}
              className="text-xs px-2.5 py-1 rounded-lg transition-all"
              style={{ background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.2)", color: "#a5b4fc" }}
            >
              + 新建项目
            </button>
          </div>
        </div>

        <div className="flex-1 min-h-0">
          <ChatWindow
            messages={messages}
            onSend={handleSend}
            loading={loading}
            agentLabel="AI 助手"
            onUpload={selectedProjectId ? handleFileUpload : undefined}
            uploading={uploading}
            projects={projects}
            selectedProjectId={selectedProjectId}
            onSelectProject={(pid) => { setSelectedProjectId(pid); restoreOrInit(pid); }}
            onNewProject={() => setShowNewProjectModal(true)}
          />
        </div>
      </div>

      {/* New Project Modal */}
      {showNewProjectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center"
             style={{ background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)" }}
             onClick={(e) => { if (e.target === e.currentTarget) setShowNewProjectModal(false); }}>
          <div className="w-full max-w-md rounded-2xl p-6"
               style={{ background: "rgba(10,14,28,0.98)", border: "1px solid rgba(99,102,241,0.3)", boxShadow: "0 0 60px rgba(99,102,241,0.15)" }}>
            <h2 className="text-base font-bold mb-1" style={{ color: "var(--text-primary)" }}>创建新项目</h2>
            <p className="text-xs mb-5" style={{ color: "var(--text-muted)" }}>创建后将自动切换到新项目并开始新对话</p>
            <div className="space-y-3">
              {[
                { label: "项目名称 *", value: newProjectName, setter: setNewProjectName, placeholder: "例：眼科 AI 辅助诊断系统" },
                { label: "行业/赛道", value: newProjectIndustry, setter: setNewProjectIndustry, placeholder: "例：医疗健康" },
                { label: "项目描述", value: newProjectDesc, setter: setNewProjectDesc, placeholder: "一句话描述你的项目（可选）" },
              ].map(({ label, value, setter, placeholder }) => (
                <div key={label}>
                  <label className="block text-xs font-semibold mb-1" style={{ color: "var(--text-muted)" }}>{label}</label>
                  <input
                    value={value}
                    onChange={(e) => setter(e.target.value)}
                    placeholder={placeholder}
                    className="w-full px-3 py-2.5 rounded-xl text-sm outline-none"
                    style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                    onFocus={(e) => { e.target.style.borderColor = "rgba(99,102,241,0.5)"; }}
                    onBlur={(e) => { e.target.style.borderColor = "var(--border)"; }}
                    onKeyDown={(e) => { if (e.key === "Enter") handleCreateProject(newProjectName, newProjectIndustry, newProjectDesc); }}
                  />
                </div>
              ))}
            </div>
            <div className="flex gap-3 mt-5">
              <button
                onClick={() => setShowNewProjectModal(false)}
                className="flex-1 py-2.5 rounded-xl text-sm"
                style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)", color: "var(--text-muted)" }}
              >
                取消
              </button>
              <button
                onClick={() => handleCreateProject(newProjectName, newProjectIndustry, newProjectDesc)}
                disabled={!newProjectName.trim() || creatingProject}
                className="flex-1 py-2.5 rounded-xl text-sm btn-glow disabled:opacity-40"
              >
                {creatingProject ? "创建中..." : "创建并开始对话 →"}
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Intake Form Modal (前置采集层) */}
      {showIntakeForm && intakeSchema.length > 0 && (
        <div className="fixed inset-0 z-50 flex items-center justify-center"
             style={{ background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)" }}>
          <div className="w-full max-w-2xl max-h-[85vh] rounded-2xl flex flex-col"
               style={{ background: "rgba(10,14,28,0.98)", border: "1px solid rgba(99,102,241,0.3)", boxShadow: "0 0 60px rgba(99,102,241,0.15)" }}>
            {/* Header */}
            <div className="px-6 py-4 flex-shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
              <h2 className="text-base font-bold" style={{ color: "var(--text-primary)" }}>
                项目信息采集
              </h2>
              <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                填写越详细，AI 教练的诊断越精准。可以跳过不确定的项目，后续在对话中补充。
              </p>
            </div>
            {/* Form Body */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5">
              {intakeSchema.map((group: any) => (
                <div key={group.group}>
                  <h3 className="text-xs font-bold uppercase tracking-wider mb-3"
                      style={{ color: "#a5b4fc" }}>
                    {group.group}
                  </h3>
                  <div className="space-y-3">
                    {group.fields.map((field: any) => (
                      <div key={field.key}>
                        <label className="block text-xs font-semibold mb-1" style={{ color: "var(--text-muted)" }}>
                          {field.label} {field.required && <span style={{ color: "#ef4444" }}>*</span>}
                        </label>
                        {field.input_type === "select" ? (
                          <select
                            value={intakeData[field.key] || ""}
                            onChange={(e) => setIntakeData(prev => ({ ...prev, [field.key]: e.target.value }))}
                            className="w-full px-3 py-2.5 rounded-xl text-sm outline-none"
                            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                          >
                            <option value="">请选择...</option>
                            {field.options?.map((opt: string) => (
                              <option key={opt} value={opt}>{opt}</option>
                            ))}
                          </select>
                        ) : field.input_type === "textarea" ? (
                          <textarea
                            value={intakeData[field.key] || ""}
                            onChange={(e) => setIntakeData(prev => ({ ...prev, [field.key]: e.target.value }))}
                            placeholder={field.placeholder}
                            rows={2}
                            className="w-full px-3 py-2.5 rounded-xl text-sm outline-none resize-none"
                            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                          />
                        ) : (
                          <input
                            value={intakeData[field.key] || ""}
                            onChange={(e) => setIntakeData(prev => ({ ...prev, [field.key]: e.target.value }))}
                            placeholder={field.placeholder}
                            className="w-full px-3 py-2.5 rounded-xl text-sm outline-none"
                            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                          />
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            {/* Footer */}
            <div className="px-6 py-4 flex gap-3 flex-shrink-0" style={{ borderTop: "1px solid var(--border)" }}>
              <button
                onClick={handleIntakeSkip}
                className="flex-1 py-2.5 rounded-xl text-sm"
                style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)", color: "var(--text-muted)" }}
              >
                跳过，直接开始对话
              </button>
              <button
                onClick={handleIntakeSubmit}
                disabled={intakeSubmitting}
                className="flex-1 py-2.5 rounded-xl text-sm btn-glow disabled:opacity-40"
              >
                {intakeSubmitting ? "分析中..." : "提交并开始智能诊断 →"}
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Grader panel: full rubric report */}
      {intent === "grader" && rubricFull && (
        <div className="w-80 flex-shrink-0 flex flex-col overflow-hidden"
             style={{ borderLeft: "1px solid var(--border)", background: "rgba(8,13,26,0.7)" }}>
          <div className="px-4 py-3 flex-shrink-0 flex items-center gap-2"
               style={{ borderBottom: "1px solid var(--border)" }}>
            <span className="text-base">📋</span>
            <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
              形成性评价报告
            </p>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {/* Radar chart */}
            <RubricRadar data={rubricFull} maxScore={RUBRIC_MAX} />
            {/* Total score */}
            {(() => {
              const total = Object.values(rubricFull).reduce((s, v) => s + (v.score || 0), 0);
              const max = Object.keys(rubricFull).length * RUBRIC_MAX;
              return (
                <div className="text-center py-3 rounded-xl mb-2"
                     style={{ background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.2)" }}>
                  <p className="text-2xl font-bold gradient-text">{total} / {max}</p>
                  <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>综合得分</p>
                </div>
              );
            })()}
            {Object.entries(rubricFull).map(([key, item]) => (
              <div key={key} className="rounded-xl p-3 space-y-1.5"
                   style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>
                    {key} {RUBRIC_NAMES[key] || key}
                  </span>
                  <span className="text-sm font-bold" style={{ color: item.score >= 4 ? "#6ee7b7" : item.score >= 3 ? "#fcd34d" : "#fca5a5" }}>
                    {item.score}/{RUBRIC_MAX}
                  </span>
                </div>
                <div className="h-1 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                  <div className="h-1 rounded-full" style={{ width: `${(item.score / RUBRIC_MAX) * 100}%`, background: item.score >= 4 ? "linear-gradient(90deg, #10b981, #34d399)" : item.score >= 3 ? "linear-gradient(90deg, #f59e0b, #fbbf24)" : "linear-gradient(90deg, #ef4444, #f87171)" }} />
                </div>
                {item.evidence && (
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    <span style={{ color: "#6ee7b7" }}>证据：</span>{item.evidence.slice(0, 80)}{item.evidence.length > 80 ? "..." : ""}
                  </p>
                )}
                {item.suggestion && (
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    <span style={{ color: "#fcd34d" }}>建议：</span>{item.suggestion.slice(0, 80)}{item.suggestion.length > 80 ? "..." : ""}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      {false && <div className="w-72 flex flex-col flex-shrink-0 overflow-hidden"
           style={{ borderLeft: "1px solid var(--border)", background: "rgba(8,13,26,0.6)" }}>
        {(intent === "coach" || intent === "hybrid") && (
          <div className="flex-1 overflow-y-auto p-4">
            <p className="text-xs font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>能力评估</p>
            <div className="mb-5">
              <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>诊断阶段</p>
              <div className="flex gap-1">
                {stageKeys.map((key, idx) => {
                  const s = STAGE_MAP[key];
                  const active = stage === key;
                  const past = idx < stageIdx;
                  return (
                    <div key={key} className="flex-1 text-center py-1.5 rounded-lg text-xs font-medium transition-all"
                         style={{background: active ? `${s.color}25` : past ? "rgba(255,255,255,0.04)" : "transparent",
                           border: `1px solid ${active ? s.color + "55" : "var(--border)"}`, color: active ? s.color : "var(--text-muted)", fontSize: "0.6rem"}}>
                      {s.label}
                    </div>
                  );
                })}
              </div>
            </div>
            <ScoreRadar scores={scores} />
            {scores && (
              <div className="mt-4 space-y-2">
                <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>各维度得分</p>
                {Object.entries(SCORE_LABELS).map(([key, label]) => {
                  const val = (scores as any)[key] || 0;
                  return (
                    <div key={key}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs" style={{ color: "var(--text-secondary)" }}>{label}</span>
                        <span className="text-xs font-bold" style={{ color: scoreTextColor(val) }}>{val}</span>
                      </div>
                      <div className="h-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                        <div className="h-1.5 rounded-full score-bar-fill" style={{ width: `${val * 10}%`, background: scoreGradient(val) }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            {diagnosis.length > 0 && (
              <div className="mt-4">
                <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>诊断发现</p>
                <div className="space-y-2">
                  {diagnosis.map((d, i) => (
                    <div key={i} className="flex items-start gap-2 px-3 py-2 rounded-lg text-xs"
                         style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.2)" }}>
                      <span style={{ color: "#fcd34d" }}>⚠</span>
                      <span style={{ color: "var(--text-secondary)" }}>{d}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {knowledgeRecs.length > 0 && (
              <div className="mt-4">
                <p className="text-xs mb-2 font-medium" style={{ color: "#a5b4fc" }}>推荐学习</p>
                <div className="space-y-1.5">
                  {knowledgeRecs.map((rec, i) => (
                    <button key={i} onClick={() => handleKnowledgeRec(rec.query)}
                            className="w-full text-left px-3 py-2 rounded-xl text-xs transition-all"
                            style={{background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.2)", color: "var(--text-secondary)"}}>
                      <span className="font-medium" style={{ color: "#a5b4fc" }}>📚 {rec.concept}</span>
                      <span className="text-xs ml-1" style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>← {rec.rule_id}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
            {!scores && (<div className="mt-8 text-center"><div className="text-3xl mb-3 opacity-40">💬</div><p className="text-xs" style={{ color: "var(--text-muted)" }}>开始对话后，AI 将实时评估你在五个维度上的表现</p></div>)}
            {messages.length >= 4 && !ratingSubmitted && (
              <div className="mt-5 pt-4" style={{ borderTop: "1px solid var(--border)" }}>
                <p className="text-xs font-medium mb-2" style={{ color: "var(--text-muted)" }}>本次对话质量</p>
                <div className="flex gap-1 mb-2">
                  {[1, 2, 3, 4, 5].map((s) => (
                    <button key={s} onClick={() => setRatingValue(s)} className="text-xl transition-all"
                            style={{ color: s <= ratingValue ? "#fbbf24" : "rgba(255,255,255,0.2)", lineHeight: 1 }}>★</button>
                  ))}
                </div>
                {ratingValue > 0 && (
                  <>
                    <textarea rows={2} placeholder="留言（可选）" value={ratingComment} onChange={(e) => setRatingComment(e.target.value)}
                              className="w-full px-2 py-1.5 rounded-lg text-xs resize-none outline-none mb-2"
                              style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)", color: "var(--text-primary)" }} />
                    <button onClick={handleSubmitRating} className="w-full text-xs py-1.5 rounded-lg btn-glow">提交评分</button>
                  </>
                )}
              </div>
            )}
            {ratingSubmitted && (<div className="mt-4 text-center"><p className="text-xs" style={{ color: "#10b981" }}>✓ 感谢你的反馈！</p></div>)}
            {selectedProjectId && (<div className="mt-5 pt-4" style={{ borderTop: "1px solid var(--border)" }}><LearningPath projectId={selectedProjectId} compact /></div>)}
            {uploadedFiles.length > 0 && (
              <div className="mt-4 pt-3" style={{ borderTop: "1px solid var(--border)" }}>
                <p className="text-xs font-medium mb-2" style={{ color: "var(--text-muted)" }}>已上传文件</p>
                <div className="space-y-1">
                  {uploadedFiles.map((f, i) => (
                    <div key={i} className="text-xs px-2 py-1.5 rounded-lg flex items-center gap-2"
                         style={{ background: "rgba(255,255,255,0.03)" }}>
                      <span style={{ color: "#a5b4fc" }}>📎</span>
                      <span style={{ color: "var(--text-secondary)" }}>{f}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        {intent === "competition" && (
          <div className="flex-1 overflow-y-auto p-4">
            <p className="text-xs font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>Rubric 评分</p>
            {rubricScores ? (
              <div>
                <div className="space-y-3">
                  {Object.entries(rubricScores as Record<string, number>).map(([key, val]) => (
                    <div key={key}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs" style={{ color: "var(--text-secondary)" }}>{RUBRIC_NAMES[key] || key}</span>
                        <span className="text-xs font-bold" style={{ color: scoreTextColor(val) }}>{val}/{RUBRIC_MAX}</span>
                      </div>
                      <div className="h-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                        <div className="h-1.5 rounded-full score-bar-fill" style={{ width: `${(val / RUBRIC_MAX) * 100}%`, background: scoreGradient(val) }} />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-4 pt-3 flex justify-between items-center" style={{ borderTop: "1px solid var(--border)" }}>
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>总分</span>
                  <span className="font-bold gradient-text">{Object.values(rubricScores as Record<string, number>).reduce((a, b) => a + b, 0)} / {Object.keys(rubricScores as Record<string, number>).length * RUBRIC_MAX}</span>
                </div>
              </div>
            ) : (
              <div className="mt-8 text-center"><div className="text-3xl mb-3 opacity-40">🏆</div><p className="text-xs" style={{ color: "var(--text-muted)" }}>描述你的项目后，AI 将对照 R1-R9 标准逐项评估</p></div>
            )}
          </div>
        )}
        {intent === "tutor" && (
          <div className="flex-1 overflow-y-auto p-4">
            <p className="text-xs font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>概念导航</p>
            <p className="text-xs mb-3" style={{ color: "var(--text-muted)" }}>可直接询问以下概念：</p>
            <div className="flex flex-wrap gap-1.5 mb-5">
              {["PMF", "TAM/SAM/SOM", "Value Prop", "Moat", "CAC", "LTV", "BEP", "Lean Canvas", "JTBD", "AARRR", "SWOT", "商业模式画布", "波特五力"].map((c) => (
                <span key={c} className="badge badge-blue cursor-default">{c}</span>
              ))}
            </div>
            <div className="rounded-xl px-4 py-3 space-y-1" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)" }}>
              <p className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>每个概念包含：</p>
              {["定义 & 原理", "真实案例", "常见错误", "练习任务", "评价标准"].map((t, i) => (
                <p key={t} className="text-xs" style={{ color: "var(--text-muted)" }}><span style={{ color: "#6366f1" }}>{i + 1}.</span> {t}</p>
              ))}
            </div>
          </div>
        )}
      </div>}
    </div>
  );
}
