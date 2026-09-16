export type RiskLevel = "normal" | "attention" | "high_attention";

export interface HealthInput {
  age: number;
  gender: "male" | "female" | "other";
  height: number;
  weight: number;
  blood_pressure?: string;
  blood_glucose?: number;
  sleep_hours: number;
  exercise_frequency: number;
  user_id?: string;
  recorded_at?: string;
  source?: string;
  health_goal?: string;
}

export interface HealthReport {
  summary: string;
  risk_level: RiskLevel;
  key_risks: string[];
  recommendations: string[];
  action_plan: string[];
  safety_notice: string;
}

export interface StoredHealthInput {
  age: number;
  gender: "male" | "female" | "other";
  height_cm: number;
  weight_kg: number;
  systolic_bp: number | null;
  diastolic_bp: number | null;
  fasting_blood_glucose_mmol_l: number | null;
  sleep_hours: number;
  exercise_days_per_week: number;
  user_id: string;
  recorded_at: string;
  source: string;
  health_goal: string | null;
}

export interface RuleAssessment {
  bmi: number;
  overall_level: RiskLevel;
}

export interface ReportHistoryItem {
  id: number;
  created_at: string;
  input: StoredHealthInput;
  assessment: RuleAssessment;
  report: HealthReport;
  generation_source: "constrained_ai" | "local_rule" | "legacy_unknown";
  generation_model: string;
  agent_version: string;
  rule_version: string;
}

export interface HealthTrendPoint {
  report_id: number;
  created_at: string;
  bmi: number;
  sleep_hours: number;
  exercise_frequency: number;
  risk_level: RiskLevel;
}

export interface UserProfile {
  id: string;
  display_name: string;
  age: number | null;
  gender: "male" | "female" | "other" | null;
  health_goal: string | null;
  medical_history: string | null;
  long_term_medication: string | null;
  allergies: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface PlanTask {
  id: number;
  day_number: number;
  content: string;
  completed: boolean;
  completion_reason: string | null;
  completed_at: string | null;
}

export interface ActionPlanState {
  id: number;
  report_id: number;
  user_id: string;
  goal: string;
  week_start: string;
  created_at: string;
  tasks: PlanTask[];
}

export interface TrendInsight {
  category: string;
  level: RiskLevel;
  title: string;
  explanation: string;
  next_step: string;
  data_points: number;
}

export interface WeeklyReview {
  user_id: string;
  week_start: string | null;
  completed_tasks: number;
  total_tasks: number;
  completion_rate: number | null;
  summary: string;
}

export interface WeeklyPlanDraft {
  id: number;
  user_id: string;
  goal: string;
  summary: string;
  adjustment_reason: string;
  created_at: string;
  confirmed_at: string | null;
  tasks: PlanTask[];
  safety_notice: string;
  version: number;
  previous_draft_id: number | null;
  experiment_variable: string;
  difficulty: number;
  experiment_snapshot: Record<string, string | number>;
}

export interface ComprehensionFeedback {
  question: string;
  correct: boolean;
  explanation: string;
}

export interface ComprehensionCheckResult {
  report_id: number;
  user_id: string;
  score: number;
  passed: boolean;
  attempts: number;
  feedback: ComprehensionFeedback[];
  submitted_at: string;
}

export interface EvidenceReference {
  title: string;
  url: string | null;
  use: string;
}

export interface EvidenceCard {
  id: string;
  kind: "rule" | "ai_explanation" | "recommendation";
  title: string;
  source_fields: string[];
  rule_version: string;
  decision_owner: "local_rule" | "constrained_ai" | "legacy_unknown";
  explanation: string;
  uncertainty: string;
  references: EvidenceReference[];
}

export interface ReportEvidenceBundle {
  report_id: number;
  generated_at: string;
  rule_version: string;
  agent_version: string;
  model: string;
  cards: EvidenceCard[];
  safety_notice: string;
}

export interface PrivacyPreferences {
  user_id: string;
  ai_processing_enabled: boolean;
  save_reports: boolean;
  retention_days: number;
  summary_export_enabled: boolean;
  ai_data_scope: string;
  updated_at: string | null;
}

export interface PortableObservation {
  code: string;
  display: string;
  value: string | number;
  unit: string | null;
  recorded_at: string;
  source: string;
}

export interface PortableHealthSummary {
  user: UserProfile;
  observations: PortableObservation[];
  trend_insights: TrendInsight[];
  weekly_review: WeeklyReview;
  provenance: {
    schema_version: string;
    generated_at: string;
    rule_version: string;
    source_report_ids: number[];
    generator: string;
    boundary: string;
  };
  safety_notice: string;
}

export interface SafetyTestCase {
  id: string;
  title: string;
  expected: string;
  passed: boolean;
  detail: string;
}

export interface SafetySuiteResult {
  suite_version: string;
  checked_at: string;
  passed: boolean;
  pass_count: number;
  total_count: number;
  cases: SafetyTestCase[];
}

export interface DoctorSummary {
  user: UserProfile;
  generated_at: string;
  record_count: number;
  trend_insights: TrendInsight[];
  weekly_review: WeeklyReview;
  safety_notice: string;
}

export interface ReportImportPreview {
  extraction_status: "needs_confirmation";
  source_filename: string | null;
  recorded_at: string | null;
  age: number | null;
  gender: "male" | "female" | "other" | null;
  height_cm: number | null;
  weight_kg: number | null;
  systolic_bp: number | null;
  diastolic_bp: number | null;
  fasting_blood_glucose_mmol_l: number | null;
  sleep_hours: number | null;
  exercise_days_per_week: number | null;
  extracted_fields: string[];
  notices: string[];
}
