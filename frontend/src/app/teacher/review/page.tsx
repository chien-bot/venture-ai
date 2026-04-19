"use client";
import { useState, useEffect } from "react";
import { getTeacherProjects, getProjectReview, setCompetitionDate, createAnnotation, getCapabilityProfile } from "@/lib/api";
import { Project, ProjectReview } from "@/lib/types";
import { ProjectListSkeleton } from "@/components/Skeleton";
import RubricRadar from "@/components/RubricRadar";

const RUBRIC_NAMES: Record<string, string> = {
  R1: "痛点定义",
  R2: "用户证据",
  R3: "方案可行性",
  R4: "商业模式一致性",
  R5: "市场与竞争",
  R6: "财务逻辑",
  R7: "创新与差异化",
  R8: "团队与执行",
  R9: "表达与材料",
  R10: "合规与社会责任",
  R11: "增长与规模化",
};

function scoreColor(score: number) {
  if (score >= 7) return { color: "#6ee7b7", bg: "rgba(16,185,129,0.15)", bar: "#10b981" };
  if (score >= 5) return { color: "#fcd34d", bg: "rgba(245,158,11,0.15)", bar: "#f59e0b" };
  return { color: "#fca5a5", bg: "rgba(239,68,68,0.15)", bar: "#ef4444" };
}

