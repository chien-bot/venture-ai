"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken() {
  if (typeof window !== "undefined") return sessionStorage.getItem("token") || "";
  return "";
}

function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color: string }) {
  return (
    <div className="glass glass-hover rounded-xl p-5 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-16 h-16 rounded-full pointer-events-none"
           style={{ background: `radial-gradient(circle, ${color}18 0%, transparent 70%)`, transform: "translate(30%, -30%)" }} />
      <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>{label}</p>
      <p className="text-3xl font-bold mb-0.5" style={{ color }}>{value}</p>
      {sub && <p className="text-xs" style={{ color: "var(--text-muted)" }}>{sub}</p>}
    </div>
  );
}

type User = {
  user_id: string;
  username: string;
  role: string;
  display_name: string;
  class_id: string;
  created_at: string;
};

type DashboardData = {
  total_projects: number;
  average_score: number;
  scored_projects: number;
  top_vulnerabilities: { vulnerability: string; count: number }[];
  user_counts: { student: number; teacher: number; admin: number };
  class_summary: Record<string, { project_count: number; student_count: number; teacher_count: number }>;
  health_status: string;
  score_distribution: Record<string, number>;
  stage_distribution: Record<string, number>;
  class_avg_scores: Record<string, number>;
};

type ProjectInfo = {
  project_id: string;
  name: string;
  industry: string;
  owner_id: string;
  owner_name?: string;
  owner_class?: string;
  stage: string;
  scores: Record<string, number>;
  diagnosis: string[];
  created_at: string;
};

type Tab = "dashboard" | "users" | "projects";

