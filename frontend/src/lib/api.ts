const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function handleSessionExpired() {
  if (typeof window !== "undefined") {
    sessionStorage.clear();
    document.cookie = "token=; path=/; max-age=0";
    // Avoid redirect loop if already on login page
    if (window.location.pathname !== "/") {
      window.location.href = "/?expired=1";
    }
  }
}

async function request(path: string, options: RequestInit = {}) {
  const token = typeof window !== "undefined" ? sessionStorage.getItem("token") : null;
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (res.status === 401 && !path.includes("/auth/")) {
    handleSessionExpired();
    throw new Error("登录已过期，请重新登录");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "请求失败" }));
    throw new Error(err.detail || "请求失败");
  }
  return res.json();
}

// Auth
export async function login(username: string, password: string, role: string = "student") {
  return request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password, role }),
  });
}

export async function refreshToken() {
  const data = await request("/api/auth/refresh", { method: "POST" });
  if (typeof window !== "undefined") {
    sessionStorage.setItem("token", data.token);
    sessionStorage.setItem("user", JSON.stringify(data));
    document.cookie = `token=${data.token}; path=/`;
  }
  return data;
}

export async function logout() {
  try {
    await request("/api/auth/logout", { method: "POST" });
  } catch {
    // Even if the API call fails, clear local state
  }
  if (typeof window !== "undefined") {
    sessionStorage.clear();
    document.cookie = "token=; path=/; max-age=0";
  }
}

export async function register(username: string, password: string, displayName: string = "", classId: string = "") {
  return request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password, display_name: displayName, class_id: classId }),
  });
}

// Chat
export async function startChat(agentType: string = "coach", projectId: string = "") {
  const params = new URLSearchParams({ agent_type: agentType });
  if (projectId) params.set("project_id", projectId);
  return request(`/api/chat/start?${params}`, { method: "POST" });
}

export async function sendMessage(sessionId: string, projectId: string, message: string, agentType: string = "coach") {
  return request("/api/chat/message", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      project_id: projectId,
      message,
      agent_type: agentType,
    }),
  });
}

export async function getChatHistory(sessionId: string) {
  return request(`/api/chat/history/${sessionId}`);
}

