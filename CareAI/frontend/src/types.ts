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
