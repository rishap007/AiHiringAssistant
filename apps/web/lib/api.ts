const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "")

export interface Job {
  id: string
  title: string
  description: string
  agent_id: string | null
  reachout_agent_id: string | null
  created_at: string
}

export interface Candidate {
  id: string
  job_id: string | null
  name: string
  phone_e164: string | null
  email: string | null
  source: string
  source_ref: string | null
  headline: string | null
  created_at: string
}

export interface Agent {
  id: string
  hunar_agent_id: string
  purpose: "screening" | "reachout" | string
  name: string
  language: string
  voice_persona: string
  created_at: string
}

export interface Call {
  id: string
  hunar_call_id: string
  agent_id: string
  candidate_id: string
  job_id: string | null
  status: string
  lifecycle_status: string
  result_json: Record<string, unknown> | null
  recording_url: string | null
  duration_seconds: number | null
  engagement_status: string | null
  request_id: string | null
  created_at: string
  updated_at: string
}

export interface SearchRun {
  id: string
  job_id: string
  provider: string
  query_json: Record<string, unknown>
  result_count: number
  created_at: string
}

export interface JobCall {
  id: string
  hunar_call_id: string
  candidate_name: string
  status: string
  result_json: Record<string, unknown> | null
  recording_url: string | null
  duration_seconds: number | null
}

export interface ReachoutDashboardCandidate extends Candidate {
  call_status: string | null
  result_json: Record<string, unknown> | null
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `API request failed (${response.status})`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const getJobs = () => apiFetch<Job[]>("/jobs")

export const createJob = (input: { title: string; description: string }) =>
  apiFetch<Job>("/jobs", { method: "POST", body: JSON.stringify(input) })

export const updateJob = (job_id: string, input: { jd_raw_text: string }) =>
  apiFetch<Job>(`/jobs/${encodeURIComponent(job_id)}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  })

export const addCandidate = (job_id: string, input: { name: string; phone_e164?: string | null }) =>
  apiFetch<Candidate>(`/jobs/${encodeURIComponent(job_id)}/candidates`, {
    method: "POST",
    body: JSON.stringify(input),
  })

export const getJobCandidates = (job_id: string) =>
  apiFetch<Candidate[]>(`/jobs/${encodeURIComponent(job_id)}/candidates`)

export const createScreeningAgent = (job_id: string) =>
  apiFetch<Agent>(`/jobs/${encodeURIComponent(job_id)}/agent`, { method: "POST" })

export const triggerCall = (job_id: string, candidate_id: string) =>
  apiFetch<Call>(`/jobs/${encodeURIComponent(job_id)}/candidates/${encodeURIComponent(candidate_id)}/call`, {
    method: "POST",
  })

export const getJobCalls = (job_id: string) =>
  apiFetch<JobCall[]>(`/jobs/${encodeURIComponent(job_id)}/calls`)

export const parseJD = (job_id: string) =>
  apiFetch<Record<string, unknown>>(`/jobs/${encodeURIComponent(job_id)}/parse`, { method: "POST" })

export const searchCandidates = (job_id: string) =>
  apiFetch<Candidate[]>(`/jobs/${encodeURIComponent(job_id)}/search`, { method: "POST" })

export const updateCandidatePhone = (job_id: string, candidate_id: string, phone_e164: string) =>
  apiFetch<Candidate>(`/jobs/${encodeURIComponent(job_id)}/candidates/${encodeURIComponent(candidate_id)}`, {
    method: "PATCH",
    body: JSON.stringify({ phone_e164 }),
  })

export const createReachoutAgent = (job_id: string) =>
  apiFetch<Agent>(`/jobs/${encodeURIComponent(job_id)}/agent/reachout`, { method: "POST" })

export const triggerReachoutCall = (job_id: string, candidate_id: string) =>
  apiFetch<Call>(
    `/jobs/${encodeURIComponent(job_id)}/candidates/${encodeURIComponent(candidate_id)}/reachout-call`,
    { method: "POST" },
  )

export const getReachoutDashboard = (job_id: string) =>
  apiFetch<ReachoutDashboardCandidate[]>(`/jobs/${encodeURIComponent(job_id)}/reachout-dashboard`)