// Streaming chat
export async function sendMessageStream(
  sessionId: string,
  projectId: string,
  message: string,
  agentType: string = "coach",
  onToken: (text: string) => void,
  onMeta: (data: any) => void,
  onDone: (data: any) => void,
  signal?: AbortSignal,
) {
  const token = typeof window !== "undefined" ? sessionStorage.getItem("token") : null;
  const res = await fetch(`${API_BASE}/api/chat/message/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      session_id: sessionId,
      project_id: projectId,
      message,
      agent_type: agentType,
    }),
    signal,
  });

  if (res.status === 401) {
    handleSessionExpired();
    throw new Error("登录已过期，请重新登录");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "请求失败" }));
    throw new Error(err.detail || "请求失败");
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const jsonStr = line.slice(6).trim();
      if (!jsonStr) continue;
      try {
        const data = JSON.parse(jsonStr);
        if (data.type === "token") {
          const clean = data.content
            .replace(/<!--\s*(?:SCORES|RUBRIC_FULL|RUBRIC|CAPABILITY_PROFILE)\s*:[\s\S]*?-->/gi, '')
            .replace(/<!--\s*(?:SCORES|RUBRIC_FULL|RUBRIC|CAPABILITY_PROFILE)\s*:[\s\S]*/gi, '');
          if (!clean) continue;
          onToken(clean);
        } else if (data.type === "meta") {
          onMeta(data);
        } else if (data.type === "done") {
          onDone(data);
        }
      } catch {
        // skip malformed JSON
      }
    }
  }
}

// Mock Investor Defense
export async function startDefense(projectId: string, investorStyle: string = "aggressive", totalQuestions: number = 7) {
  return request("/api/chat/defense/start", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId, investor_style: investorStyle, total_questions: totalQuestions }),
  });
}

export async function sendDefenseMessage(
  sessionId: string, projectId: string, message: string,
  investorStyle: string, currentRound: number, totalQuestions: number
) {
  return request("/api/chat/defense/message", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId, project_id: projectId, message,
      investor_style: investorStyle, current_round: currentRound, total_questions: totalQuestions,
    }),
  });
}

// Projects
export async function listProjects(ownerId?: string) {
  const query = ownerId ? `?owner_id=${ownerId}` : "";
  return request(`/api/projects/${query}`);
}

export async function getProject(projectId: string) {
  return request(`/api/projects/${projectId}`);
}

export async function createProject(name: string, industry: string, description: string) {
  return request("/api/projects/", {
    method: "POST",
    body: JSON.stringify({ name, industry, description }),
  });
}

// Intake Form (前置采集层)
export async function getIntakeSchema() {
  return request("/api/chat/intake/schema");
}

export async function submitIntake(sessionId: string, projectId: string, filledData: Record<string, string>) {
  return request("/api/chat/intake/submit", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, project_id: projectId, filled_data: filledData }),
  });
}

export async function checkIntakeGaps(filledData: Record<string, string>) {
  return request("/api/chat/intake/gaps", {
    method: "POST",
    body: JSON.stringify({ filled_data: filledData }),
  });
}

// Knowledge Cards
export async function searchKnowledgeCards(params: {
  q?: string; card_type?: string; stage?: string;
  dimension?: string; rubric?: string; industry?: string; limit?: number;
} = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  }
  return request(`/api/knowledge/cards?${qs}`);
}

export async function getKnowledgeCard(cardId: string) {
  return request(`/api/knowledge/cards/${cardId}`);
}

export async function getCardsForRubric(rubricId: string, dimension?: string) {
  const qs = dimension ? `?dimension=${dimension}` : "";
  return request(`/api/knowledge/cards/rubric/${rubricId}${qs}`);
}

export async function generateKnowledgeCards() {
  return request("/api/knowledge/cards/generate", { method: "POST" });
}

export async function getKnowledgeStats() {
  return request("/api/knowledge/stats");
}

// Teacher
export async function getDashboard() {
  return request("/api/teacher/dashboard");
}

export async function getTeacherProjects() {
  return request("/api/teacher/projects");
}

export async function getProjectReview(projectId: string) {
  return request(`/api/teacher/project/${projectId}/review`);
}

export async function getCapabilityProfile(projectId: string) {
  return request(`/api/teacher/project/${projectId}/capability-profile`);
}

export async function getProjectConversations(projectId: string) {
  return request(`/api/teacher/project/${projectId}/conversations`);
}

// Hypergraph insights (teacher dashboard)
export async function getHypergraphInsights() {
  return request("/api/graph/hypergraph/insights");
}

// Tools: Timeline / Benchmark / Pitch Check / Interview Analyze
export async function getTimeline(projectId: string) {
  return request(`/api/tools/timeline/${projectId}`);
}

export async function getBenchmark(projectId: string) {
  return request(`/api/tools/benchmark/${projectId}`);
}

export async function checkPitch(projectId: string, outline: string) {
  return request("/api/tools/pitch-check", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId, outline }),
  });
}

export async function analyzeInterview(projectId: string, interviewText: string) {
  return request("/api/tools/interview-analyze", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId, interview_text: interviewText }),
  });
}

export async function getInterviewHistory(projectId: string) {
  return request(`/api/tools/interview-history/${projectId}`);
}

export async function getPitchHistory(projectId: string) {
  return request(`/api/tools/pitch-history/${projectId}`);
}

// F4: Evidence Dashboard
export async function getEvidenceDashboard(projectId: string) {
  return request(`/api/tools/evidence/${projectId}`);
}

// F5: Session Rating
export async function submitRating(sessionId: string, projectId: string, rating: number, comment: string = "") {
  return request("/api/chat/rating", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, project_id: projectId, rating, comment }),
  });
}

export async function getTeacherRatings() {
  return request("/api/teacher/ratings");
}

// F2: Competition Countdown
export async function setCompetitionDate(projectId: string, competitionDate: string) {
  return request(`/api/teacher/project/${projectId}/competition-date`, {
    method: "POST",
    body: JSON.stringify({ competition_date: competitionDate }),
  });
}

// F3: Teacher Annotations
export async function createAnnotation(
  projectId: string, sessionId: string, messageIdx: number,
  action: string, noteText: string = ""
) {
  return request("/api/teacher/annotation", {
    method: "POST",
    body: JSON.stringify({
      project_id: projectId, session_id: sessionId,
      message_idx: messageIdx, action, note_text: noteText,
    }),
  });
}

export async function getProjectAnnotations(projectId: string) {
  return request(`/api/teacher/project/${projectId}/annotations`);
}

// Teacher Interventions
export async function createIntervention(
  projectId: string, triggerKeyword: string, instruction: string, priority: number = 1
) {
  return request("/api/teacher/interventions", {
    method: "POST",
    body: JSON.stringify({
      project_id: projectId, trigger_keyword: triggerKeyword,
      instruction, priority,
    }),
  });
}

export async function getInterventions(projectId: string) {
  return request(`/api/teacher/interventions/${projectId}`);
}

export async function deleteIntervention(interventionId: string) {
  return request(`/api/teacher/interventions/${interventionId}`, { method: "DELETE" });
}

// Session Memory
export async function getLatestSession(projectId: string) {
  return request(`/api/chat/latest-session/${projectId}`);
}

// Student chat history
export async function getMySessions() {
  return request(`/api/chat/my-sessions`);
}

export async function deleteSession(sessionId: string) {
  return request(`/api/chat/session/${sessionId}`, { method: "DELETE" });
}


// File Upload
export async function uploadFile(file: File, projectId: string, sessionId: string) {
  const token = typeof window !== "undefined" ? sessionStorage.getItem("token") : null;
  const formData = new FormData();
  formData.append("file", file);
  formData.append("project_id", projectId);
  formData.append("session_id", sessionId);
  const res = await fetch(`${API_BASE}/api/upload/file`, {
    method: "POST",
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: formData,
  });
  if (!res.ok) throw new Error("上传失败");
  return res.json();
}

// Weekly Report
export async function getWeeklyReport(projectId: string, weekStart?: string) {
  const q = weekStart ? `?week_start=${weekStart}` : "";
  return request(`/api/tools/weekly-report/${projectId}${q}`);
}

export async function getAllWeeklyReports(weekStart?: string) {
  const q = weekStart ? `?week_start=${weekStart}` : "";
  return request(`/api/tools/weekly-reports/all${q}`);
}

// Peer Review
export async function getMyReviewAssignments(userId: string) {
  return request(`/api/peer-review/assignments/${userId}`);
}

export async function getAvailableProjectsForReview(userId: string) {
  return request(`/api/peer-review/available?user_id=${userId}`);
}

export async function assignReview(reviewerId: string, projectId: string) {
  return request("/api/peer-review/assign", {
    method: "POST",
    body: JSON.stringify({ reviewer_id: reviewerId, project_id: projectId }),
  });
}

export async function submitPeerReview(
  assignmentId: string, projectId: string,
  scores: Record<string, number>, comments: Record<string, string>,
  overallComment: string
) {
  return request("/api/peer-review/submit", {
    method: "POST",
    body: JSON.stringify({
      assignment_id: assignmentId, project_id: projectId,
      scores, comments, overall_comment: overallComment,
    }),
  });
}

export async function getReceivedReviews(projectId: string) {
  return request(`/api/peer-review/received/${projectId}`);
}

// Teacher: Knowledge Coverage
export async function getKnowledgeCoverage() {
  return request("/api/teacher/knowledge-coverage");
}

// Learning Path
export async function getLearningPath(projectId: string) {
  return request(`/api/tools/learning-path/${projectId}`);
}

export async function generateLearningPath(projectId: string) {
  return request(`/api/tools/learning-path/${projectId}/generate`, { method: "POST" });
}

export async function updateTaskStatus(taskId: string, status: string) {
  return request(`/api/tools/learning-path/task/${taskId}/status`, {
    method: "POST",
    body: JSON.stringify({ status }),
  });
}

// Team
export async function getTeamMembers(projectId: string) {
  return request(`/api/projects/${projectId}/team`);
}

export async function addTeamMember(projectId: string, username: string) {
  return request(`/api/projects/${projectId}/team`, {
    method: "POST",
    body: JSON.stringify({ username }),
  });
}

export async function removeTeamMember(projectId: string, userId: string) {
  return request(`/api/projects/${projectId}/team/${userId}`, { method: "DELETE" });
}

// Playbooks (创业范式库)
export async function listPlaybooks() {
  return request("/api/playbooks/");
}

export async function getPlaybook(playbookId: string) {
  return request(`/api/playbooks/${playbookId}`);
}

export async function matchPlaybook(description: string, industry: string = "", bizModel: string = "", techs: string[] = []) {
  return request("/api/playbooks/match", {
    method: "POST",
    body: JSON.stringify({ description, industry, biz_model: bizModel, techs }),
  });
}

export async function clusterPlaybooks() {
  return request("/api/playbooks/cluster", { method: "POST" });
}
