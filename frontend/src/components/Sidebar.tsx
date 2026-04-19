"use client";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useEffect, useState, Suspense } from "react";
import { User } from "@/lib/types";

const CHAT_MODES = [
  { label: "自动模式",  mode: "auto",        icon: "🤖" },
  { label: "项目教练",  mode: "coach",       icon: "🎯" },
  { label: "概念辅导",  mode: "tutor",       icon: "📚" },
  { label: "竞赛评分",  mode: "competition", icon: "🏆" },
  { label: "批改评估",  mode: "grader",      icon: "📝" },
];

const STUDENT_NAV = [
  { label: "AI 教练",  path: "/student/chat",        icon: "💬", desc: "智能对话" },
  { label: "我的项目", path: "/student/projects",     icon: "📋", desc: "项目管理" },
  { label: "能力画像", path: "/student/profile",      icon: "📊", desc: "个人画像" },
  { label: "模拟答辩", path: "/student/defense",      icon: "🎤", desc: "投资人问答" },
  { label: "同学互评", path: "/student/peer-review",  icon: "👥", desc: "匿名评审" },
];

const TEACHER_NAV = [
  { label: "控制面板", path: "/teacher/dashboard",         icon: "📊", desc: "班级概览" },
  { label: "项目审阅", path: "/teacher/review",            icon: "📝", desc: "逐项评分" },
  { label: "对话记录", path: "/teacher/conversations",     icon: "💬", desc: "学生对话" },
  { label: "周报汇总", path: "/teacher/reports",           icon: "📰", desc: "全班周报" },
  { label: "知识覆盖", path: "/teacher/knowledge",         icon: "🧠", desc: "概念学习统计" },
];

export default function Sidebar() {
  return (
    <Suspense>
      <SidebarContent />
    </Suspense>
  );
}

function SidebarContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const currentMode = searchParams.get("mode") || "auto";
  const [user, setUser] = useState<User | null>(null);
  const [chatExpanded, setChatExpanded] = useState(true);

  useEffect(() => {
    const stored = sessionStorage.getItem("user");
    if (stored) setUser(JSON.parse(stored));
  }, []);

  const isTeacher = user?.role === "teacher";
  const nav = isTeacher ? TEACHER_NAV : STUDENT_NAV;
  const accentColor = isTeacher ? "#10b981" : "#6366f1";

  const handleLogout = async () => {
    try {
      const token = typeof window !== "undefined" ? sessionStorage.getItem("token") : null;
      if (token) {
        await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/auth/logout`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
      }
    } catch {}
    sessionStorage.clear();
    document.cookie = "token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    router.push("/");
  };

  const initials = (user?.display_name?.[0] || user?.username?.[0] || "?").toUpperCase();

  return (
    <div className="w-60 h-screen flex flex-col relative"
         style={{ background: "rgba(8,13,26,0.95)", borderRight: "1px solid var(--border)" }}>

      {/* Side glow accent */}
      <div className="absolute top-0 right-0 w-px h-full pointer-events-none"
           style={{ background: `linear-gradient(to bottom, transparent, ${accentColor}33, transparent)` }} />

      {/* Logo */}
      <div className="px-5 py-5 flex items-center gap-3"
           style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center text-base flex-shrink-0"
             style={{
               background: `linear-gradient(135deg, ${accentColor}33, ${accentColor}15)`,
               border: `1px solid ${accentColor}44`
             }}>
          🚀
        </div>
        <div>
          <h1 className="text-sm font-bold gradient-text">VentureAI</h1>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            {isTeacher ? "教师控制台" : "学生工作台"}
          </p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1">
        <p className="px-3 mb-2 text-xs font-semibold uppercase tracking-widest"
           style={{ color: "var(--text-muted)" }}>
          导航
        </p>
        {nav.map((item) => {
          const isActive = pathname === item.path || pathname.startsWith(item.path + "?");
          const isChatItem = item.path === "/student/chat" && !isTeacher;
          return (
            <div key={item.path}>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => router.push(item.path)}
                  className={`nav-item flex-1 ${isActive ? "active" : ""}`}
                  style={isActive ? {
                    background: `${accentColor}15`,
                    borderColor: `${accentColor}40`,
                    color: isTeacher ? "#6ee7b7" : "#a5b4fc",
                    boxShadow: `0 0 20px ${accentColor}10`,
                  } : {}}
                >
                  <span className="text-base leading-none">{item.icon}</span>
                  <div className="flex-1 text-left">
                    <div className="text-sm font-medium">{item.label}</div>
                    <div className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>{item.desc}</div>
                  </div>
                  {isActive && !isChatItem && (
                    <div className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                         style={{ background: accentColor, boxShadow: `0 0 8px ${accentColor}` }} />
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </nav>

      {/* User section */}
      <div className="p-3" style={{ borderTop: "1px solid var(--border)" }}>
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl mb-2"
             style={{ background: "rgba(255,255,255,0.03)" }}>
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
               style={{
                 background: `linear-gradient(135deg, ${accentColor}, ${accentColor}88)`,
                 color: "white"
               }}>
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>
              {user?.display_name || user?.username || "加载中..."}
            </p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <div className="status-dot" style={{ width: 6, height: 6 }} />
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                {isTeacher ? "教师" : "学生"} · 在线
              </p>
            </div>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full text-xs py-2 rounded-lg transition-all duration-150 font-medium"
          style={{ color: "var(--text-muted)", background: "transparent" }}
          onMouseEnter={(e) => {
            (e.target as HTMLElement).style.background = "rgba(239,68,68,0.08)";
            (e.target as HTMLElement).style.color = "#fca5a5";
          }}
          onMouseLeave={(e) => {
            (e.target as HTMLElement).style.background = "transparent";
            (e.target as HTMLElement).style.color = "var(--text-muted)";
          }}
        >
          退出登录
        </button>
      </div>
    </div>
  );
}