export default function AdminDashboard() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("dashboard");
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [classes, setClasses] = useState<string[]>([]);
  const [newClassName, setNewClassName] = useState("");
  const [editingClassUser, setEditingClassUser] = useState<string | null>(null);
  const [allProjects, setAllProjects] = useState<ProjectInfo[]>([]);
  const [selectedUserIds, setSelectedUserIds] = useState<Set<string>>(new Set());
  const [batchClass, setBatchClass] = useState("");
  const [batchNewClass, setBatchNewClass] = useState("");
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [projectSearch, setProjectSearch] = useState("");
  const [projectStageFilter, setProjectStageFilter] = useState("");
  const [projectClassFilter, setProjectClassFilter] = useState("");
  const [selectedProject, setSelectedProject] = useState<ProjectInfo | null>(null);

  const headers = { Authorization: `Bearer ${getToken()}`, "Content-Type": "application/json" };

  useEffect(() => {
    const user = sessionStorage.getItem("user");
    if (user) {
      const parsed = JSON.parse(user);
      if (parsed.role !== "admin") {
        router.push("/");
        return;
      }
    }
    fetchDashboard();
    fetchUsers();
    fetchClasses();
    fetchProjects();
  }, []);

  // Re-fetch projects when switching to projects tab
  useEffect(() => {
    if (tab === "projects" && allProjects.length === 0) {
      fetchProjects();
    }
  }, [tab]);

  async function fetchDashboard() {
    try {
      const res = await fetch(`${API}/api/admin/dashboard`, { headers });
      if (res.status === 403) { setError("Unauthorized Access Attempt"); return; }
      if (!res.ok) throw new Error("Failed");
      setDashboard(await res.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function fetchUsers() {
    try {
      const res = await fetch(`${API}/api/admin/users`, { headers });
      if (!res.ok) return;
      const data = await res.json();
      setUsers(data.users || []);
    } catch {}
  }

  async function fetchClasses() {
    try {
      const res = await fetch(`${API}/api/admin/classes`, { headers });
      if (res.ok) {
        const data = await res.json();
        setClasses(data.classes || []);
      }
    } catch {}
  }

  async function updateRole(userId: string, newRole: string) {
    try {
      const res = await fetch(`${API}/api/admin/users/${userId}/role`, {
        method: "PUT", headers,
        body: JSON.stringify({ role: newRole }),
      });
      if (res.ok) fetchUsers();
    } catch {}
  }

  async function updateClass(userId: string, classId: string) {
    try {
      const res = await fetch(`${API}/api/admin/users/${userId}/class`, {
        method: "PUT", headers,
        body: JSON.stringify({ class_id: classId }),
      });
      if (res.ok) {
        fetchUsers();
        fetchClasses();
        fetchDashboard();
        setEditingClassUser(null);
        setNewClassName("");
      }
    } catch {}
  }

  async function fetchProjects() {
    setProjectsLoading(true);
    try {
      const token = getToken();
      const res = await fetch(`${API}/api/admin/projects`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setAllProjects(data.projects || []);
      } else {
        console.error("fetchProjects failed:", res.status);
      }
    } catch (e) {
      console.error("fetchProjects error:", e);
    } finally {
      setProjectsLoading(false);
    }
  }

  async function batchUpdateClass() {
    const cls = batchClass === "__new__" ? batchNewClass.trim() : batchClass;
    if (!cls || selectedUserIds.size === 0) return;
    try {
      const res = await fetch(`${API}/api/admin/users/batch-class`, {
        method: "PUT", headers,
        body: JSON.stringify({ user_ids: Array.from(selectedUserIds), class_id: cls }),
      });
      if (res.ok) {
        fetchUsers(); fetchClasses(); fetchDashboard();
        setSelectedUserIds(new Set());
        setBatchClass(""); setBatchNewClass("");
      }
    } catch {}
  }

  async function handleExportExcel() {
    try {
      const res = await fetch(`${API}/api/admin/export/excel`, { headers: { Authorization: `Bearer ${getToken()}` } });
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "ventureai_admin_export.xlsx";
      a.click();
      URL.revokeObjectURL(url);
    } catch {}
  }

  function toggleSelectUser(uid: string) {
    setSelectedUserIds((prev) => {
      const next = new Set(prev);
      if (next.has(uid)) next.delete(uid); else next.add(uid);
      return next;
    });
  }

  function toggleSelectAll() {
    const nonAdminUsers = users.filter(u => u.role !== "admin");
    if (selectedUserIds.size === nonAdminUsers.length) {
      setSelectedUserIds(new Set());
    } else {
      setSelectedUserIds(new Set(nonAdminUsers.map(u => u.user_id)));
    }
  }

  async function deleteUser(userId: string, username: string) {
    if (!confirm(`确定删除用户 ${username}？此操作不可撤销。`)) return;
    try {
      const res = await fetch(`${API}/api/admin/users/${userId}`, { method: "DELETE", headers });
      if (res.ok) fetchUsers();
    } catch {}
  }

  async function handleLogout() {
    try {
      const token = getToken();
      await fetch(`${API}/api/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {}
    sessionStorage.clear();
    document.cookie = "token=; path=/; max-age=0";
    router.push("/");
  }

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-base)" }}>
      <div className="w-8 h-8 border-2 border-amber-400/30 border-t-amber-400 rounded-full animate-spin" />
    </div>
  );

  if (error) return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-base)" }}>
      <div className="glass rounded-xl p-8 text-center">
        <p className="text-red-400 text-lg font-bold mb-2">403 Forbidden</p>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>{error}</p>
        <button onClick={() => router.push("/")} className="mt-4 px-6 py-2 rounded-lg text-sm" style={{ background: "rgba(245,158,11,0.2)", color: "#fcd34d" }}>
          返回登录
        </button>
      </div>
    </div>
  );

  const healthColors: Record<string, string> = { healthy: "#10b981", at_risk: "#f59e0b", critical: "#ef4444" };
  const healthLabels: Record<string, string> = { healthy: "健康", at_risk: "需关注", critical: "高风险" };
  const stageLabels: Record<string, string> = { discovery: "发现", ideation: "构思", modeling: "建模", validation: "验证", pitching: "路演" };
  const stageColors: Record<string, string> = { discovery: "#6366f1", ideation: "#22d3ee", modeling: "#a78bfa", validation: "#f59e0b", pitching: "#10b981" };

  // Filtered projects
  const filteredProjects = allProjects.filter((p) => {
    if (projectSearch) {
      const q = projectSearch.toLowerCase();
      const nameMatch = p.name.toLowerCase().includes(q);
      const ownerMatch = (p.owner_name || p.owner_id).toLowerCase().includes(q);
      const industryMatch = (p.industry || "").toLowerCase().includes(q);
      if (!nameMatch && !ownerMatch && !industryMatch) return false;
    }
    if (projectStageFilter && (p.stage || "discovery") !== projectStageFilter) return false;
    if (projectClassFilter && (p.owner_class || "未分班") !== projectClassFilter) return false;
    return true;
  });

  // Unique stages and classes for filter dropdowns
  const projectStages = [...new Set(allProjects.map(p => p.stage || "discovery"))];
  const projectClasses = [...new Set(allProjects.map(p => p.owner_class || "未分班"))];

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-base)" }}>
      {/* Header */}
      <div className="glass border-b" style={{ borderColor: "var(--border)" }}>
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                 style={{ background: "linear-gradient(135deg, rgba(245,158,11,0.3), rgba(245,158,11,0.15))", border: "1px solid rgba(245,158,11,0.4)" }}>
              <span className="text-xl">⚙</span>
            </div>
            <div>
              <h1 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>VentureAI 管理后台</h1>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>教务管理端 Admin Portal</p>
            </div>
          </div>
          <button onClick={handleLogout} className="px-4 py-2 rounded-lg text-sm" style={{ background: "rgba(239,68,68,0.1)", color: "#fca5a5", border: "1px solid rgba(239,68,68,0.3)" }}>
            退出登录
          </button>
        </div>
      </div>

      {/* Tab bar */}
      <div className="max-w-7xl mx-auto px-6 mt-6">
        <div className="flex items-center gap-3">
          <div className="flex rounded-xl p-1" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)" }}>
            {([["dashboard", "全局大盘"], ["users", "用户管理"], ["projects", "项目管理"]] as const).map(([key, label]) => (
              <button key={key} onClick={() => setTab(key as Tab)}
                className="px-6 py-2 rounded-lg text-sm font-medium transition-all"
                style={tab === key ? { background: "linear-gradient(135deg, rgba(245,158,11,0.3), rgba(245,158,11,0.15))", color: "#fcd34d", border: "1px solid rgba(245,158,11,0.4)" } : { color: "var(--text-muted)" }}>
                {label}
              </button>
            ))}
          </div>
          <button onClick={handleExportExcel}
            className="px-4 py-2 rounded-lg text-sm font-medium transition-all"
            style={{ background: "rgba(16,185,129,0.12)", color: "#6ee7b7", border: "1px solid rgba(16,185,129,0.3)" }}>
            导出 Excel
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {tab === "dashboard" && dashboard && (
          <div className="space-y-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="项目总数" value={dashboard.total_projects} color="#6366f1" />
              <StatCard label="平均分" value={dashboard.average_score} sub={`${dashboard.scored_projects} 个已评分`} color="#22d3ee" />
              <StatCard label="学生数" value={dashboard.user_counts.student} sub={`${dashboard.user_counts.teacher} 位教师`} color="#a78bfa" />
              <StatCard label="系统健康度" value={healthLabels[dashboard.health_status] || "未知"} color={healthColors[dashboard.health_status] || "#6b7280"} />
            </div>

            {/* Top Vulnerabilities */}
            <div className="glass rounded-xl p-6">
              <h2 className="text-sm font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>高频业务漏洞 Top 5</h2>
              {dashboard.top_vulnerabilities.length === 0 ? (
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>暂无数据</p>
              ) : (
                <div className="space-y-3">
                  {dashboard.top_vulnerabilities.map((v, i) => (
                    <div key={i} className="flex items-center gap-4">
                      <span className="text-xs font-bold w-6 h-6 rounded-full flex items-center justify-center" style={{ background: "rgba(245,158,11,0.2)", color: "#fcd34d" }}>{i + 1}</span>
                      <div className="flex-1">
                        <div className="h-2 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                          <div className="h-2 rounded-full" style={{ width: `${Math.min(100, (v.count / (dashboard.top_vulnerabilities[0]?.count || 1)) * 100)}%`, background: "linear-gradient(90deg, #f59e0b, #ef4444)" }} />
                        </div>
                      </div>
                      <span className="text-sm" style={{ color: "var(--text-secondary)" }}>{v.vulnerability}</span>
                      <span className="text-xs font-mono px-2 py-0.5 rounded" style={{ background: "rgba(245,158,11,0.1)", color: "#fcd34d" }}>{v.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Score Distribution */}
              <div className="glass rounded-xl p-6">
                <h2 className="text-sm font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>评分分布</h2>
                <div className="flex items-end gap-3" style={{ height: "160px" }}>
                  {Object.entries(dashboard.score_distribution || {}).map(([range, count]) => {
                    const maxCount = Math.max(...Object.values(dashboard.score_distribution || {}), 1);
                    const barH = count > 0 ? Math.max((count / maxCount) * 120, 20) : 0;
                    const colors: Record<string, string> = { "0-2": "#ef4444", "2-4": "#f59e0b", "4-6": "#eab308", "6-8": "#22d3ee", "8-10": "#10b981" };
                    return (
                      <div key={range} className="flex-1 flex flex-col items-center justify-end" style={{ height: "100%" }}>
                        <span className="text-xs font-bold mb-1" style={{ color: count > 0 ? colors[range] : "var(--text-muted)", opacity: count > 0 ? 1 : 0.4 }}>{count}</span>
                        {count > 0 ? (
                          <div className="w-full rounded-t-md" style={{ height: `${barH}px`, background: `linear-gradient(180deg, ${colors[range]}cc, ${colors[range]}44)`, borderTop: `1px solid ${colors[range]}66`, borderLeft: `1px solid ${colors[range]}66`, borderRight: `1px solid ${colors[range]}66` }} />
                        ) : (
                          <div className="w-full" style={{ height: "3px", background: "rgba(255,255,255,0.1)", borderRadius: "2px" }} />
                        )}
                        <span className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>{range}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Stage Distribution */}
              <div className="glass rounded-xl p-6">
                <h2 className="text-sm font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>阶段分布</h2>
                <div className="space-y-3">
                  {Object.entries(dashboard.stage_distribution || {}).map(([stage, count]) => {
                    const total = Object.values(dashboard.stage_distribution || {}).reduce((a, b) => a + b, 0) || 1;
                    const pct = (count / total) * 100;
                    const color = stageColors[stage] || "#6b7280";
                    return (
                      <div key={stage} className="flex items-center gap-3">
                        <span className="text-xs w-12 text-right font-medium" style={{ color }}>{stageLabels[stage] || stage}</span>
                        <div className="flex-1 h-5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.06)" }}>
                          <div className="h-full rounded-full transition-all flex items-center pl-2" style={{ width: `${Math.max(pct, 8)}%`, background: `linear-gradient(90deg, ${color}cc, ${color}44)` }}>
                            <span className="text-xs font-bold text-white/80">{count}</span>
                          </div>
                        </div>
                        <span className="text-xs w-10" style={{ color: "var(--text-muted)" }}>{pct.toFixed(0)}%</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Class Comparison */}
            <div className="glass rounded-xl p-6">
              <h2 className="text-sm font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>班级平均分对比</h2>
              {Object.keys(dashboard.class_avg_scores || {}).length === 0 ? (
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>暂无评分数据</p>
              ) : (
                <div style={{ display: "flex", alignItems: "flex-end", gap: "16px", height: "180px", paddingTop: "8px" }}>
                  {Object.entries(dashboard.class_avg_scores || {})
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([cls, avg], i) => {
                      const barH = Math.max(Math.round((avg / 10) * 130), 20);
                      const hue = (i * 70 + 200) % 360;
                      const color = `hsl(${hue}, 70%, 65%)`;
                      const colorFaded = `hsla(${hue}, 70%, 65%, 0.2)`;
                      return (
                        <div key={cls} style={{ flex: 1, textAlign: "center" }}>
                          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end", height: "150px" }}>
                            <span style={{ fontSize: "14px", fontWeight: 700, color, marginBottom: "6px" }}>{avg}</span>
                            <div style={{ width: "48px", height: `${barH}px`, background: `linear-gradient(to top, ${colorFaded}, ${color})`, borderRadius: "6px 6px 0 0" }} />
                          </div>
                          <span style={{ fontSize: "11px", color: "var(--text-muted)", display: "block", marginTop: "6px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{cls}</span>
                        </div>
                      );
                    })}
                </div>
              )}
            </div>

            {/* Class Summary */}
            <div className="glass rounded-xl p-6">
              <h2 className="text-sm font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>班级概览</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {Object.entries(dashboard.class_summary)
                  .sort(([a], [b]) => a === "未分班" ? -1 : b === "未分班" ? 1 : a.localeCompare(b))
                  .map(([cls, info]) => (
                  <div key={cls} className="rounded-lg p-4" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)" }}>
                    <p className="font-medium text-sm mb-2" style={{ color: "var(--text-primary)" }}>{cls || "未分班"}</p>
                    <div className="flex gap-4 text-xs" style={{ color: "var(--text-muted)" }}>
                      <span>{info.student_count} 学生</span>
                      <span>{info.teacher_count} 教师</span>
                      <span>{info.project_count} 项目</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {tab === "users" && (
          <div className="space-y-3">
            {/* Batch action bar */}
            {selectedUserIds.size > 0 && (
              <div className="glass rounded-xl px-5 py-3 flex items-center gap-3">
                <span className="text-xs font-medium" style={{ color: "#fcd34d" }}>
                  已选 {selectedUserIds.size} 人
                </span>
                <select value={batchClass} onChange={(e) => setBatchClass(e.target.value)}
                  className="rounded-lg px-3 py-1.5 text-xs"
                  style={{ background: "rgba(255,255,255,0.06)", border: "1px solid var(--border)", color: "var(--text-primary)" }}>
                  <option value="">选择班级...</option>
                  {classes.map(c => <option key={c} value={c}>{c}</option>)}
                  <option value="__new__">+ 新建班级</option>
                </select>
                {batchClass === "__new__" && (
                  <input value={batchNewClass} onChange={(e) => setBatchNewClass(e.target.value)}
                    placeholder="新班级名"
                    className="rounded-lg px-3 py-1.5 text-xs w-32"
                    style={{ background: "rgba(255,255,255,0.06)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                    onKeyDown={(e) => { if (e.key === "Enter") batchUpdateClass(); }}
                  />
                )}
                <button onClick={batchUpdateClass}
                  disabled={!batchClass || (batchClass === "__new__" && !batchNewClass.trim())}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium disabled:opacity-40"
                  style={{ background: "rgba(245,158,11,0.2)", color: "#fcd34d", border: "1px solid rgba(245,158,11,0.3)" }}>
                  批量分班
                </button>
                <button onClick={() => setSelectedUserIds(new Set())}
                  className="text-xs" style={{ color: "var(--text-muted)" }}>
                  取消选择
                </button>
              </div>
            )}
          <div className="glass rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  <th className="px-3 py-3 w-8">
                    <input type="checkbox" checked={selectedUserIds.size === users.filter(u => u.role !== "admin").length && users.filter(u => u.role !== "admin").length > 0}
                      onChange={toggleSelectAll}
                      className="rounded" style={{ accentColor: "#f59e0b" }} />
                  </th>
                  {["用户名", "显示名称", "角色", "班级", "注册时间", "操作"].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.user_id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td className="px-3 py-3">
                      {u.role !== "admin" ? (
                        <input type="checkbox" checked={selectedUserIds.has(u.user_id)}
                          onChange={() => toggleSelectUser(u.user_id)}
                          style={{ accentColor: "#f59e0b" }} />
                      ) : <span />}
                    </td>
                    <td className="px-4 py-3" style={{ color: "var(--text-primary)" }}>{u.username}</td>
                    <td className="px-4 py-3" style={{ color: "var(--text-secondary)" }}>{u.display_name}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 rounded text-xs font-medium"
                        style={u.role === "admin"
                          ? { background: "rgba(245,158,11,0.15)", color: "#fcd34d", border: "1px solid rgba(245,158,11,0.3)" }
                          : u.role === "teacher"
                          ? { background: "rgba(16,185,129,0.15)", color: "#6ee7b7", border: "1px solid rgba(16,185,129,0.3)" }
                          : { background: "rgba(99,102,241,0.15)", color: "#a5b4fc", border: "1px solid rgba(99,102,241,0.3)" }
                        }>
                        {u.role === "admin" ? "管理员" : u.role === "teacher" ? "教师" : "学生"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {u.role === "admin" ? (
                        <span style={{ color: "var(--text-muted)" }}>—</span>
                      ) : editingClassUser === u.user_id ? (
                        <div className="flex items-center gap-1">
                          <select
                            defaultValue={u.class_id || ""}
                            onChange={(e) => {
                              if (e.target.value === "__new__") {
                                setNewClassName("");
                              } else {
                                updateClass(u.user_id, e.target.value);
                              }
                            }}
                            className="rounded px-2 py-1 text-xs"
                            style={{ background: "rgba(255,255,255,0.06)", border: "1px solid var(--border)", color: "var(--text-primary)" }}>
                            <option value="">未分班</option>
                            {classes.map(c => <option key={c} value={c}>{c}</option>)}
                            <option value="__new__">+ 新建班级</option>
                          </select>
                          <input
                            placeholder="新班级名"
                            value={newClassName}
                            onChange={(e) => setNewClassName(e.target.value)}
                            onKeyDown={(e) => { if (e.key === "Enter" && newClassName.trim()) updateClass(u.user_id, newClassName.trim()); }}
                            className="rounded px-2 py-1 text-xs w-24"
                            style={{ background: "rgba(255,255,255,0.06)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                          />
                          <button onClick={() => { if (newClassName.trim()) updateClass(u.user_id, newClassName.trim()); else setEditingClassUser(null); }}
                            className="text-xs px-2 py-1 rounded"
                            style={{ background: "rgba(34,197,94,0.15)", color: "#86efac", border: "1px solid rgba(34,197,94,0.3)" }}>
                            ✓
                          </button>
                          <button onClick={() => setEditingClassUser(null)}
                            className="text-xs px-1 py-1 rounded"
                            style={{ color: "var(--text-muted)" }}>
                            ✕
                          </button>
                        </div>
                      ) : (
                        <span onClick={() => setEditingClassUser(u.user_id)}
                          className="cursor-pointer hover:underline"
                          style={{ color: u.class_id ? "var(--text-secondary)" : "var(--text-muted)" }}>
                          {u.class_id || "未分班"} ✎
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{u.created_at?.slice(0, 10)}</td>
                    <td className="px-4 py-3">
                      <button onClick={() => deleteUser(u.user_id, u.username)}
                        className="px-3 py-1 rounded text-xs"
                        style={{ background: "rgba(239,68,68,0.1)", color: "#fca5a5", border: "1px solid rgba(239,68,68,0.2)" }}>
                        删除
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          </div>
        )}

        {tab === "projects" && (
          <div className="space-y-4">
            {/* Search & Filter Bar */}
            <div className="glass rounded-xl px-5 py-3 flex flex-wrap items-center gap-3">
              <input
                value={projectSearch}
                onChange={(e) => setProjectSearch(e.target.value)}
                placeholder="搜索项目名称、所有者、行业..."
                className="flex-1 min-w-48 rounded-lg px-3 py-2 text-sm"
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
              />
              <select value={projectStageFilter} onChange={(e) => setProjectStageFilter(e.target.value)}
                className="rounded-lg px-3 py-2 text-xs"
                style={{ background: "#1e1e2e", border: "1px solid var(--border)", color: "var(--text-primary)" }}>
                <option value="" style={{ background: "#1e1e2e", color: "#e2e8f0" }}>全部阶段</option>
                {projectStages.map(s => <option key={s} value={s} style={{ background: "#1e1e2e", color: "#e2e8f0" }}>{stageLabels[s] || s}</option>)}
              </select>
              <select value={projectClassFilter} onChange={(e) => setProjectClassFilter(e.target.value)}
                className="rounded-lg px-3 py-2 text-xs"
                style={{ background: "#1e1e2e", border: "1px solid var(--border)", color: "var(--text-primary)" }}>
                <option value="" style={{ background: "#1e1e2e", color: "#e2e8f0" }}>全部班级</option>
                {projectClasses.map(c => <option key={c} value={c} style={{ background: "#1e1e2e", color: "#e2e8f0" }}>{c}</option>)}
              </select>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                {filteredProjects.length} / {allProjects.length} 项目
              </span>
            </div>

            <div className="flex gap-4">
              {/* Projects Table */}
              <div className={`glass rounded-xl overflow-hidden ${selectedProject ? "flex-1" : "w-full"}`}>
                <table className="w-full text-sm">
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border)" }}>
                      {["项目名称", "行业", "所有者", "班级", "阶段", "评分", "创建时间"].map(h => (
                        <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredProjects.map((p) => {
                      const scores = p.scores || {};
                      const avg = Object.values(scores).length > 0
                        ? (Object.values(scores).reduce((a, b) => a + b, 0) / Object.values(scores).length).toFixed(1)
                        : "—";
                      const avgNum = parseFloat(avg) || 0;
                      const isSelected = selectedProject?.project_id === p.project_id;
                      return (
                        <tr key={p.project_id}
                          onClick={() => setSelectedProject(isSelected ? null : p)}
                          className="cursor-pointer transition-all"
                          style={{
                            borderBottom: "1px solid var(--border)",
                            background: isSelected ? "rgba(245,158,11,0.08)" : undefined,
                          }}
                          onMouseEnter={(e) => { if (!isSelected) (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.03)"; }}
                          onMouseLeave={(e) => { if (!isSelected) (e.currentTarget as HTMLElement).style.background = ""; }}
                        >
                          <td className="px-4 py-3 font-medium" style={{ color: "var(--text-primary)" }}>{p.name}</td>
                          <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{p.industry || "—"}</td>
                          <td className="px-4 py-3 text-xs" style={{ color: "var(--text-secondary)" }}>{p.owner_name || p.owner_id}</td>
                          <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{p.owner_class || "—"}</td>
                          <td className="px-4 py-3">
                            <span className="text-xs px-2 py-0.5 rounded"
                              style={{ background: `${stageColors[p.stage] || "#6366f1"}20`, color: stageColors[p.stage] || "#a5b4fc" }}>
                              {stageLabels[p.stage] || p.stage || "discovery"}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-xs font-bold"
                              style={{ color: avgNum >= 7 ? "#6ee7b7" : avgNum >= 4 ? "#fcd34d" : avgNum > 0 ? "#fca5a5" : "var(--text-muted)" }}>
                              {avg}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{p.created_at?.slice(0, 10)}</td>
                        </tr>
                      );
                    })}
                    {filteredProjects.length === 0 && (
                      <tr>
                        <td colSpan={7} className="px-4 py-8 text-center text-sm" style={{ color: "var(--text-muted)" }}>
                          {projectsLoading ? "加载中..." : projectSearch || projectStageFilter || projectClassFilter ? "无匹配项目" : "暂无项目数据"}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Project Detail Panel */}
              {selectedProject && (() => {
                const p = selectedProject;
                const scores = p.scores || {};
                const scoreEntries = Object.entries(scores);
                const avg = scoreEntries.length > 0
                  ? (scoreEntries.reduce((a, [, v]) => a + v, 0) / scoreEntries.length).toFixed(1)
                  : "—";
                const dimLabels: Record<string, string> = { empathy: "同理心", ideation: "创意力", business: "商业力", execution: "执行力", pitching: "表达力" };
                return (
                  <div className="glass rounded-xl p-5 w-80 shrink-0 space-y-5 self-start sticky top-6">
                    {/* Header */}
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="text-base font-bold" style={{ color: "var(--text-primary)" }}>{p.name}</h3>
                        <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>{p.industry || "未设置行业"}</p>
                      </div>
                      <button onClick={() => setSelectedProject(null)} className="text-sm px-2 py-1 rounded"
                        style={{ color: "var(--text-muted)" }}>✕</button>
                    </div>

                    {/* Info */}
                    <div className="space-y-2 text-xs">
                      <div className="flex justify-between">
                        <span style={{ color: "var(--text-muted)" }}>所有者</span>
                        <span style={{ color: "var(--text-secondary)" }}>{p.owner_name || p.owner_id}</span>
                      </div>
                      <div className="flex justify-between">
                        <span style={{ color: "var(--text-muted)" }}>班级</span>
                        <span style={{ color: "var(--text-secondary)" }}>{p.owner_class || "未分班"}</span>
                      </div>
                      <div className="flex justify-between">
                        <span style={{ color: "var(--text-muted)" }}>阶段</span>
                        <span className="px-2 py-0.5 rounded" style={{ background: `${stageColors[p.stage] || "#6366f1"}20`, color: stageColors[p.stage] || "#a5b4fc" }}>
                          {stageLabels[p.stage] || p.stage || "discovery"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span style={{ color: "var(--text-muted)" }}>创建时间</span>
                        <span style={{ color: "var(--text-secondary)" }}>{p.created_at?.slice(0, 10)}</span>
                      </div>
                    </div>

                    {/* Scores */}
                    {scoreEntries.length > 0 ? (
                      <div>
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>维度评分</span>
                          <span className="text-lg font-bold" style={{ color: "#fcd34d" }}>{avg}</span>
                        </div>
                        <div className="space-y-2">
                          {scoreEntries.map(([dim, val]) => {
                            const pct = (val / 10) * 100;
                            const color = val >= 7 ? "#10b981" : val >= 4 ? "#f59e0b" : "#ef4444";
                            return (
                              <div key={dim}>
                                <div className="flex justify-between text-xs mb-1">
                                  <span style={{ color: "var(--text-secondary)" }}>{dimLabels[dim] || dim}</span>
                                  <span className="font-bold" style={{ color }}>{val}</span>
                                </div>
                                <div className="h-2 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                                  <div className="h-2 rounded-full transition-all" style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${color}cc, ${color}44)` }} />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs" style={{ color: "var(--text-muted)" }}>暂无评分数据</p>
                    )}

                    {/* Diagnosis */}
                    {p.diagnosis && p.diagnosis.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>诊断结果</p>
                        <div className="flex flex-wrap gap-1.5">
                          {p.diagnosis.map((d, i) => (
                            <span key={i} className="text-xs px-2 py-1 rounded"
                              style={{ background: "rgba(239,68,68,0.1)", color: "#fca5a5", border: "1px solid rgba(239,68,68,0.2)" }}>
                              {d}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
