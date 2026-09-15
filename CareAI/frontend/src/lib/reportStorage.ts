import type { HealthReport } from "../types";

/** Produces a stable browser-local key for a report's 7-day action-plan state. */
export function reportPlanKey(report: HealthReport, savedReportId?: number): string {
  if (savedReportId) return `careai.action-plan.report-${savedReportId}`;
  const source = `${report.summary}|${report.action_plan.join("|")}`;
  let hash = 0;
  for (let index = 0; index < source.length; index += 1) {
    hash = (hash * 31 + source.charCodeAt(index)) | 0;
  }
  return `careai.action-plan.generated-${Math.abs(hash)}`;
}

export function readCompletedDays(storageKey: string): number[] {
  try {
    const value = window.localStorage.getItem(storageKey);
    const parsed: unknown = value ? JSON.parse(value) : [];
    return Array.isArray(parsed) ? parsed.filter((day): day is number => Number.isInteger(day) && day >= 0 && day < 7) : [];
  } catch {
    return [];
  }
}

export function saveCompletedDays(storageKey: string, completedDays: number[]): void {
  try {
    window.localStorage.setItem(storageKey, JSON.stringify(completedDays));
  } catch {
    // The report remains usable when a browser blocks local storage.
  }
}
