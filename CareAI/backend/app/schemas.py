"""Request and response schemas for the CareAI health-memory prototype."""

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class RiskLevel(str, Enum):
    NORMAL = "normal"
    ATTENTION = "attention"
    HIGH_ATTENTION = "high_attention"


class HealthDataInput(BaseModel):
    """Minimum adult health data accepted by the MVP.

    This data supports health-risk education only; it is not a diagnostic record.
    """

    age: int = Field(..., ge=18, le=120, description="Age in years; MVP supports adults only")
    gender: Gender
    height_cm: float = Field(..., ge=100, le=250, description="Height in centimetres")
    weight_kg: float = Field(..., ge=20, le=350, description="Weight in kilograms")
    systolic_bp: int | None = Field(None, ge=60, le=260, description="Systolic blood pressure, mmHg")
    diastolic_bp: int | None = Field(None, ge=30, le=160, description="Diastolic blood pressure, mmHg")
    fasting_blood_glucose_mmol_l: float | None = Field(
        None,
        ge=1.0,
        le=40.0,
        description="Optional fasting blood glucose, mmol/L. Provide only when measured after at least 8 hours without caloric intake.",
    )
    sleep_hours: float = Field(..., ge=0, le=24, description="Average sleep hours per night")
    exercise_days_per_week: int = Field(..., ge=0, le=7, description="Days with exercise per week")
    user_id: str = Field("demo-user", min_length=1, max_length=64, description="Local demo profile identifier")
    recorded_at: date = Field(default_factory=date.today, description="The date the measurements were taken")
    source: str = Field("manual", min_length=1, max_length=40, description="manual, report_import, or demo_device")
    health_goal: str | None = Field(None, max_length=120, description="Optional primary lifestyle goal")

    @model_validator(mode="before")
    @classmethod
    def normalize_common_client_fields(cls, value: object) -> object:
        """Accept the concise MVP field names used by the client test payload.

        Data is normalized at the API boundary so the rule engine only handles one
        internal representation.
        """
        if not isinstance(value, dict):
            return value
        data = value.copy()
        aliases = {
            "height": "height_cm",
            "weight": "weight_kg",
            "exercise_frequency": "exercise_days_per_week",
            "blood_glucose": "fasting_blood_glucose_mmol_l",
        }
        for client_name, internal_name in aliases.items():
            if internal_name not in data and client_name in data:
                data[internal_name] = data[client_name]

        blood_pressure = data.get("blood_pressure")
        if blood_pressure is not None and "systolic_bp" not in data and "diastolic_bp" not in data:
            try:
                systolic, diastolic = str(blood_pressure).strip().split("/", maxsplit=1)
                data["systolic_bp"] = int(systolic.strip())
                data["diastolic_bp"] = int(diastolic.strip())
            except (TypeError, ValueError) as exc:
                raise ValueError("blood_pressure must use format systolic/diastolic, e.g. 120/80") from exc
        return data

    @model_validator(mode="after")
    def validate_blood_pressure_pair(self) -> "HealthDataInput":
        if (self.systolic_bp is None) != (self.diastolic_bp is None):
            raise ValueError("systolic_bp and diastolic_bp must be provided together")
        if (
            self.systolic_bp is not None
            and self.diastolic_bp is not None
            and self.systolic_bp <= self.diastolic_bp
        ):
            raise ValueError("systolic_bp must be greater than diastolic_bp")
        return self

    @property
    def bmi(self) -> float:
        return round(self.weight_kg / ((self.height_cm / 100) ** 2), 1)


class RiskItem(BaseModel):
    category: str
    level: RiskLevel
    source: str = Field("user_input", description="The user-input field(s) that produced this risk item")
    title: str
    reason: str
    recommendation: str


class RuleAssessment(BaseModel):
    bmi: float
    overall_level: RiskLevel
    risks: list[RiskItem]
    safety_notice: str


class LLMTestRequest(BaseModel):
    prompt: str = Field("请回复：CareAI MaaS API 连接成功。", min_length=1, max_length=500)


class LLMTestResponse(BaseModel):
    model: str
    content: str


class HealthReport(BaseModel):
    """Fixed, non-diagnostic output of the Health Report Agent."""

    summary: str
    risk_level: RiskLevel
    key_risks: list[str]
    recommendations: list[str]
    action_plan: list[str]
    safety_notice: str


class ReportHistoryItem(BaseModel):
    id: int
    created_at: str
    input: HealthDataInput
    assessment: RuleAssessment
    report: HealthReport
    generation_source: Literal["constrained_ai", "local_rule", "legacy_unknown"] = "legacy_unknown"
    generation_model: str = "unknown"
    agent_version: str = "unknown"
    rule_version: str = "unknown"


class HealthTrendPoint(BaseModel):
    report_id: int
    created_at: str
    bmi: float
    sleep_hours: float
    exercise_frequency: int
    risk_level: RiskLevel


class UserProfile(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=60)
    age: int | None = Field(None, ge=18, le=120)
    gender: Gender | None = None
    health_goal: str | None = Field(None, max_length=120)
    medical_history: str | None = Field(None, max_length=1000)
    long_term_medication: str | None = Field(None, max_length=1000)
    allergies: str | None = Field(None, max_length=1000)
    created_at: str | None = None
    updated_at: str | None = None


