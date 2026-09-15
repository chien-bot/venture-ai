import { useEffect, useState } from "react";
import { analyzeHealth, ApiError, deleteHealthReport, fetchHealthReportHistory, fetchHealthTrends, fetchInsights, fetchProfiles, fetchWeeklyReview, saveProfile } from "./api";
import { Header, type Page } from "./components/Header";
import { HealthForm } from "./components/HealthForm";
import { HistoryPage } from "./components/HistoryPage";
import { HomePage } from "./components/HomePage";
import { ProfilePage } from "./components/ProfilePage";
import { ReportView } from "./components/ReportView";
import { reportPlanKey } from "./lib/reportStorage";
import type { HealthInput, HealthReport, HealthTrendPoint, ReportHistoryItem, StoredHealthInput, TrendInsight, UserProfile, WeeklyReview } from "./types";

const fallbackProfile: UserProfile = { id: "demo-user", display_name: "健康记忆演示用户", age: null, gender: null, health_goal: null, medical_history: null, long_term_medication: null, allergies: null };

function App() {
  const [activePage, setActivePage] = useState<Page>("home");
  const [report, setReport] = useState<HealthReport | null>(null);
  const [reportInput, setReportInput] = useState<HealthInput | StoredHealthInput | null>(null);
  const [reportBmi, setReportBmi] = useState<number | null>(null);
  const [activeReportId, setActiveReportId] = useState<number | null>(null);
  const [activePlanKey, setActivePlanKey] = useState<string | null>(null);
  const [historyReports, setHistoryReports] = useState<ReportHistoryItem[]>([]);
  const [trendPoints, setTrendPoints] = useState<HealthTrendPoint[]>([]);
  const [insights, setInsights] = useState<TrendInsight[]>([]);
  const [weeklyReview, setWeeklyReview] = useState<WeeklyReview | null>(null);
  const [profiles, setProfiles] = useState<UserProfile[]>([fallbackProfile]);
  const [activeUser, setActiveUser] = useState<UserProfile>(fallbackProfile);
  const [profileSaving, setProfileSaving] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submitHealthData(input: HealthInput) {
    setError(null);
    setIsLoading(true);
    try {
      const result = await analyzeHealth(input);
      setReport(result.report);
      setReportInput(input);
      setReportBmi(Math.round((input.weight / ((input.height / 100) ** 2)) * 10) / 10);
      setActiveReportId(result.reportId ?? null);
      setActivePlanKey(reportPlanKey(result.report, result.reportId));
      setActivePage("report");
      void loadHistory();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "无法连接健康分析服务，请确认后端已启动。" );
    } finally {
      setIsLoading(false);
    }
  }

  async function loadHistory() {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const [reports, trends, nextInsights, review] = await Promise.all([fetchHealthReportHistory(activeUser.id), fetchHealthTrends(activeUser.id), fetchInsights(activeUser.id), fetchWeeklyReview(activeUser.id)]);
      setHistoryReports(reports);
      setTrendPoints(trends);
      setInsights(nextInsights);
      setWeeklyReview(review);
    } catch (caught) {
      setHistoryError(caught instanceof ApiError ? caught.message : "无法读取历史健康报告。");
    } finally {
      setHistoryLoading(false);
    }
  }

  useEffect(() => {
    if (activePage === "history") void loadHistory();
  }, [activePage, activeUser.id]);

  useEffect(() => {
    void (async () => {
      try {
        const availableProfiles = await fetchProfiles();
        if (availableProfiles.length) {
          setProfiles(availableProfiles);
          setActiveUser((current) => availableProfiles.find((profile) => profile.id === current.id) ?? availableProfiles[0]);
        }
      } catch {
        // The health-analysis form will still show its existing connection error when the backend is unavailable.
      }
    })();
  }, []);

  function viewHistoryReport(historyReport: ReportHistoryItem) {
    setReport(historyReport.report);
    setReportInput(historyReport.input);
    setReportBmi(historyReport.assessment.bmi);
    setActiveReportId(historyReport.id);
    setActivePlanKey(reportPlanKey(historyReport.report, historyReport.id));
    setActivePage("report");
  }

  const goToForm = () => { setError(null); setActivePage("form"); };
  const previousReport = activeReportId === null ? null : historyReports.find((item) => item.id < activeReportId) ?? null;
  async function persistProfile(profile: UserProfile) {
    setProfileSaving(true);
    try {
      const saved = await saveProfile(profile);
      setProfiles((current) => current.map((item) => item.id === saved.id ? saved : item));
      setActiveUser(saved);
    } finally { setProfileSaving(false); }
  }

  function createDemoProfile() {
    const id = `demo-${Date.now()}`;
    const profile: UserProfile = { id, display_name: "新的演示用户", age: 22, gender: null, health_goal: null, medical_history: null, long_term_medication: null, allergies: null };
    setProfiles((current) => [...current, profile]);
    setActiveUser(profile);
  }

  function changeActiveUser(userId: string) {
    const selected = profiles.find((profile) => profile.id === userId);
    if (selected) { setActiveUser(selected); setReport(null); setActiveReportId(null); }
  }

  async function removeHistoryReport(reportId: number) {
    await deleteHealthReport(reportId, activeUser.id);
    if (activeReportId === reportId) { setReport(null); setActiveReportId(null); }
    await loadHistory();
  }

  return <div className="min-h-screen bg-[#f8fafb] text-slate-900"><Header activePage={activePage} onNavigate={setActivePage} profiles={profiles} activeUserId={activeUser.id} onUserChange={changeActiveUser} />
    {activePage === "home" && <HomePage onStart={goToForm} />}
    {activePage === "form" && <HealthForm onSubmit={submitHealthData} isLoading={isLoading} error={error} userId={activeUser.id} defaultGoal={activeUser.health_goal} />}
    {activePage === "report" && <ReportView report={report} input={reportInput} bmi={reportBmi} planStorageKey={activePlanKey} previousReport={previousReport} onStart={goToForm} reportId={activeReportId} userId={activeUser.id} />}
    {activePage === "history" && <HistoryPage reports={historyReports} trends={trendPoints} insights={insights} weeklyReview={weeklyReview} user={activeUser} isLoading={historyLoading} error={historyError} onView={viewHistoryReport} onDelete={removeHistoryReport} onRetry={loadHistory} />}
    {activePage === "profile" && <ProfilePage profile={activeUser} onSave={persistProfile} onCreate={createDemoProfile} saving={profileSaving} />}
    <footer className="border-t border-slate-200 bg-white"><div className="mx-auto max-w-6xl px-5 py-6 text-xs leading-5 text-slate-500">CareAI 是 AI 辅助健康风险管理工具，仅提供健康风险提示与健康教育，不诊断疾病，也不替代医生的专业意见。</div></footer>
  </div>;
}

export default App;
