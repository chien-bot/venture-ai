"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, register } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [tab, setTab] = useState<"login" | "register">("login");
  const [role, setRole] = useState<"student" | "teacher">("student");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [classId, setClassId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await login(username, password, role);
      sessionStorage.setItem("token", res.token);
      sessionStorage.setItem("user", JSON.stringify(res));
      document.cookie = `token=${res.token}; path=/`;
      router.push(role === "teacher" ? "/teacher/dashboard" : "/student/chat");
    } catch (err: any) {
      setError(err.message || "登录失败");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await register(username, password, displayName, classId);
      sessionStorage.setItem("token", res.token);
      sessionStorage.setItem("user", JSON.stringify(res));
      document.cookie = `token=${res.token}; path=/`;
      router.push("/student/chat");
    } catch (err: any) {
      setError(err.message || "注册失败");
    } finally {
      setLoading(false);
    }
  };

  const isTeacher = role === "teacher";

  return (
    <div className="min-h-screen relative flex items-center justify-center p-4 overflow-hidden"
         style={{ background: "var(--bg-base)" }}>

      {/* Aurora background orbs */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="animate-aurora absolute w-[600px] h-[600px] rounded-full top-[-200px] left-[-200px]"
             style={{ background: "radial-gradient(circle, rgba(99,102,241,0.3) 0%, transparent 70%)" }} />
        <div className="animate-aurora absolute w-[500px] h-[500px] rounded-full bottom-[-150px] right-[-150px]"
             style={{ background: "radial-gradient(circle, rgba(34,211,238,0.2) 0%, transparent 70%)", animationDelay: "3s" }} />
        <div className="animate-aurora absolute w-[400px] h-[400px] rounded-full top-[40%] right-[20%]"
             style={{ background: "radial-gradient(circle, rgba(167,139,250,0.15) 0%, transparent 70%)", animationDelay: "6s" }} />
      </div>

      {/* Grid overlay */}
      <div className="absolute inset-0 pointer-events-none"
           style={{
             backgroundImage: "linear-gradient(rgba(99,102,241,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,0.03) 1px, transparent 1px)",
             backgroundSize: "60px 60px"
           }} />

      {/* Login card */}
      <div className="relative w-full max-w-md animate-fadeInScale">
        <div className="glass rounded-2xl p-8"
             style={{ boxShadow: "0 0 60px rgba(99,102,241,0.12), 0 0 0 1px rgba(255,255,255,0.06)" }}>

          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4 animate-float"
                 style={{ background: "linear-gradient(135deg, rgba(99,102,241,0.3), rgba(34,211,238,0.2))", border: "1px solid rgba(99,102,241,0.4)" }}>
              <span className="text-3xl">🚀</span>
            </div>
            <h1 className="text-3xl font-bold gradient-text mb-1">VentureAI</h1>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>创新创业教学智能体</p>
          </div>

          {/* Login / Register tab */}
          <div className="flex rounded-xl p-1 mb-4"
               style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)" }}>
            {(["login", "register"] as const).map((t) => (
              <button key={t} type="button" onClick={() => { setTab(t); setError(""); }}
                      className="flex-1 py-2 rounded-lg text-sm font-medium transition-all duration-200"
                      style={tab === t ? {
                        background: "linear-gradient(135deg, rgba(99,102,241,0.3), rgba(99,102,241,0.15))",
                        color: "#a5b4fc",
                        border: "1px solid rgba(99,102,241,0.4)",
                      } : { color: "var(--text-muted)" }}>
                {t === "login" ? "登录" : "注册新账号"}
              </button>
            ))}
          </div>

          {/* Role selector — only for login */}
          {tab === "login" && (
          <div className="flex rounded-xl p-1 mb-6"
               style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)" }}>
            {(["student", "teacher"] as const).map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRole(r)}
                className="flex-1 py-2.5 rounded-lg text-sm font-medium transition-all duration-200"
                style={role === r ? {
                  background: r === "teacher"
                    ? "linear-gradient(135deg, rgba(16,185,129,0.3), rgba(16,185,129,0.15))"
                    : "linear-gradient(135deg, rgba(99,102,241,0.3), rgba(99,102,241,0.15))",
                  color: r === "teacher" ? "#6ee7b7" : "#a5b4fc",
                  border: `1px solid ${r === "teacher" ? "rgba(16,185,129,0.4)" : "rgba(99,102,241,0.4)"}`,
                  boxShadow: r === "teacher" ? "0 0 20px rgba(16,185,129,0.1)" : "0 0 20px rgba(99,102,241,0.15)"
                } : { color: "var(--text-muted)" }}
              >
                {r === "student" ? "🎓 学生端" : "📊 教师端"}
              </button>
            ))}
          </div>
          )}

          {/* Login Form */}
          {tab === "login" && (
          <form onSubmit={handleLogin} className="space-y-4">
            {[
              { label: "用户名", type: "text", value: username, setter: setUsername, placeholder: isTeacher ? "teacher01" : "student01" },
              { label: "密码",   type: "password", value: password, setter: setPassword, placeholder: "123456" },
            ].map(({ label, type, value, setter, placeholder }) => (
              <div key={label}>
                <label className="block text-xs font-semibold mb-1.5 uppercase tracking-wider"
                       style={{ color: "var(--text-muted)" }}>
                  {label}
                </label>
                <input
                  type={type}
                  value={value}
                  onChange={(e) => setter(e.target.value)}
                  placeholder={placeholder}
                  className="w-full px-4 py-3 rounded-xl text-sm outline-none transition-all duration-200"
                  style={{
                    background: "rgba(255,255,255,0.04)",
                    border: "1px solid var(--border)",
                    color: "var(--text-primary)",
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = "rgba(99,102,241,0.5)";
                    e.target.style.boxShadow = "0 0 0 3px rgba(99,102,241,0.1)";
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = "var(--border)";
                    e.target.style.boxShadow = "none";
                  }}
                />
              </div>
            ))}

            {error && (
              <div className="flex items-center gap-2 px-4 py-3 rounded-xl text-sm"
                   style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", color: "#fca5a5" }}>
                <span>⚠</span>
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !username || !password}
              className="btn-glow w-full py-3 rounded-xl text-sm disabled:opacity-40 disabled:cursor-not-allowed mt-2"
              style={isTeacher ? {
                background: "linear-gradient(135deg, #059669, #10b981)",
                borderColor: "rgba(16,185,129,0.5)"
              } : {}}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin inline-block" />
                  登录中...
                </span>
              ) : (
                `以${isTeacher ? "教师" : "学生"}身份登录 →`
              )}
            </button>
          </form>
          )}

          {/* Register Form */}
          {tab === "register" && (
          <form onSubmit={handleRegister} className="space-y-4">
            {[
              { label: "用户名 *", id: "reg-username", type: "text", value: username, setter: setUsername, placeholder: "至少3个字符" },
              { label: "密码 *",   id: "reg-password", type: "password", value: password, setter: setPassword, placeholder: "至少4个字符" },
              { label: "显示名称（可选）", id: "reg-display", type: "text", value: displayName, setter: setDisplayName, placeholder: "你的名字" },
              { label: "班级代码（可选）", id: "reg-class", type: "text", value: classId, setter: setClassId, placeholder: "由教师提供" },
            ].map(({ label, id, type, value, setter, placeholder }) => (
              <div key={id}>
                <label htmlFor={id} className="block text-xs font-semibold mb-1.5 uppercase tracking-wider"
                       style={{ color: "var(--text-muted)" }}>
                  {label}
                </label>
                <input
                  id={id}
                  type={type}
                  value={value}
                  onChange={(e) => setter(e.target.value)}
                  placeholder={placeholder}
                  className="w-full px-4 py-3 rounded-xl text-sm outline-none transition-all duration-200"
                  style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                  onFocus={(e) => { e.target.style.borderColor = "rgba(99,102,241,0.5)"; e.target.style.boxShadow = "0 0 0 3px rgba(99,102,241,0.1)"; }}
                  onBlur={(e) => { e.target.style.borderColor = "var(--border)"; e.target.style.boxShadow = "none"; }}
                />
              </div>
            ))}
            {error && (
              <div className="flex items-center gap-2 px-4 py-3 rounded-xl text-sm"
                   style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", color: "#fca5a5" }}>
                <span>⚠</span>
                <span>{error}</span>
              </div>
            )}
            <button
              type="submit"
              disabled={loading || !username || !password}
              className="btn-glow w-full py-3 rounded-xl text-sm disabled:opacity-40 disabled:cursor-not-allowed mt-2"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin inline-block" />
                  注册中...
                </span>
              ) : "注册并开始使用 →"}
            </button>
          </form>
          )}

          {/* Demo accounts — only on login tab */}
          {tab === "login" && (
          <div className="mt-6 px-4 py-3 rounded-xl text-xs space-y-1"
               style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
            <p className="font-semibold mb-1" style={{ color: "var(--text-secondary)" }}>测试账号</p>
            <p style={{ color: "var(--text-muted)" }}>学生：student01 / student02 / student03</p>
            <p style={{ color: "var(--text-muted)" }}>教师：teacher01 &nbsp;|&nbsp; 密码均为 123456</p>
          </div>
          )}
        </div>

        {/* Bottom glow line */}
        <div className="absolute -bottom-px left-1/2 -translate-x-1/2 w-2/3 h-px"
             style={{ background: "linear-gradient(90deg, transparent, rgba(99,102,241,0.6), transparent)" }} />
      </div>
    </div>
  );
}