class UserProfileInput(BaseModel):
    id: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    display_name: str = Field(..., min_length=1, max_length=60)
    age: int | None = Field(None, ge=18, le=120)
    gender: Gender | None = None
    health_goal: str | None = Field(None, max_length=120)
    medical_history: str | None = Field(None, max_length=1000)
    long_term_medication: str | None = Field(None, max_length=1000)
    allergies: str | None = Field(None, max_length=1000)


class PlanTask(BaseModel):
    id: int
    day_number: int
    content: str
    completed: bool
    completion_reason: str | None = None
    completed_at: str | None = None


class ActionPlanState(BaseModel):
    id: int
    report_id: int
    user_id: str
    goal: str
    week_start: str
    created_at: str
    tasks: list[PlanTask]


class PlanTaskUpdate(BaseModel):
    completed: bool
    completion_reason: str | None = Field(None, max_length=240)


class ReportImportPreviewRequest(BaseModel):
    """Text copied from a health report or read from a local TXT file."""

    text: str = Field(..., min_length=1, max_length=12000)
    source_filename: str | None = Field(None, max_length=180)


class ReportImportPreview(BaseModel):
    extraction_status: str = "needs_confirmation"
    source_filename: str | None = None
    recorded_at: date | None = None
    age: int | None = None
    gender: Gender | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    systolic_bp: int | None = None
    diastolic_bp: int | None = None
    fasting_blood_glucose_mmol_l: float | None = None
    sleep_hours: float | None = None
    exercise_days_per_week: int | None = None
    extracted_fields: list[str]
    notices: list[str]


class TrendInsight(BaseModel):
    category: str
    level: RiskLevel
    title: str
    explanation: str
    next_step: str
    data_points: int


class WeeklyReview(BaseModel):
    user_id: str
    week_start: str | None = None
    completed_tasks: int
    total_tasks: int
    completion_rate: int | None = None
    summary: str


class WeeklyPlanDraft(BaseModel):
    id: int
    user_id: str
    goal: str
    summary: str
    adjustment_reason: str
    created_at: str
    confirmed_at: str | None = None
    tasks: list[PlanTask]
    safety_notice: str
    version: int = 1
    previous_draft_id: int | None = None
    experiment_variable: str = "保持当前计划"
    difficulty: int = Field(2, ge=1, le=5)
    experiment_snapshot: dict[str, str | int] = Field(default_factory=dict)


class WeeklyPlanExperimentRequest(BaseModel):
    experiment_variable: Literal["提醒时间", "行动时长", "行动频率", "任务难度"] = "任务难度"
    difficulty: int = Field(2, ge=1, le=5)


class ComprehensionCheckRequest(BaseModel):
    meaning_answer: Literal["health_education", "medical_diagnosis", "guaranteed_outcome"]
    boundary_answer: Literal["repeat_and_seek_help", "change_medicine", "ignore_all_results"]
    action_answer: Literal["choose_one_small_step", "complete_everything_today", "wait_for_diagnosis"]


class ComprehensionFeedback(BaseModel):
    question: str
    correct: bool
    explanation: str


class ComprehensionCheckResult(BaseModel):
    report_id: int
    user_id: str
    score: int
    passed: bool
    attempts: int
    feedback: list[ComprehensionFeedback]
    submitted_at: str


class EvidenceReference(BaseModel):
    title: str
    url: str | None = None
    use: str


class EvidenceCard(BaseModel):
    id: str
    kind: Literal["rule", "ai_explanation", "recommendation"]
    title: str
    source_fields: list[str]
    rule_version: str
    decision_owner: Literal["local_rule", "constrained_ai", "legacy_unknown"]
    explanation: str
    uncertainty: str
    references: list[EvidenceReference]


class ReportEvidenceBundle(BaseModel):
    report_id: int
    generated_at: str
    rule_version: str
    agent_version: str
    model: str
    cards: list[EvidenceCard]
    safety_notice: str


class PrivacyPreferences(BaseModel):
    user_id: str
    ai_processing_enabled: bool = True
    save_reports: bool = True
    retention_days: int = Field(365, ge=0, le=3650)
    summary_export_enabled: bool = True
    ai_data_scope: str = "仅发送规则已经确定的关注项，不发送姓名、完整档案或原始健康记录。"
    updated_at: str | None = None


class PrivacyPreferencesUpdate(BaseModel):
    ai_processing_enabled: bool
    save_reports: bool
    retention_days: int = Field(..., ge=0, le=3650)
    summary_export_enabled: bool


class PortableObservation(BaseModel):
    code: str
    display: str
    value: float | int | str
    unit: str | None = None
    recorded_at: str
    source: str


class ProvenanceMetadata(BaseModel):
    schema_version: str
    generated_at: str
    rule_version: str
    source_report_ids: list[int]
    generator: str
    boundary: str


class PortableHealthSummary(BaseModel):
    user: UserProfile
    observations: list[PortableObservation]
    trend_insights: list[TrendInsight]
    weekly_review: WeeklyReview
    provenance: ProvenanceMetadata
    safety_notice: str


class SafetyTestCase(BaseModel):
    id: str
    title: str
    expected: str
    passed: bool
    detail: str


class SafetySuiteResult(BaseModel):
    suite_version: str
    checked_at: str
    passed: bool
    pass_count: int
    total_count: int
    cases: list[SafetyTestCase]


class DoctorSummary(BaseModel):
    user: UserProfile
    generated_at: str
    record_count: int
    trend_insights: list[TrendInsight]
    weekly_review: WeeklyReview
    safety_notice: str
