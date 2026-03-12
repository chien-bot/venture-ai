"use client";
import { useState, useEffect } from "react";
import {
  getMyReviewAssignments, getAvailableProjectsForReview,
  assignReview, submitPeerReview, getReceivedReviews,
  listProjects,
} from "@/lib/api";
import { ReviewAssignment, PeerReview, User } from "@/lib/types";

const DIMS = ["empathy", "ideation", "business", "execution", "pitching"] as const;
const DIM_LABELS: Record<string, string> = {
  empathy: "痛点发现", ideation: "方案策划",
  business: "商业建模", execution: "资源杠杆", pitching: "路演表达",
};

type Tab = "assignments" | "received" | "browse";

export default function PeerReviewPage() {
  const [user, setUser] = useState<User | null>(null);
  const [tab, setTab] = useState<Tab>("assignments");
  const [assignments, setAssignments] = useState<ReviewAssignment[]>([]);
  const [received, setReceived] = useState<PeerReview[]>([]);
  const [available, setAvailable] = useState<any[]>([]);
  const [myProjects, setMyProjects] = useState<any[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>("");

  // Review form state
  const [reviewingAssignment, setReviewingAssignment] = useState<ReviewAssignment | null>(null);
  const [scores, setScores] = useState<Record<string, number>>({});
  const [comments, setComments] = useState<Record<string, string>>({});
  const [overallComment, setOverallComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [claiming, setClaiming] = useState<string | null>(null);
  const [claimed, setClaimed] = useState<Set<string>>(new Set());

  useEffect(() => {
    const stored = sessionStorage.getItem("user");
    if (stored) {
      const u = JSON.parse(stored);
      setUser(u);
      loadData(u.user_id);
    }
  }, []);

  const loadData = async (userId: string) => {
    try {
      const [asgn, avail, projects] = await Promise.all([
        getMyReviewAssignments(userId),
        getAvailableProjectsForReview(userId),
        listProjects(userId),
      ]);
      setAssignments(asgn.assignments || []);
      setAvailable(avail.projects || []);
      setMyProjects(projects.projects || []);
    } catch { /* ignore */ }
  };

  const loadReceived = async (projectId: string) => {
    try {
      const res = await getReceivedReviews(projectId);
      setReceived(res.reviews || []);
    } catch { /* ignore */ }
  };

  const handleClaim = async (projectId: string) => {
    if (!user || claiming) return;
    setClaiming(projectId);
    try {
      await assignReview(user.user_id, projectId);
      setClaimed(prev => new Set(prev).add(projectId));
      loadData(user.user_id);
    } catch { /* ignore */ }
    setClaiming(null);
  };

  const startReview = (a: ReviewAssignment) => {
    setReviewingAssignment(a);
    setScores({});
    setComments({});
    setOverallComment("");
  };

  const handleSubmitReview = async () => {
    if (!reviewingAssignment) return;
    setSubmitting(true);
    try {
      await submitPeerReview(
        reviewingAssignment.assignment_id,
        reviewingAssignment.project_id,
        scores, comments, overallComment,
      );
      setReviewingAssignment(null);
      if (user) loadData(user.user_id);
    } catch { /* ignore */ }
    setSubmitting(false);
  };

  const tabs: { id: Tab; label: string }[] = [
    { id: "assignments", label: "待评审" },
    { id: "received", label: "收到的评价" },
    { id: "browse", label: "浏览项目" },
  ];

  return (
    <div className="flex-1 p-6 overflow-y-auto">
      <div className="max-w-4xl mx-auto space-y-6">
        <h1 className="text-xl font-bold gradient-text">同学互评</h1>

        {/* Tabs */}
        <div className="flex gap-2">
          {tabs.map(t => (
            <button key={t.id} onClick={() => {
              setTab(t.id);
              if (t.id === "received") {
                const projectId = selectedProject || myProjects[0]?.project_id;
                if (projectId) {
                  setSelectedProject(projectId);
                  loadReceived(projectId);
                }
              }
            }}
              className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              style={{
                background: tab === t.id ? "rgba(99,102,241,0.2)" : "rgba(255,255,255,0.03)",
                color: tab === t.id ? "#a5b4fc" : "var(--text-muted)",
                border: `1px solid ${tab === t.id ? "rgba(99,102,241,0.3)" : "var(--border)"}`,
              }}>
              {t.label}
            </button>
          ))}
        </div>

        {/* Review Form Modal */}
        {reviewingAssignment && tab === "assignments" && (
          <div style={{
            position: "fixed", inset: 0, zIndex: 50,
            background: "rgba(0,0,0,0.6)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <div style={{
              width: "100%", maxWidth: 560, maxHeight: "85vh",
              display: "flex", flexDirection: "column",
              background: "var(--bg-card, #0f172a)",
              border: "1px solid rgba(99,102,241,0.3)",
              borderRadius: 16, overflow: "hidden",
            }}>
              {/* Header */}
              <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", flexShrink: 0, display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
                <div>
                  <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                    评审项目: {reviewingAssignment.project_name || reviewingAssignment.project_id}
                  </h3>
                  <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>请对以下5个维度进行1-10分评分并给出建议</p>
                </div>
                <button onClick={() => setReviewingAssignment(null)}
                  style={{ color: "var(--text-muted)", fontSize: 18, lineHeight: 1, background: "none", border: "none", cursor: "pointer", marginLeft: 12 }}>
                  ✕
                </button>
              </div>

              {/* Scrollable body */}
              <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }} className="space-y-4">
                {DIMS.map(d => (
                  <div key={d} className="space-y-1">
                    <label className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
                      {DIM_LABELS[d]}
                    </label>
                    <div className="flex gap-3 items-center">
                      <input type="range" min={1} max={10} value={scores[d] || 5}
                        onChange={e => setScores({ ...scores, [d]: Number(e.target.value) })}
                        className="flex-1" />
                      <span className="text-sm w-6 text-right" style={{ color: "#a5b4fc" }}>{scores[d] || 5}</span>
                    </div>
                    <input value={comments[d] || ""} placeholder="简短建议..."
                      onChange={e => setComments({ ...comments, [d]: e.target.value })}
                      className="w-full text-sm px-3 py-1.5 rounded-lg"
                      style={{ background: "rgba(255,255,255,0.05)", border: "1px solid var(--border)",
                        color: "var(--text-primary)", outline: "none" }} />
                  </div>
                ))}
                <div>
                  <label className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>总体评价</label>
                  <textarea value={overallComment} onChange={e => setOverallComment(e.target.value)}
                    rows={3} placeholder="写下你的总体评价..."
                    className="w-full text-sm px-3 py-2 rounded-lg mt-1"
                    style={{ background: "rgba(255,255,255,0.05)", border: "1px solid var(--border)",
                      color: "var(--text-primary)", outline: "none", resize: "none" }} />
                </div>
              </div>

              {/* Fixed footer */}
              <div className="flex gap-2 justify-end" style={{
                padding: "12px 20px", borderTop: "1px solid var(--border)", flexShrink: 0,
                background: "var(--bg-card, #0f172a)",
              }}>
                <button onClick={() => setReviewingAssignment(null)}
                  className="px-4 py-2 rounded-lg text-sm"
                  style={{ color: "var(--text-muted)" }}>取消</button>
                <button onClick={handleSubmitReview} disabled={submitting}
                  className="px-4 py-2 rounded-lg text-sm font-medium"
                  style={{ background: "#6366f1", color: "white", opacity: submitting ? 0.5 : 1 }}>
                  {submitting ? "提交中..." : "提交评审"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Assignments Tab */}
        {tab === "assignments" && !reviewingAssignment && (
          <div className="space-y-3">
            {assignments.length === 0 ? (
              <div className="glass-card p-8 rounded-xl text-center">
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>暂无待评审任务</p>
                <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                  去「浏览项目」标签领取评审任务
                </p>
              </div>
            ) : assignments.map(a => (
              <div key={a.assignment_id} className="glass-card p-4 rounded-xl flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                    {a.project_name || a.project_id}
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                    状态: {a.status === "completed" ? "已完成" : "待评审"} · {a.created_at?.slice(0, 10)}
                  </p>
                </div>
                {a.status === "pending" && (
                  <button onClick={() => startReview(a)}
                    className="px-3 py-1.5 rounded-lg text-sm font-medium"
                    style={{ background: "#6366f1", color: "white" }}>
                    开始评审
                  </button>
                )}
                {a.status === "completed" && (
                  <span className="text-xs px-2 py-1 rounded-full"
                    style={{ background: "rgba(16,185,129,0.15)", color: "#6ee7b7" }}>已完成</span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Received Tab */}
        {tab === "received" && (
          <div className="space-y-4">
            {myProjects.length > 1 && (
              <select value={selectedProject}
                onChange={e => { setSelectedProject(e.target.value); loadReceived(e.target.value); }}
                className="text-sm px-3 py-2 rounded-lg"
                style={{ background: "rgba(255,255,255,0.05)", border: "1px solid var(--border)",
                  color: "var(--text-primary)", outline: "none" }}>
                {myProjects.map(p => (
                  <option key={p.project_id} value={p.project_id}>{p.name}</option>
                ))}
              </select>
            )}
            {received.length === 0 ? (
              <div className="glass-card p-8 rounded-xl text-center">
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>暂无收到的评价</p>
              </div>
            ) : received.map((r, i) => (
              <div key={r.review_id || i} className="glass-card p-4 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                    匿名评审 #{i + 1}
                  </span>
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {r.created_at?.slice(0, 10)}
                  </span>
                </div>
                <div className="grid grid-cols-5 gap-2">
                  {DIMS.map(d => (
                    <div key={d} className="text-center p-2 rounded-lg"
                      style={{ background: "rgba(255,255,255,0.03)" }}>
                      <p className="text-lg font-bold" style={{
                        color: (r.scores?.[d] || 0) >= 7 ? "#10b981" : (r.scores?.[d] || 0) >= 5 ? "#f59e0b" : "#ef4444"
                      }}>{r.scores?.[d] || "-"}</p>
                      <p className="text-xs" style={{ color: "var(--text-muted)" }}>{DIM_LABELS[d]}</p>
                      {r.comments?.[d] && (
                        <p className="text-xs mt-1" style={{ color: "var(--text-secondary)" }}>{r.comments[d]}</p>
                      )}
                    </div>
                  ))}
                </div>
                {r.overall_comment && (
                  <p className="text-sm" style={{ color: "var(--text-secondary)" }}>{r.overall_comment}</p>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Browse Tab */}
        {tab === "browse" && (
          <div className="space-y-3">
            {available.length === 0 ? (
              <div className="glass-card p-8 rounded-xl text-center">
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>暂无可评审的项目</p>
              </div>
            ) : available.map((p: any) => (
              <div key={p.project_id} className="glass-card p-4 rounded-xl flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{p.name}</p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                    {p.industry} · {p.stage || "未知阶段"}
                  </p>
                </div>
                <button onClick={() => handleClaim(p.project_id)}
                  disabled={!!claiming || claimed.has(p.project_id)}
                  className="px-3 py-1.5 rounded-lg text-sm font-medium transition-all"
                  style={{
                    background: claimed.has(p.project_id) ? "rgba(16,185,129,0.15)" : claiming === p.project_id ? "rgba(99,102,241,0.08)" : "rgba(99,102,241,0.15)",
                    color: claimed.has(p.project_id) ? "#6ee7b7" : "#a5b4fc",
                    opacity: claiming && claiming !== p.project_id ? 0.5 : 1,
                    cursor: claimed.has(p.project_id) ? "default" : "pointer",
                  }}>
                  {claimed.has(p.project_id) ? "✓ 已领取" : claiming === p.project_id ? "领取中..." : "领取评审"}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
