"""FastAPI entry point for the CareAI explainable health-action prototype."""

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.database import (
    confirm_weekly_plan_draft, delete_all_health_data, delete_health_report, get_action_plan_for_report,
    get_health_report, get_health_trends, get_latest_comprehension_check, get_latest_weekly_plan_draft,
    get_privacy_preferences, is_plan_task_unlocked,
    get_user_profile, get_weekly_review, list_health_reports, list_user_profiles, purge_expired_reports,
    save_comprehension_check, save_health_report, save_privacy_preferences, save_user_profile,
    save_weekly_plan_draft, update_plan_task, update_weekly_plan_draft_task,
)
from app.schemas import (
    ActionPlanState,
    ComprehensionCheckRequest,
    ComprehensionCheckResult,
    DoctorSummary,
    HealthDataInput,
    HealthReport,
    HealthTrendPoint,
    LLMTestRequest,
    LLMTestResponse,
    PlanTask,
    PlanTaskUpdate,
    PortableHealthSummary,
    PrivacyPreferences,
    PrivacyPreferencesUpdate,
    ReportImportPreview,
    ReportImportPreviewRequest,
    ReportHistoryItem,
    ReportEvidenceBundle,
    RuleAssessment,
    SafetySuiteResult,
    TrendInsight,
    UserProfile,
    UserProfileInput,
    WeeklyPlanDraft,
    WeeklyPlanExperimentRequest,
    WeeklyReview,
)
from app.services.evidence_cards import build_report_evidence
from app.services.health_report_agent import AGENT_VERSION, HealthReportAgentError, generate_health_report, generate_local_rule_report
from app.services.llm import LLMServiceError, chat, get_active_model_name
from app.services.risk_rules import assess_health_risk
from app.services.risk_config import RULES_VERSION, get_rule_information
from app.services.report_import import preview_report_import
from app.services.portable_export import build_fhir_demo_bundle, build_portable_summary
from app.services.safety_lab import run_safety_suite
from app.services.trend_insights import generate_trend_insights
from app.services.weekly_plan_agent import build_single_variable_experiment, generate_weekly_plan

app = FastAPI(
    title="CareAI Explainable Health Action API",
    version="0.2.0",
    description="Explainable health education and habit support only. Not a disease diagnosis or a replacement for clinicians.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
    expose_headers=["X-CareAI-Report-Id", "X-CareAI-Generation-Source", "X-CareAI-Generation-Model"],
)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "careai-backend"}


@app.post("/api/v1/health/risk-assessment", response_model=RuleAssessment, tags=["risk"])
async def risk_assessment(data: HealthDataInput) -> RuleAssessment:
    """Run local deterministic BMI, sleep, and exercise risk checks."""
    return assess_health_risk(data)


@app.get("/api/v1/health/rule-info", tags=["risk"])
async def health_rule_information() -> dict:
    """Expose the versioned, non-diagnostic rule configuration for product explanation and review."""
    return get_rule_information()


@app.post("/api/v1/health/report-import-preview", response_model=ReportImportPreview, tags=["import"])
async def report_import_preview(payload: ReportImportPreviewRequest) -> ReportImportPreview:
    """Extract a draft from user-supplied report text; the client must ask for confirmation."""
    return preview_report_import(payload)


@app.post("/api/v1/llm/test", response_model=LLMTestResponse, tags=["llm"])
async def llm_test(payload: LLMTestRequest) -> LLMTestResponse:
    """Simple connectivity test for the configured school MaaS API."""
    try:
        content = await chat([{"role": "user", "content": payload.prompt}], temperature=0)
        return LLMTestResponse(model=get_active_model_name(), content=content)
    except LLMServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@app.post("/api/v1/health/analyze", response_model=HealthReport, tags=["risk"])
async def analyze_health(data: HealthDataInput, response: Response) -> HealthReport:
    """Return the fixed Health Report Agent output from deterministic rules and MaaS writing."""
    if get_user_profile(data.user_id) is None:
        save_user_profile(UserProfileInput(
            id=data.user_id, display_name=data.user_id, age=data.age, gender=data.gender, health_goal=data.health_goal
        ))
    preferences = get_privacy_preferences(data.user_id)
    assessment = assess_health_risk(data)
    try:
        if preferences.ai_processing_enabled:
            report = await generate_health_report(assessment)
            generation_source = "constrained_ai"
            try:
                generation_model = get_active_model_name()
            except LLMServiceError:
                generation_model = "constrained AI test double"
        else:
            report = generate_local_rule_report(assessment)
            generation_source = "local_rule"
            generation_model = "CareAI deterministic local rules"
        response.headers["X-CareAI-Generation-Source"] = generation_source
        response.headers["X-CareAI-Generation-Model"] = generation_model
        if preferences.save_reports:
            saved_report = save_health_report(
                data, assessment, report, generation_source, generation_model, AGENT_VERSION, RULES_VERSION
            )
            response.headers["X-CareAI-Report-Id"] = str(saved_report.id)
            purge_expired_reports(data.user_id, preferences.retention_days)
        return report
    except HealthReportAgentError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@app.get("/api/v1/users", response_model=list[UserProfile], tags=["profiles"])
