export interface User {
  user_id: string;
  username: string;
  role: "student" | "teacher";
  display_name?: string;
  token: string;
}

export interface FixTask {
  rule_id: string;
  severity: "high" | "medium";
  fix_task: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  fix_tasks?: FixTask[];
}

export interface Scores {
  empathy: number;
  ideation: number;
  business: number;
  execution: number;
  pitching: number;
}

export interface Project {
  project_id: string;
  name: string;
  industry: string;
  description: string;
  stage: string;
  owner_id: string;
  scores: Scores;
  diagnosis: string[];
  project_type?: string;
  created_at: string;
}

export interface ClassSummary {
  class_id: string;
  total_students: number;
  total_projects: number;
  avg_scores: Scores;
  top_mistakes: Array<{
    rank: number;
    mistake: string;
    frequency: string;
    affected_rubric: string;
  }>;
  high_risk_projects: Array<{
    project_id: string;
    name: string;
    risk: string;
    score: number;
  }>;
  suggestions: string[];
}

export interface RubricScore {
  score: number;
  justification: string;
  missing: string[];
}

export interface ProjectReview {
  project_id: string;
  rubric_scores: Record<string, RubricScore>;
  total_score: number;
  max_score: number;
  evidence_trace: Array<{ rubric: string; quote: string; source: string }>;
  revision_suggestions: string[];
}

// F6-adv: Team
export interface TeamMember {
  user_id: string;
  username?: string;
  display_name?: string;
  role: "owner" | "member";
  joined_at: string;
}

// F4-adv: Peer Review
export interface ReviewAssignment {
  assignment_id: string;
  reviewer_id: string;
  project_id: string;
  project_name?: string;
  status: "pending" | "completed";
  assigned_by: string;
  created_at: string;
}

export interface PeerReview {
  review_id: string;
  project_id: string;
  scores: Record<string, number>;
  comments: Record<string, string>;
  overall_comment: string;
  created_at: string;
}

// F5-adv: Learning Path
export interface LearningTask {
  task_id: string;
  project_id: string;
  dimension: string;
  title: string;
  description: string;
  status: "pending" | "completed";
  completed_at?: string;
}

// F2-adv: Weekly Report
export interface WeeklyReport {
  project_id: string;
  project_name?: string;
  week_start: string;
  week_end: string;
  highlights: string[];
  score_changes: Record<string, { from: number; to: number; delta: number }>;
  action_items: string[];
  stats: { total_sessions: number; sessions: number; messages: number };
}