export default function TeacherReviewPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [review, setReview] = useState<ProjectReview | null>(null);
  const [loading, setLoading] = useState(false);
  const [listLoading, setListLoading] = useState(true);
  const [compDate, setCompDate] = useState("");
  const [compDateSaved, setCompDateSaved] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [noteSaved, setNoteSaved] = useState(false);
  const [expandedRubric, setExpandedRubric] = useState<string | null>(null);
  const [capProfile, setCapProfile] = useState<any>(null);
  const [capLoading, setCapLoading] = useState(false);

  const toggleRubric = (key: string) =>
    setExpandedRubric((prev) => (prev === key ? null : key));

  useEffect(() => {
    getTeacherProjects()
      .then((res) => setProjects(res.projects))
      .catch(console.error)
      .finally(() => setListLoading(false));
  }, []);

  const loadReview = async (projectId: string) => {
    setSelectedId(projectId);
    setLoading(true);
    setCapProfile(null);
    setCompDate(""); setCompDateSaved(false); setNoteText(""); setNoteSaved(false);
    try {
      const res = await getProjectReview(projectId);
      setReview(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
    // Fetch capability profile in background
    setCapLoading(true);
    getCapabilityProfile(projectId)
      .then((res) => setCapProfile(res))
      .catch(() => {})
      .finally(() => setCapLoading(false));
  };

  const handleSaveCompDate = async () => {
    if (!compDate || !selectedId) return;
    try {
      await setCompetitionDate(selectedId, compDate);
      setCompDateSaved(true);
    } catch {}
  };

  const handleSaveNote = async () => {
    if (!noteText.trim() || !selectedId) return;
    try {
      await createAnnotation(selectedId, "", 0, "note", noteText.trim());
      setNoteSaved(true);
      setNoteText("");
    } catch {}
  };

  return (
    <div className="flex h-full" style={{ background: "var(--bg-base)" }}>

      {/* Project list sidebar */}
      <div className="w-72 flex-shrink-0 flex flex-col overflow-hidden"
           style={{ borderRight: "1px solid var(--border)", background: "var(--bg-surface)" }}>
        <div className="p-4 flex-shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
          <h2 className="font-semibold text-sm gradient-text">项目审阅</h2>
          <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>选择项目查看 Rubric 评估</p>
        </div>
        <div className="flex-1 overflow-y-auto">
          {listLoading && <ProjectListSkeleton />}
          {projects.map((proj) => {
            const isSelected = selectedId === proj.project_id;
            return (
              <button
                key={proj.project_id}
                onClick={() => loadReview(proj.project_id)}
                className="w-full text-left px-4 py-3 transition-all duration-150"
                style={{
                  borderBottom: "1px solid var(--border)",
                  background: isSelected ? "rgba(99,102,241,0.1)" : "transparent",
                  borderLeft: isSelected ? "3px solid #6366f1" : "3px solid transparent",
                }}
              >
                <h3 className="text-sm font-medium truncate" style={{ color: isSelected ? "#a5b4fc" : "var(--text-primary)" }}>
                  {proj.name}
                </h3>
                <p className="text-xs mt-0.5 truncate" style={{ color: "var(--text-muted)" }}>{proj.industry}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Review detail */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <p style={{ color: "var(--text-muted)" }}>加载评估报告...</p>
          </div>
        ) : review ? (
          <div className="max-w-3xl mx-auto space-y-4 animate-fadeInUp">

            {/* Rubric — header + collapsible rows in one card */}
            <div className="glass rounded-2xl overflow-hidden">
              {/* Card header */}
              <div className="flex items-center justify-between px-5 py-4"
                   style={{ borderBottom: "1px solid var(--border)" }}>
                <div className="flex items-center gap-2">
                  <span className="badge badge-blue">Rubric</span>
                  <h2 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>评估报告</h2>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => window.print()}
                    className="no-print flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs transition-all"
                    style={{ border: "1px solid var(--border)", color: "var(--text-muted)" }}
                  >
                    ⎙ 打印
                  </button>
                  <div className="text-right">
                    <p className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
                      {review.total_score}
                      <span className="text-sm ml-1" style={{ color: "var(--text-muted)" }}>/{review.max_score}</span>
                    </p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>总分</p>
                  </div>
                </div>
              </div>

              {/* Radar chart */}
              <div className="py-3" style={{ borderBottom: "1px solid var(--border)" }}>
                <RubricRadar data={review.rubric_scores} maxScore={10} />
              </div>

              {/* Collapsible rows */}
              {Object.entries(review.rubric_scores).map(([key, item], idx, arr) => {
                const c = scoreColor(item.score);
                const isOpen = expandedRubric === key;
                const isLast = idx === arr.length - 1;
                return (
                  <div key={key} style={{ borderBottom: isLast ? "none" : "1px solid var(--border)" }}>
                    <button
                      onClick={() => toggleRubric(key)}
                      className="w-full flex items-center gap-3 px-5 py-3 transition-all duration-150 text-left"
                      style={{ background: isOpen ? "rgba(99,102,241,0.06)" : "transparent" }}
                    >
                      <span className="text-xs font-bold w-5 flex-shrink-0" style={{ color: "var(--text-muted)" }}>{key}</span>
                      <span className="text-xs flex-1" style={{ color: "var(--text-primary)" }}>{RUBRIC_NAMES[key]}</span>
                      <div className="flex-1 h-2 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                        <div className="h-2 rounded-full transition-all"
                             style={{ width: `${(item.score / 10) * 100}%`, background: c.bar }} />
                      </div>
                      <span className="text-xs font-bold w-10 text-center px-1.5 py-0.5 rounded-md flex-shrink-0"
                            style={{ background: c.bg, color: c.color }}>
                        {item.score}/10
                      </span>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                           stroke="currentColor" strokeWidth="2.5" className="flex-shrink-0 transition-transform duration-200"
                           style={{ color: "var(--text-muted)", transform: isOpen ? "rotate(180deg)" : "rotate(0deg)" }}>
                        <polyline points="6 9 12 15 18 9" />
                      </svg>
                    </button>

                    {isOpen && (
                      <div className="px-5 pb-4 pt-1 space-y-2" style={{ background: "rgba(99,102,241,0.04)" }}>
                        <p className="text-xs" style={{ color: "var(--text-muted)" }}>{item.justification}</p>
                        {item.missing.length > 0 && (
                          <div className="rounded-lg px-3 py-2" style={{ background: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.15)" }}>
                            <p className="text-xs font-medium mb-1" style={{ color: "#fca5a5" }}>缺失证据</p>
                            <ul className="space-y-0.5">
                              {item.missing.map((m, i) => (
                                <li key={i} className="text-xs" style={{ color: "var(--text-muted)" }}>— {m}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Evidence trace */}
            {review.evidence_trace.length > 0 && (
              <div className="glass rounded-2xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <span className="badge badge-purple">证据链</span>
                  <h3 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>来源追溯</h3>
                </div>
                <div className="space-y-2">
                  {review.evidence_trace.map((e, i) => (
                    <div key={i} className="flex items-start gap-3 px-3 py-2.5 rounded-xl"
                         style={{ background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.15)" }}>
                      <span className="badge badge-blue flex-shrink-0" style={{ fontSize: "0.6rem" }}>{e.rubric}</span>
                      <div>
                        <p className="text-xs italic" style={{ color: "var(--text-primary)" }}>{e.quote}</p>
                        <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>来源：{e.source}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Revision suggestions */}
            <div className="glass rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <span className="badge badge-green">修改建议</span>
              </div>
              <div className="space-y-2">
                {review.revision_suggestions.map((s, i) => (
                  <div key={i} className="flex items-start gap-2 px-3 py-2 rounded-xl"
                       style={{ background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.12)" }}>
                    <span className="text-xs font-bold flex-shrink-0 mt-0.5" style={{ color: "#6ee7b7" }}>{i + 1}</span>
                    <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{s}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Capability Profile */}
            {capLoading && (
              <div className="glass rounded-2xl p-5 text-center">
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>正在生成能力画像...</p>
              </div>
            )}
            {capProfile?.capability_profile && (
              <div className="glass rounded-2xl overflow-hidden">
                <div className="flex items-center justify-between px-5 py-4"
                     style={{ borderBottom: "1px solid var(--border)" }}>
                  <div className="flex items-center gap-2">
                    <span className="badge badge-amber">画像</span>
                    <h3 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>学生能力画像</h3>
                  </div>
                  {capProfile.session_count != null && (
                    <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                      基于 {capProfile.session_count} 轮对话
                    </span>
                  )}
                </div>
                <div className="p-5 space-y-3">
                  {Object.entries(capProfile.capability_profile)
                    .filter(([k]) => k !== "overall_comment")
                    .map(([dim, detail]: [string, any]) => {
                      const score = detail?.score ?? 0;
                      const maxScore = 10;
                      const pct = Math.min((score / maxScore) * 100, 100);
                      const c = scoreColor(score);
                      const DIM_LABELS: Record<string, string> = {
                        empathy: "同理心", ideation: "方案策划", business: "商业建模",
                        execution: "执行力", logic: "逻辑论证", pitching: "表达力", expression: "表达力",
                      };
                      return (
                        <div key={dim}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>
                              {DIM_LABELS[dim] || dim}
                            </span>
                            <span className="text-xs font-bold px-1.5 py-0.5 rounded-md"
                                  style={{ background: c.bg, color: c.color }}>
                              {score}/{maxScore}
                            </span>
                          </div>
                          <div className="h-2 rounded-full mb-1" style={{ background: "rgba(255,255,255,0.06)" }}>
                            <div className="h-2 rounded-full transition-all" style={{ width: `${pct}%`, background: c.bar }} />
                          </div>
                          {detail?.evidence && (
                            <p className="text-xs" style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>
                              <span style={{ color: "#6ee7b7" }}>证据：</span>{detail.evidence}
                            </p>
                          )}
                          {detail?.suggestion && (
                            <p className="text-xs" style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>
                              <span style={{ color: "#fcd34d" }}>建议：</span>{detail.suggestion}
                            </p>
                          )}
                        </div>
                      );
                    })}
                  {capProfile.capability_profile.overall_comment && (
                    <div className="mt-3 px-3 py-2.5 rounded-xl"
                         style={{ background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.15)" }}>
                      <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
                        {capProfile.capability_profile.overall_comment}
                      </p>
                    </div>
                  )}
                  {capProfile.summary && !capProfile.capability_profile.overall_comment && (
                    <div className="mt-2 px-3 py-2.5 rounded-xl"
                         style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                      <p className="text-xs font-semibold mb-1" style={{ color: "var(--text-muted)" }}>AI 综合分析</p>
                      <p className="text-xs whitespace-pre-wrap" style={{ color: "var(--text-secondary)" }}>
                        {capProfile.summary}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Competition Date + Annotation — side by side */}
            <div className="grid grid-cols-2 gap-3 no-print">
              <div className="glass rounded-2xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <span className="badge badge-blue">竞赛设置</span>
                </div>
                <div className="flex gap-2 items-center">
                  <input
                    type="date"
                    value={compDate}
                    onChange={(e) => { setCompDate(e.target.value); setCompDateSaved(false); }}
                    className="flex-1 px-3 py-1.5 rounded-lg text-xs outline-none"
                    style={{ background: "rgba(255,255,255,0.05)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                  />
                  <button
                    onClick={handleSaveCompDate}
                    className="btn-glow px-3 py-1.5 rounded-lg text-xs"
                    style={{ background: "linear-gradient(135deg, #4f46e5, #6366f1)", borderColor: "rgba(99,102,241,0.5)" }}
                  >
                    保存
                  </button>
                </div>
                {compDateSaved && (
                  <p className="text-xs mt-2" style={{ color: "#6ee7b7" }}>✓ 已保存，AI 将自动切换倒计时模式</p>
                )}
              </div>

              <div className="glass rounded-2xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <span className="badge badge-purple">教师批注</span>
                </div>
                <textarea
                  rows={2}
                  placeholder="写下指导意见，AI 将在学生下次对话中体现..."
                  value={noteText}
                  onChange={(e) => { setNoteText(e.target.value); setNoteSaved(false); }}
                  className="w-full px-3 py-2 rounded-lg text-xs resize-none outline-none mb-2"
                  style={{ background: "rgba(255,255,255,0.05)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                />
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleSaveNote}
                    className="btn-glow px-3 py-1.5 rounded-lg text-xs"
                    style={{ background: "linear-gradient(135deg, #d97706, #f59e0b)", borderColor: "rgba(245,158,11,0.5)" }}
                  >
                    添加批注
                  </button>
                  {noteSaved && <span className="text-xs" style={{ color: "#6ee7b7" }}>✓ 批注已保存</span>}
                </div>
              </div>
            </div>

          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-3">
            <div className="w-12 h-12 rounded-2xl flex items-center justify-center"
                 style={{ background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.2)" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="1.5">
                <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5.586a1 1 0 0 1 .707.293l5.414 5.414a1 1 0 0 1 .293.707V19a2 2 0 0 1-2 2z" />
              </svg>
            </div>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>选择左侧项目查看评估报告</p>
          </div>
        )}
      </div>
    </div>
  );
}