async def user_profiles() -> list[UserProfile]:
    """List local demo profiles. Production authentication is outside this prototype."""
    return list_user_profiles()


@app.post("/api/v1/users", response_model=UserProfile, tags=["profiles"])
async def upsert_user_profile(data: UserProfileInput) -> UserProfile:
    return save_user_profile(data)


@app.get("/api/v1/users/{user_id}", response_model=UserProfile, tags=["profiles"])
async def user_profile(user_id: str) -> UserProfile:
    profile = get_user_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health profile not found")
    return profile


@app.get("/api/v1/health/reports", response_model=list[ReportHistoryItem], tags=["history"])
async def health_report_history(user_id: str = "demo-user", limit: int = 20) -> list[ReportHistoryItem]:
    """Return saved health reports for one profile, newest first."""
    preferences = get_privacy_preferences(user_id)
    purge_expired_reports(user_id, preferences.retention_days)
    return list_health_reports(user_id, limit)


@app.get("/api/v1/health/reports/{report_id}", response_model=ReportHistoryItem, tags=["history"])
async def health_report_detail(report_id: int, user_id: str = "demo-user") -> ReportHistoryItem:
    """Return one saved report together with its input metrics and rule output."""
    report = get_health_report(report_id, user_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health report not found")
    return report


@app.get("/api/v1/health/reports/{report_id}/evidence", response_model=ReportEvidenceBundle, tags=["evidence"])
async def report_evidence(report_id: int, user_id: str = "demo-user") -> ReportEvidenceBundle:
    report = get_health_report(report_id, user_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health report not found")
    return build_report_evidence(report)


@app.post("/api/v1/health/reports/{report_id}/comprehension", response_model=ComprehensionCheckResult, tags=["understanding"])
async def submit_comprehension_check(
    report_id: int, payload: ComprehensionCheckRequest, user_id: str = "demo-user"
) -> ComprehensionCheckResult:
    result = save_comprehension_check(report_id, user_id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health report not found")
    return result


@app.get("/api/v1/health/reports/{report_id}/comprehension", response_model=ComprehensionCheckResult | None, tags=["understanding"])
async def latest_comprehension_check(report_id: int, user_id: str = "demo-user") -> ComprehensionCheckResult | None:
    if get_health_report(report_id, user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health report not found")
    return get_latest_comprehension_check(report_id, user_id)


@app.get("/api/v1/health/trends", response_model=list[HealthTrendPoint], tags=["history"])
async def health_report_trends(user_id: str = "demo-user", limit: int = 12) -> list[HealthTrendPoint]:
    """Return chronological BMI, sleep, exercise, and overall-risk trend points."""
    return get_health_trends(user_id, limit)


@app.delete("/api/v1/health/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["history"])
async def remove_health_report(report_id: int, user_id: str = "demo-user") -> None:
    if not delete_health_report(report_id, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health report not found")


@app.get("/api/v1/health/insights", response_model=list[TrendInsight], tags=["history"])
async def health_memory_insights(user_id: str = "demo-user") -> list[TrendInsight]:
    return generate_trend_insights(list_health_reports(user_id, 100))


@app.get("/api/v1/health/reports/{report_id}/plan", response_model=ActionPlanState, tags=["plans"])
async def report_action_plan(report_id: int, user_id: str = "demo-user") -> ActionPlanState:
    plan = get_action_plan_for_report(report_id, user_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action plan not found")
    return plan


@app.patch("/api/v1/health/plan-tasks/{task_id}", response_model=PlanTask, tags=["plans"])
async def set_plan_task(task_id: int, data: PlanTaskUpdate, user_id: str = "demo-user") -> PlanTask:
    if not get_privacy_preferences(user_id).save_reports:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Plan saving is disabled in privacy settings")
    if not is_plan_task_unlocked(task_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Complete the report understanding check before tracking this action plan",
        )
    task = update_plan_task(task_id, user_id, data.completed, data.completion_reason)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan task not found")
    return task


@app.get("/api/v1/health/weekly-review", response_model=WeeklyReview, tags=["plans"])
async def weekly_review(user_id: str = "demo-user") -> WeeklyReview:
    return get_weekly_review(user_id)


@app.post("/api/v1/health/weekly-plan-drafts", response_model=WeeklyPlanDraft, tags=["plans"])
async def create_weekly_plan_draft(user_id: str = "demo-user") -> WeeklyPlanDraft:
    profile = get_user_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health profile not found")
    review = get_weekly_review(user_id)
    insights = generate_trend_insights(list_health_reports(user_id, 100))
    preferences = get_privacy_preferences(user_id)
    if not preferences.save_reports:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Plan saving is disabled in privacy settings")
    previous = get_latest_weekly_plan_draft(user_id)
    try:
        if preferences.ai_processing_enabled:
            content = await generate_weekly_plan(profile.health_goal or "建立可持续的健康习惯", review, insights)
            snapshot: dict[str, str | int] = {}
            difficulty = 2
        else:
            local = build_single_variable_experiment(
                profile.health_goal or "建立可持续的健康习惯", review, "任务难度", 2, previous
            )
            content, snapshot, difficulty = local, local.snapshot, local.difficulty
    except HealthReportAgentError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return save_weekly_plan_draft(
        user_id, profile.health_goal or "建立可持续的健康习惯", content.summary,
        content.adjustment_reason, content.action_plan,
        "保持当前计划" if preferences.ai_processing_enabled else "任务难度", difficulty, snapshot,
    )


@app.post("/api/v1/health/weekly-plan-experiments", response_model=WeeklyPlanDraft, tags=["plans"])
async def create_weekly_plan_experiment(
    payload: WeeklyPlanExperimentRequest, user_id: str = "demo-user"
) -> WeeklyPlanDraft:
    profile = get_user_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health profile not found")
    if not get_privacy_preferences(user_id).save_reports:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Plan saving is disabled in privacy settings")
    review = get_weekly_review(user_id)
    previous = get_latest_weekly_plan_draft(user_id)
    content = build_single_variable_experiment(
        profile.health_goal or "建立可持续的健康习惯", review,
        payload.experiment_variable, payload.difficulty, previous,
    )
    return save_weekly_plan_draft(
        user_id, profile.health_goal or "建立可持续的健康习惯", content.summary,
        content.adjustment_reason, content.action_plan, payload.experiment_variable,
        content.difficulty, content.snapshot,
    )


@app.post("/api/v1/health/weekly-plan-drafts/{draft_id}/confirm", response_model=WeeklyPlanDraft, tags=["plans"])
async def confirm_weekly_plan(draft_id: int, user_id: str = "demo-user") -> WeeklyPlanDraft:
    if not get_privacy_preferences(user_id).save_reports:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Plan saving is disabled in privacy settings")
    draft = confirm_weekly_plan_draft(draft_id, user_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Weekly plan draft not found")
    return draft


@app.patch("/api/v1/health/weekly-plan-draft-tasks/{task_id}", response_model=PlanTask, tags=["plans"])
async def set_weekly_plan_task(task_id: int, data: PlanTaskUpdate, user_id: str = "demo-user") -> PlanTask:
    if not get_privacy_preferences(user_id).save_reports:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Plan saving is disabled in privacy settings")
    task = update_weekly_plan_draft_task(task_id, user_id, data.completed, data.completion_reason)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Confirmed weekly plan task not found")
    return task


@app.get("/api/v1/health/doctor-summary", response_model=DoctorSummary, tags=["sharing"])
async def doctor_summary(user_id: str = "demo-user") -> DoctorSummary:
    profile = get_user_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health profile not found")
    reports = list_health_reports(user_id, 100)
    from datetime import datetime, timezone
    return DoctorSummary(user=profile, generated_at=datetime.now(timezone.utc).isoformat(), record_count=len(reports),
        trend_insights=generate_trend_insights(reports), weekly_review=get_weekly_review(user_id),
        safety_notice="本摘要由用户记录与非诊断性规则生成，仅供用户与专业人员沟通参考，不能替代医疗诊断或处方。")


@app.get("/api/v1/privacy/{user_id}", response_model=PrivacyPreferences, tags=["privacy"])
async def privacy_preferences(user_id: str) -> PrivacyPreferences:
    if get_user_profile(user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health profile not found")
    return get_privacy_preferences(user_id)


@app.put("/api/v1/privacy/{user_id}", response_model=PrivacyPreferences, tags=["privacy"])
async def update_privacy_preferences(user_id: str, payload: PrivacyPreferencesUpdate) -> PrivacyPreferences:
    if get_user_profile(user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health profile not found")
    return save_privacy_preferences(user_id, payload)


@app.delete("/api/v1/privacy/{user_id}/health-data", tags=["privacy"])
async def remove_all_health_data(user_id: str) -> dict[str, int | str]:
    if get_user_profile(user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health profile not found")
    deleted = delete_all_health_data(user_id)
    return {"status": "deleted", "deleted_reports": deleted}


def _portable_summary_for(user_id: str) -> PortableHealthSummary:
    profile = get_user_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health profile not found")
    preferences = get_privacy_preferences(user_id)
    if not preferences.summary_export_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Summary export is disabled in privacy settings")
    reports = list_health_reports(user_id, 100)
    return build_portable_summary(
        profile, reports, generate_trend_insights(reports), get_weekly_review(user_id)
    )


@app.get("/api/v1/health/portable-summary", response_model=PortableHealthSummary, tags=["sharing"])
async def portable_summary(user_id: str = "demo-user") -> PortableHealthSummary:
    return _portable_summary_for(user_id)


@app.get("/api/v1/health/fhir-export", tags=["sharing"])
async def fhir_export(user_id: str = "demo-user") -> dict:
    return build_fhir_demo_bundle(_portable_summary_for(user_id))


@app.get("/api/v1/safety/suite", response_model=SafetySuiteResult, tags=["safety"])
async def safety_suite() -> SafetySuiteResult:
    return run_safety_suite()
