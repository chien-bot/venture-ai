"use client";
import { useState, useEffect } from "react";
import { getTeamMembers, addTeamMember, removeTeamMember } from "@/lib/api";
import { TeamMember } from "@/lib/types";

interface Props {
  projectId: string;
  isOwner?: boolean;
}

export default function TeamPanel({ projectId, isOwner = false }: Props) {
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchMembers = async () => {
    try {
      const res = await getTeamMembers(projectId);
      setMembers(res.members || []);
    } catch { /* ignore */ }
  };

  useEffect(() => { fetchMembers(); }, [projectId]);

  const handleAdd = async () => {
    if (!username.trim()) return;
    setLoading(true);
    setError("");
    try {
      await addTeamMember(projectId, username.trim());
      setUsername("");
      fetchMembers();
    } catch (e: any) {
      setError(e.message || "添加失败");
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (userId: string) => {
    try {
      await removeTeamMember(projectId, userId);
      fetchMembers();
    } catch { /* ignore */ }
  };

  const roleLabel = (role: string) => role === "owner" ? "创建者" : "成员";
  const roleColor = (role: string) => role === "owner" ? "#f59e0b" : "#6366f1";

  return (
    <div className="glass-card p-4 rounded-xl space-y-3">
      <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
        团队成员 ({members.length})
      </h3>

      <div className="space-y-2">
        {members.map((m) => (
          <div key={m.user_id} className="flex items-center gap-2 px-3 py-2 rounded-lg"
               style={{ background: "rgba(255,255,255,0.03)" }}>
            <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold"
                 style={{ background: `${roleColor(m.role)}33`, color: roleColor(m.role) }}>
              {(m.display_name || m.username || m.user_id)[0].toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm truncate" style={{ color: "var(--text-primary)" }}>
                {m.display_name || m.username || m.user_id}
              </p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>{roleLabel(m.role)}</p>
            </div>
            {isOwner && m.role !== "owner" && (
              <button onClick={() => handleRemove(m.user_id)}
                      className="text-xs px-2 py-1 rounded hover:bg-red-500/10"
                      style={{ color: "#ef4444" }}>
                移除
              </button>
            )}
          </div>
        ))}
      </div>

      {isOwner && (
        <div className="flex gap-2">
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            placeholder="输入用户名添加成员..."
            className="flex-1 text-sm px-3 py-2 rounded-lg"
            style={{
              background: "rgba(255,255,255,0.05)",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
              outline: "none",
            }}
          />
          <button onClick={handleAdd} disabled={loading}
                  className="text-sm px-3 py-2 rounded-lg font-medium"
                  style={{ background: "#6366f1", color: "white", opacity: loading ? 0.5 : 1 }}>
            添加
          </button>
        </div>
      )}
      {error && <p className="text-xs" style={{ color: "#ef4444" }}>{error}</p>}
    </div>
  );
}
