"use client";
import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { ChatMessage } from "@/lib/types";
import { Project } from "@/lib/types";

interface Props {
  messages: ChatMessage[];
  onSend: (msg: string) => void;
  loading: boolean;
  agentLabel: string;
  onUpload?: (file: File) => void;
  uploading?: boolean;
  projects?: Project[];
  selectedProjectId?: string;
  onSelectProject?: (projectId: string) => void;
  onNewProject?: () => void;
}

export default function ChatWindow({ messages, onSend, loading, agentLabel, onUpload, uploading, projects = [], selectedProjectId, onSelectProject, onNewProject }: Props) {
  const [input, setInput] = useState("");
  const [slashMenu, setSlashMenu] = useState(false);
  const [slashFilter, setSlashFilter] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const userScrolledUp = useRef(false);
  const prevMsgCount = useRef(messages.length);

  // Detect if user manually scrolled up
  const handleScroll = () => {
    const el = scrollAreaRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
    userScrolledUp.current = !atBottom;
  };

  useEffect(() => {
    const newMsgAdded = messages.length !== prevMsgCount.current;
    prevMsgCount.current = messages.length;
    // Only auto-scroll when a new message is added (not during streaming tokens)
    // or when user is already at the bottom
    if (newMsgAdded || !userScrolledUp.current) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, loading]);

  // Slash menu: filtered items
  const slashItems = [
    { id: "__new__", label: "/new — 创建新项目", icon: "✨" },
    ...projects.map((p) => ({ id: p.project_id, label: p.name, icon: "📋", active: p.project_id === selectedProjectId })),
  ].filter((item) => {
    if (!slashFilter) return true;
    const q = slashFilter.toLowerCase();
    return item.label.toLowerCase().includes(q) || item.id.toLowerCase().includes(q);
  });

  const handleSlashSelect = (id: string) => {
    setSlashMenu(false);
    setSlashFilter("");
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    if (id === "__new__") {
      onNewProject?.();
    } else {
      onSelectProject?.(id);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (slashMenu) return;
    if (!input.trim() || loading) return;
    userScrolledUp.current = false;
    onSend(input.trim());
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (slashMenu) {
      if (e.key === "Escape") { setSlashMenu(false); setSlashFilter(""); e.preventDefault(); return; }
      if (e.key === "Enter") {
        e.preventDefault();
        if (slashItems.length > 0) handleSlashSelect(slashItems[0].id);
        return;
      }
      return;
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setInput(val);
    // Detect slash command
    if (val === "/" || val.startsWith("/")) {
      setSlashMenu(true);
      setSlashFilter(val.slice(1)); // text after "/"
    } else {
      setSlashMenu(false);
      setSlashFilter("");
    }
    const ta = e.target;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 120) + "px";
  };

  return (
    <div className="flex flex-col h-full" style={{ background: "var(--bg-base)" }}>

      {/* Messages */}
      <div ref={scrollAreaRef} onScroll={handleScroll} className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-3 animate-fadeInUp ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            style={{ animationDelay: `${Math.min(i * 0.03, 0.3)}s` }}
          >
            {/* AI avatar */}
            {msg.role === "assistant" && (
              <div className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-sm font-bold"
                   style={{
                     background: "linear-gradient(135deg, rgba(99,102,241,0.3), rgba(34,211,238,0.2))",
                     border: "1px solid rgba(99,102,241,0.3)",
                     marginTop: 2,
                   }}>
                🤖
              </div>
            )}

            <div className={`max-w-[75%] ${msg.role === "user" ? "items-end" : "items-start"} flex flex-col gap-1`}>
              <div
                className={`px-4 py-3 text-sm leading-relaxed ${
                  msg.role === "user" ? "bubble-user" : "bubble-ai"
                }`}
                style={{ wordBreak: "break-word" }}
              >
                {msg.role === "user" ? (
                  <span className="whitespace-pre-wrap">{msg.content}</span>
                ) : (
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                      strong: ({ children }) => <strong className="font-semibold" style={{ color: "var(--text-primary)" }}>{children}</strong>,
                      h1: ({ children }) => <h1 className="text-base font-bold mb-2 mt-3 first:mt-0" style={{ color: "var(--text-primary)" }}>{children}</h1>,
                      h2: ({ children }) => <h2 className="text-sm font-bold mb-1.5 mt-3 first:mt-0" style={{ color: "var(--text-primary)" }}>{children}</h2>,
                      h3: ({ children }) => <h3 className="text-sm font-semibold mb-1 mt-2 first:mt-0" style={{ color: "var(--text-secondary)" }}>{children}</h3>,
                      ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-0.5">{children}</ul>,
                      ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-0.5">{children}</ol>,
                      li: ({ children }) => <li className="text-sm">{children}</li>,
                      code: ({ children, className }) => {
                        const isBlock = className?.includes("language-");
                        return isBlock ? (
                          <code className="block text-xs p-2 rounded-lg my-2 font-mono overflow-x-auto" style={{ background: "rgba(0,0,0,0.3)", color: "#a5b4fc" }}>{children}</code>
                        ) : (
                          <code className="text-xs px-1.5 py-0.5 rounded font-mono" style={{ background: "rgba(99,102,241,0.15)", color: "#a5b4fc" }}>{children}</code>
                        );
                      },
                      hr: () => <hr className="my-3" style={{ borderColor: "var(--border)" }} />,
                      blockquote: ({ children }) => <blockquote className="pl-3 my-2 text-xs italic" style={{ borderLeft: "2px solid var(--border)", color: "var(--text-muted)" }}>{children}</blockquote>,
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                )}
              </div>
            {/* Fix tasks from H1-H15 rules */}
            {msg.role === "assistant" && msg.fix_tasks && msg.fix_tasks.length > 0 && (
              <div className="mt-2 space-y-1.5 max-w-[75%]">
                <p className="text-xs font-semibold px-1" style={{ color: "#fcd34d" }}>
                  ⚠ 超图检测到以下需修正的问题：
                </p>
                {msg.fix_tasks.map((ft, fi) => (
                  <div key={fi} className="flex items-start gap-2 px-3 py-2 rounded-xl text-xs"
                       style={{
                         background: ft.severity === "high" ? "rgba(239,68,68,0.08)" : "rgba(245,158,11,0.08)",
                         border: `1px solid ${ft.severity === "high" ? "rgba(239,68,68,0.25)" : "rgba(245,158,11,0.25)"}`,
                       }}>
                    <span className="flex-shrink-0 text-xs font-bold px-1.5 py-0.5 rounded"
                          style={{ background: ft.severity === "high" ? "rgba(239,68,68,0.2)" : "rgba(245,158,11,0.2)", color: ft.severity === "high" ? "#fca5a5" : "#fcd34d" }}>
                      {ft.rule_id}
                    </span>
                    <span style={{ color: "var(--text-secondary)" }}>{ft.fix_task}</span>
                  </div>
                ))}
              </div>
            )}
            </div>

            {/* User avatar */}
            {msg.role === "user" && (
              <div className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold text-white"
                   style={{
                     background: "linear-gradient(135deg, #6366f1, #4f46e5)",
                     marginTop: 2,
                   }}>
                我
              </div>
            )}
          </div>
        ))}

        {/* Typing indicator */}
        {loading && (
          <div className="flex gap-3 justify-start animate-fadeInUp">
            <div className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-sm"
                 style={{
                   background: "linear-gradient(135deg, rgba(99,102,241,0.3), rgba(34,211,238,0.2))",
                   border: "1px solid rgba(99,102,241,0.3)",
                   marginTop: 2,
                 }}>
              🤖
            </div>
            <div className="bubble-ai px-4 py-3 flex items-center gap-1.5">
              <div className="typing-dot" />
              <div className="typing-dot" />
              <div className="typing-dot" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="px-4 pb-4 pt-2 relative"
           style={{ borderTop: "1px solid var(--border)", background: "rgba(8,13,26,0.8)" }}>
        {/* Slash command menu */}
        {slashMenu && (
          <div className="absolute left-4 right-4 bottom-full mb-2 rounded-2xl overflow-hidden z-50"
               style={{ background: "rgba(10,14,28,0.98)", border: "1px solid rgba(99,102,241,0.3)", boxShadow: "0 -8px 32px rgba(0,0,0,0.4)" }}>
            <div className="px-3 py-2 flex items-center gap-2"
                 style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
              <span className="text-xs font-semibold" style={{ color: "#a5b4fc" }}>/</span>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                选择项目或输入项目名过滤 · Enter 确认 · Esc 关闭
              </span>
            </div>
            <div className="max-h-56 overflow-y-auto py-1">
              {slashItems.length === 0 ? (
                <div className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>无匹配项目</div>
              ) : slashItems.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleSlashSelect(item.id)}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-left transition-all"
                  style={{ background: "transparent" }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(99,102,241,0.1)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <span className="text-base flex-shrink-0">{item.icon}</span>
                  <div className="flex-1 min-w-0">
                    <span className="text-sm" style={{ color: item.id === "__new__" ? "#a5b4fc" : "var(--text-primary)" }}>
                      {item.label}
                    </span>
                    {(item as any).active && (
                      <span className="ml-2 text-xs px-1.5 py-0.5 rounded"
                            style={{ background: "rgba(99,102,241,0.2)", color: "#a5b4fc" }}>当前</span>
                    )}
                  </div>
                  {item.id !== "__new__" && (
                    <span className="text-xs flex-shrink-0" style={{ color: "var(--text-muted)" }}>
                      切换
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}
        <form onSubmit={handleSubmit}>
          <div className="flex items-end gap-2 rounded-2xl p-2"
               style={{
                 background: "rgba(255,255,255,0.04)",
                 border: "1px solid var(--border)",
                 transition: "border-color 0.2s, box-shadow 0.2s",
               }}
               onFocus={() => {}}
          >
            {onUpload && (
              <>
                <input
                  id="chat-file-input"
                  type="file"
                  className="hidden"
                  accept=".pdf,.txt,.md,.csv,.png,.jpg,.jpeg"
                  onChange={(e) => { if (e.target.files?.[0]) onUpload(e.target.files[0]); e.target.value = ""; }}
                />
                <button
                  type="button"
                  disabled={uploading}
                  onClick={() => document.getElementById("chat-file-input")?.click()}
                  className="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center transition-all disabled:opacity-30"
                  style={{ background: "rgba(255,255,255,0.06)", border: "1px solid var(--border)", color: "var(--text-muted)" }}
                  title="上传文件"
                >
                  {uploading ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="animate-spin"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
                  ) : (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
                  )}
                </button>
              </>
            )}
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="输入你的想法... （Enter 发送，Shift+Enter 换行）"
              disabled={loading}
              rows={1}
              className="flex-1 bg-transparent text-sm outline-none resize-none py-1.5 px-2"
              style={{
                color: "var(--text-primary)",
                maxHeight: "120px",
                lineHeight: "1.6",
              }}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="btn-glow flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
          <p className="text-center mt-1.5 text-xs" style={{ color: "var(--text-muted)" }}>
            AI 回复仅供参考，请结合实际情况判断
          </p>
        </form>
      </div>
    </div>
  );
}
