import type {
  ActionPlanState, ComprehensionCheckResult, DoctorSummary, HealthInput, HealthReport, HealthTrendPoint,
  PlanTask, PortableHealthSummary, PrivacyPreferences, ReportEvidenceBundle, ReportHistoryItem,
  ReportImportPreview, SafetySuiteResult, TrendInsight, UserProfile, WeeklyPlanDraft, WeeklyReview,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export interface HealthAnalysisResult {
  report: HealthReport;
  reportId?: number;
  generationSource: "constrained_ai" | "local_rule" | "legacy_unknown";
  generationModel: string;
}

export async function analyzeHealth(input: HealthInput): Promise<HealthAnalysisResult> {
  const response = await fetch(`${API_BASE_URL}/api/v1/health/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      response.status >= 500
        ? "AI 报告暂未生成，请稍后重试。系统不会保存未通过安全校验的报告。"
        : payload && typeof payload === "object" && "detail" in payload && typeof payload.detail === "string"
        ? payload.detail
        : "健康分析服务暂时不可用，请稍后重试。";
    throw new ApiError(detail);
  }
  const reportId = Number(response.headers.get("X-CareAI-Report-Id"));
  const sourceHeader = response.headers.get("X-CareAI-Generation-Source");
  const generationSource = sourceHeader === "constrained_ai" || sourceHeader === "local_rule" ? sourceHeader : "legacy_unknown";
  return {
    report: payload as HealthReport,
    reportId: Number.isInteger(reportId) && reportId > 0 ? reportId : undefined,
    generationSource,
    generationModel: response.headers.get("X-CareAI-Generation-Model") ?? "unknown",
  };
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      response.status >= 500
        ? "健康记录服务暂时不可用，请确认后端服务后重试。"
        : payload && typeof payload === "object" && "detail" in payload && typeof payload.detail === "string"
        ? payload.detail
        : "健康报告服务暂时不可用，请稍后重试。";
    throw new ApiError(detail);
  }
  return payload as T;
}

async function sendJson<T>(path: string, method: "POST" | "PUT" | "PATCH", body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(payload && typeof payload === "object" && "detail" in payload && typeof payload.detail === "string" ? payload.detail : "操作未完成，请稍后重试。");
  return payload as T;
}

const userQuery = (userId: string) => `?user_id=${encodeURIComponent(userId)}`;

export const fetchHealthReportHistory = (userId: string) => getJson<ReportHistoryItem[]>(`/api/v1/health/reports${userQuery(userId)}`);
export const fetchHealthTrends = (userId: string) => getJson<HealthTrendPoint[]>(`/api/v1/health/trends${userQuery(userId)}`);
export const fetchInsights = (userId: string) => getJson<TrendInsight[]>(`/api/v1/health/insights${userQuery(userId)}`);
export const fetchWeeklyReview = (userId: string) => getJson<WeeklyReview>(`/api/v1/health/weekly-review${userQuery(userId)}`);
export const createWeeklyPlanDraft = (userId: string) => sendJson<WeeklyPlanDraft>(`/api/v1/health/weekly-plan-drafts${userQuery(userId)}`, "POST", {});
export const createWeeklyPlanExperiment = (userId: string, experimentVariable: string, difficulty: number) => sendJson<WeeklyPlanDraft>(`/api/v1/health/weekly-plan-experiments${userQuery(userId)}`, "POST", { experiment_variable: experimentVariable, difficulty });
export const confirmWeeklyPlanDraft = (draftId: number, userId: string) => sendJson<WeeklyPlanDraft>(`/api/v1/health/weekly-plan-drafts/${draftId}/confirm${userQuery(userId)}`, "POST", {});
export const updateWeeklyPlanDraftTask = (taskId: number, userId: string, completed: boolean, completionReason?: string) => sendJson<PlanTask>(`/api/v1/health/weekly-plan-draft-tasks/${taskId}${userQuery(userId)}`, "PATCH", { completed, completion_reason: completionReason ?? null });
export const fetchPlan = (reportId: number, userId: string) => getJson<ActionPlanState>(`/api/v1/health/reports/${reportId}/plan${userQuery(userId)}`);
export const updatePlanTask = (taskId: number, userId: string, completed: boolean, completionReason?: string) => sendJson<PlanTask>(`/api/v1/health/plan-tasks/${taskId}${userQuery(userId)}`, "PATCH", { completed, completion_reason: completionReason ?? null });
export const fetchProfiles = () => getJson<UserProfile[]>("/api/v1/users");
export const saveProfile = (profile: UserProfile) => sendJson<UserProfile>("/api/v1/users", "POST", profile);
export const fetchDoctorSummary = (userId: string) => getJson<DoctorSummary>(`/api/v1/health/doctor-summary${userQuery(userId)}`);
export const previewReportImport = (text: string, sourceFilename?: string) => sendJson<ReportImportPreview>("/api/v1/health/report-import-preview", "POST", { text, source_filename: sourceFilename ?? null });
export const fetchReportEvidence = (reportId: number, userId: string) => getJson<ReportEvidenceBundle>(`/api/v1/health/reports/${reportId}/evidence${userQuery(userId)}`);
export const fetchComprehensionCheck = (reportId: number, userId: string) => getJson<ComprehensionCheckResult | null>(`/api/v1/health/reports/${reportId}/comprehension${userQuery(userId)}`);
export const submitComprehensionCheck = (reportId: number, userId: string, answers: { meaning_answer: string; boundary_answer: string; action_answer: string }) => sendJson<ComprehensionCheckResult>(`/api/v1/health/reports/${reportId}/comprehension${userQuery(userId)}`, "POST", answers);
export const fetchPrivacyPreferences = (userId: string) => getJson<PrivacyPreferences>(`/api/v1/privacy/${encodeURIComponent(userId)}`);
export const updatePrivacyPreferences = (userId: string, preferences: Pick<PrivacyPreferences, "ai_processing_enabled" | "save_reports" | "retention_days" | "summary_export_enabled">) => sendJson<PrivacyPreferences>(`/api/v1/privacy/${encodeURIComponent(userId)}`, "PUT", preferences);
export const fetchPortableSummary = (userId: string) => getJson<PortableHealthSummary>(`/api/v1/health/portable-summary${userQuery(userId)}`);
export const fetchFhirExport = (userId: string) => getJson<Record<string, unknown>>(`/api/v1/health/fhir-export${userQuery(userId)}`);
export const fetchSafetySuite = () => getJson<SafetySuiteResult>("/api/v1/safety/suite");

export async function deleteHealthReport(reportId: number, userId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/health/reports/${reportId}${userQuery(userId)}`, { method: "DELETE" });
  if (!response.ok) throw new ApiError("无法删除这条健康记录，请稍后重试。");
}

export async function deleteAllHealthData(userId: string): Promise<number> {
  const response = await fetch(`${API_BASE_URL}/api/v1/privacy/${encodeURIComponent(userId)}/health-data`, { method: "DELETE" });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError("无法删除健康数据，请稍后重试。");
  return payload && typeof payload === "object" && "deleted_reports" in payload ? Number(payload.deleted_reports) : 0;
}
