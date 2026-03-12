"use client";
import { useState, useEffect } from "react";
import { getTeacherProjects, getProjectReview, setCompetitionDate, createAnnotation } from "@/lib/api";
import { Project, ProjectReview } from "@/lib/types";
import { ProjectListSkeleton } from "@/components/Skeleton";

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
};

function getScoreColor(score: number): string {
  if (score >= 7) return "bg-green-100 text-green-700";
  if (score >= 5) return "bg-amber-100 text-amber-700";
  return "bg-red-100 text-red-700";
}

function getScoreBg(score: number): string {
  if (score >= 7) return "bg-green-500";
  if (score >= 5) return "bg-amber-500";
  return "bg-red-500";
}

export default function TeacherReviewPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [review, setReview] = useState<ProjectReview | null>(null);
  const [loading, setLoading] = useState(false);
  const [listLoading, setListLoading] = useState(true);
  // F2: Competition date
  const [compDate, setCompDate] = useState("");
  const [compDateSaved, setCompDateSaved] = useState(false);
  // F3: Annotation note
  const [noteText, setNoteText] = useState("");
  const [noteSaved, setNoteSaved] = useState(false);

  useEffect(() => {
    getTeacherProjects()
      .then((res) => setProjects(res.projects))
      .catch(console.error)
      .finally(() => setListLoading(false));
  }, []);

  const loadReview = async (projectId: string) => {
    setSelectedId(projectId);
    setLoading(true);
    setCompDate(""); setCompDateSaved(false); setNoteText(""); setNoteSaved(false);
    try {
      const res = await getProjectReview(projectId);
      setReview(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
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
    <div className="flex h-full">
      {/* Project list */}
      <div className="w-80 border-r bg-white overflow-y-auto">
        <div className="p-4 border-b">
          <h2 className="font-semibold text-gray-800">项目审阅</h2>
          <p className="text-xs text-gray-400 mt-1">选择项目查看 Rubric 评估</p>
        </div>
        <div className="divide-y">
          {listLoading ? <ProjectListSkeleton /> : null}
          {projects.map((proj) => (
            <button
              key={proj.project_id}
              onClick={() => loadReview(proj.project_id)}
              className={`w-full text-left p-4 hover:bg-gray-50 transition-colors ${
                selectedId === proj.project_id ? "bg-emerald-50 border-l-4 border-emerald-500" : ""
              }`}
            >
              <h3 className="font-medium text-sm text-gray-800">{proj.name}</h3>
              <p className="text-xs text-gray-400 mt-0.5">{proj.industry}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Review detail - printable area */}
      <div className="flex-1 overflow-y-auto bg-gray-50 p-8">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-400">加载评估报告...</p>
          </div>
        ) : review ? (
          <div className="max-w-4xl mx-auto print-area animate-fadeIn">
            {/* Score summary */}
            <div className="bg-white rounded-xl p-6 shadow-sm mb-6 print-card">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-800 print-title">Rubric 评估报告</h2>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => window.print()}
                    className="no-print flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    ⎙ 打印报告
                  </button>
                  <div className="text-right">
                    <p className="text-3xl font-bold text-gray-800">
                      {review.total_score}
                      <span className="text-lg text-gray-400">/{review.max_score}</span>
                    </p>
                    <p className="text-xs text-gray-400">总分</p>
                  </div>
                </div>
              </div>

              {/* Score bars */}
              <div className="space-y-3">
                {Object.entries(review.rubric_scores).map(([key, item]) => (
                  <div key={key} className="flex items-center gap-3">
                    <span className="w-28 text-sm text-gray-600">{RUBRIC_NAMES[key] || key}</span>
                    <div className="flex-1 bg-gray-100 rounded-full h-3">
                      <div
                        className={`h-3 rounded-full transition-all ${getScoreBg(item.score)}`}
                        style={{ width: `${(item.score / 10) * 100}%` }}
                      ></div>
                    </div>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${getScoreColor(item.score)}`}>
                      {item.score}/10
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Detail cards */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              {Object.entries(review.rubric_scores).map(([key, item]) => (
                <div key={key} className="bg-white rounded-xl p-4 shadow-sm">
                  <div className="flex justify-between items-start mb-2">
                    <h4 className="font-medium text-sm text-gray-800">{RUBRIC_NAMES[key]}</h4>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${getScoreColor(item.score)}`}>
                      {item.score}
                    </span>
                  </div>
                  <p className="text-xs text-gray-600 mb-2">{item.justification}</p>
                  {item.missing.length > 0 && (
                    <div>
                      <p className="text-xs text-red-500 font-medium">缺失证据:</p>
                      <ul className="text-xs text-gray-500 mt-1">
                        {item.missing.map((m, i) => (
                          <li key={i}>- {m}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Evidence trace */}
            {review.evidence_trace.length > 0 && (
              <div className="bg-white rounded-xl p-6 shadow-sm mb-6">
                <h3 className="font-semibold text-gray-700 mb-4">证据链追溯</h3>
                <div className="space-y-3">
                  {review.evidence_trace.map((e, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">{e.rubric}</span>
                      <div>
                        <p className="text-sm text-gray-700 italic">{e.quote}</p>
                        <p className="text-xs text-gray-400 mt-1">来源: {e.source}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Revision suggestions */}
            <div className="bg-white rounded-xl p-6 shadow-sm mb-4">
              <h3 className="font-semibold text-gray-700 mb-4">修改建议</h3>
              <div className="space-y-2">
                {review.revision_suggestions.map((s, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-emerald-50 rounded-lg">
                    <span className="text-emerald-600 font-bold text-sm">{i + 1}</span>
                    <p className="text-sm text-gray-700">{s}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* F2: Competition Date */}
            <div className="bg-white rounded-xl p-5 shadow-sm mb-4 no-print">
              <h3 className="font-semibold text-gray-700 mb-3">竞赛倒计时设置</h3>
              <div className="flex gap-2 items-center">
                <input type="date" value={compDate} onChange={(e) => { setCompDate(e.target.value); setCompDateSaved(false); }}
                       className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm text-gray-700 outline-none" />
                <button onClick={handleSaveCompDate}
                        className="px-4 py-1.5 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 transition-colors">
                  保存
                </button>
                {compDateSaved && <span className="text-xs text-green-600">✓ 已保存，AI 将自动切换倒计时模式</span>}
              </div>
            </div>

            {/* F3: Teacher Annotation */}
            <div className="bg-white rounded-xl p-5 shadow-sm no-print">
              <h3 className="font-semibold text-gray-700 mb-3">教师批注（将注入 AI 对话）</h3>
              <textarea rows={3} placeholder="写下对该项目的指导意见，AI 将在学生下次对话中体现..."
                        value={noteText} onChange={(e) => { setNoteText(e.target.value); setNoteSaved(false); }}
                        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 resize-none outline-none mb-2" />
              <div className="flex items-center gap-3">
                <button onClick={handleSaveNote}
                        className="px-4 py-1.5 bg-amber-500 text-white text-sm rounded-lg hover:bg-amber-600 transition-colors">
                  添加批注
                </button>
                {noteSaved && <span className="text-xs text-green-600">✓ 批注已保存，将在下次 AI 对话中生效</span>}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400">
            <p>选择一个项目查看评估报告</p>
          </div>
        )}
      </div>
    </div>
  );
}
