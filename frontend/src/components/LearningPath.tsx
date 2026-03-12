"use client";
import { useState, useEffect } from "react";
import { getLearningPath, updateTaskStatus, generateLearningPath } from "@/lib/api";
import { LearningTask } from "@/lib/types";

const DIM_LABELS: Record<string, string> = {
  empathy: "痛点发现", ideation: "方案策划",
  business: "商业建模", execution: "资源杠杆", pitching: "路演表达",
};
const DIM_COLORS: Record<string, string> = {
  empathy: "#6366f1", ideation: "#22d3ee",
  business: "#a78bfa", execution: "#f59e0b", pitching: "#10b981",
};

interface Props {
  projectId: string;
  compact?: boolean;
}

export default function LearningPath({ projectId, compact = false }: Props) {
  const [data, setData] = useState<{
    tasks: LearningTask[];
    by_dimension: Record<string, LearningTask[]>;
    total: number;
    completed: number;
    progress: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchPath = async () => {
    setLoading(true);
    try {
      const res = await getLearningPath(projectId);
      setData(res);
    } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => { fetchPath(); }, [projectId]);

  const toggleTask = async (taskId: string, currentStatus: string) => {
    const newStatus = currentStatus === "completed" ? "pending" : "completed";
    try {
      await updateTaskStatus(taskId, newStatus);
      fetchPath();
    } catch { /* ignore */ }
  };

  const handleRegenerate = async () => {
    try {
      await generateLearningPath(projectId);
      fetchPath();
    } catch { /* ignore */ }
  };

  if (loading) return <div className="text-sm" style={{ color: "var(--text-muted)" }}>加载学习路径...</div>;
  if (!data || data.total === 0) return (
    <div className="glass-card p-4 rounded-xl text-center">
      <p className="text-sm mb-2" style={{ color: "var(--text-muted)" }}>暂无学习任务</p>
      <button onClick={handleRegenerate} className="text-xs px-3 py-1.5 rounded-lg"
              style={{ background: "#6366f1", color: "white" }}>
        生成学习路径
      </button>
    </div>
  );

  // Compact mode: just show progress + top tasks
  if (compact) {
    const pending = data.tasks.filter(t => t.status === "pending").slice(0, 3);
    return (
      <div className="glass-card p-4 rounded-xl space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>学习路径</h3>
          <span className="text-xs" style={{ color: "#6366f1" }}>{data.progress}%</span>
        </div>
        <div className="w-full h-2 rounded-full" style={{ background: "rgba(255,255,255,0.05)" }}>
          <div className="h-full rounded-full transition-all" style={{
            width: `${data.progress}%`,
            background: "linear-gradient(90deg, #6366f1, #22d3ee)",
          }} />
        </div>
        <div className="space-y-1.5">
          {pending.map(t => (
            <div key={t.task_id} className="flex items-center gap-2 text-xs cursor-pointer"
                 onClick={() => toggleTask(t.task_id, t.status)}>
              <div className="w-3.5 h-3.5 rounded border flex-shrink-0"
                   style={{ borderColor: DIM_COLORS[t.dimension] || "#6366f1" }} />
              <span style={{ color: "var(--text-secondary)" }}>{t.title}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Full mode
  return (
    <div className="space-y-4">
      {/* Progress header */}
      <div className="glass-card p-4 rounded-xl">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            学习路径 · {data.completed}/{data.total} 已完成
          </h3>
          <button onClick={handleRegenerate} className="text-xs px-2 py-1 rounded-lg"
                  style={{ background: "rgba(99,102,241,0.15)", color: "#a5b4fc" }}>
            重新生成
          </button>
        </div>
        <div className="w-full h-3 rounded-full" style={{ background: "rgba(255,255,255,0.05)" }}>
          <div className="h-full rounded-full transition-all" style={{
            width: `${data.progress}%`,
            background: "linear-gradient(90deg, #6366f1, #22d3ee)",
          }} />
        </div>
        <p className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>{data.progress}% 完成</p>
      </div>

      {/* Tasks by dimension */}
      {Object.entries(data.by_dimension).map(([dim, tasks]) => (
        <div key={dim} className="glass-card p-4 rounded-xl">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2 h-2 rounded-full" style={{ background: DIM_COLORS[dim] || "#6366f1" }} />
            <h4 className="text-sm font-medium" style={{ color: DIM_COLORS[dim] || "var(--text-primary)" }}>
              {DIM_LABELS[dim] || dim}
            </h4>
            <span className="text-xs ml-auto" style={{ color: "var(--text-muted)" }}>
              {tasks.filter(t => t.status === "completed").length}/{tasks.length}
            </span>
          </div>
          <div className="space-y-2">
            {tasks.map(t => (
              <div key={t.task_id}
                   className="flex items-start gap-3 p-2 rounded-lg cursor-pointer hover:bg-white/5 transition-colors"
                   onClick={() => toggleTask(t.task_id, t.status)}>
                <div className="w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 mt-0.5"
                     style={{
                       borderColor: t.status === "completed" ? "#10b981" : (DIM_COLORS[dim] || "#6366f1"),
                       background: t.status === "completed" ? "#10b98133" : "transparent",
                     }}>
                  {t.status === "completed" && <span className="text-xs" style={{ color: "#10b981" }}>✓</span>}
                </div>
                <div className="flex-1">
                  <p className="text-sm" style={{
                    color: t.status === "completed" ? "var(--text-muted)" : "var(--text-primary)",
                    textDecoration: t.status === "completed" ? "line-through" : "none",
                  }}>{t.title}</p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>{t.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
