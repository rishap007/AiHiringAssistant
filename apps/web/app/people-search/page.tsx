"use client"

import { useCallback, useEffect, useMemo, useState } from "react"

import {
  createJob,
  createReachoutAgent,
  getJobs,
  getJobCandidates,
  getReachoutDashboard,
  parseJD,
  searchCandidates,
  triggerReachoutCall,
  updateCandidatePhone,
  updateJob,
  type Candidate,
  type Job,
  type ReachoutDashboardCandidate,
} from "@/lib/api"
import { StatusBadge } from "@/components/status-badge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"

type ParsedCriteria = {
  title: string
  seniority: string
  skills: string[]
  location: string
  keywords: string[]
}

const phonePattern = /^\+[1-9]\d{6,14}$/
const terminalStatuses = new Set(["COMPLETED", "NOT_CONNECTED", "FAILED", "CANCELLED"])

function ResultFields({ result }: { result: Record<string, unknown> | null }) {
  if (!result || Object.keys(result).length === 0) return <span className="text-muted-foreground">—</span>
  return <dl className="space-y-1 text-xs">{Object.entries(result).map(([key, value]) => <div key={key}><dt className="inline font-medium">{key}: </dt><dd className="inline text-muted-foreground">{typeof value === "object" ? JSON.stringify(value) : String(value)}</dd></div>)}</dl>
}

export default function PeopleSearchPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [jobId, setJobId] = useState("")
  const [newJobTitle, setNewJobTitle] = useState("")
  const [jdRawText, setJdRawText] = useState("")
  const [criteria, setCriteria] = useState<ParsedCriteria | null>(null)
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [dashboard, setDashboard] = useState<ReachoutDashboardCandidate[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  const selectedCandidates = useMemo(() => candidates.filter((candidate) => selected.has(candidate.id)), [candidates, selected])
  const reachoutBlocked = selectedCandidates.some((candidate) => !candidate.phone_e164)

  useEffect(() => {
    getJobs().then((loaded) => { setJobs(loaded); if (loaded[0]) { setJobId(loaded[0].id); setJdRawText(loaded[0].description || "") } }).catch((err) => setError(err.message))
  }, [])

  useEffect(() => {
    if (!jobId) return
    Promise.all([getJobCandidates(jobId), getReachoutDashboard(jobId)])
      .then(([loadedCandidates, loadedDashboard]) => { setCandidates(loadedCandidates); setDashboard(loadedDashboard) })
      .catch((err) => setError(err.message))
  }, [jobId])

  const refreshDashboard = useCallback(async () => {
    setDashboard(await getReachoutDashboard(jobId))
  }, [jobId])

  useEffect(() => {
    if (!jobId || dashboard.length === 0 || dashboard.every((candidate) => !candidate.call_status || terminalStatuses.has(candidate.call_status.toUpperCase()))) return
    const interval = window.setInterval(() => { refreshDashboard().catch((err) => setError(err.message)) }, 5000)
    return () => window.clearInterval(interval)
  }, [dashboard, jobId, refreshDashboard])

  async function handleCreateJob() {
    if (!newJobTitle.trim()) return
    setBusy("new-job")
    try {
      const job = await createJob({ title: newJobTitle.trim(), description: "" })
      setJobs((current) => [job, ...current]); setJobId(job.id); setNewJobTitle(""); setNotice("Job created")
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to create job") }
    finally { setBusy(null) }
  }

  async function handleSaveAndParse() {
    if (!jobId || !jdRawText.trim()) return
    setBusy("parse"); setError(null); setNotice(null)
    try {
      await updateJob(jobId, { jd_raw_text: jdRawText })
      const parsed = await parseJD(jobId)
      setCriteria({
        title: String(parsed.title || ""), seniority: String(parsed.seniority || ""), location: String(parsed.location || ""),
        skills: Array.isArray(parsed.skills) ? parsed.skills.map(String) : [], keywords: Array.isArray(parsed.keywords) ? parsed.keywords.map(String) : [],
      })
      setNotice("Job description parsed")
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to parse job description") }
    finally { setBusy(null) }
  }

  async function handleSearch() {
    if (!jobId) return
    setBusy("search"); setError(null); setNotice(null)
    try { const found = await searchCandidates(jobId); setCandidates(found); setSelected(new Set()); await refreshDashboard(); setNotice(`${found.length} candidates found`) }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to search candidates") }
    finally { setBusy(null) }
  }

  async function handlePhoneSave(candidate: Candidate, value: string) {
    if (!phonePattern.test(value)) { setError("Use an E.164 number, for example +919876543210"); return }
    try { const updated = await updateCandidatePhone(jobId, candidate.id, value); setCandidates((current) => current.map((item) => item.id === updated.id ? updated : item)); setNotice(`${candidate.name}'s phone number saved`) }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to save phone number") }
  }

  async function handleReachout() {
    if (!jobId || !selectedCandidates.length || reachoutBlocked) return
    setBusy("reachout"); setError(null); setNotice(null)
    try {
      const job = jobs.find((item) => item.id === jobId)
      if (!job?.reachout_agent_id) await createReachoutAgent(jobId)
      await Promise.all(selectedCandidates.map((candidate) => triggerReachoutCall(jobId, candidate.id)))
      await refreshDashboard(); setNotice(`Reachout started for ${selectedCandidates.length} candidate${selectedCandidates.length === 1 ? "" : "s"}`); setSelected(new Set())
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to start reachout calls") }
    finally { setBusy(null) }
  }

  function updateCriteria(field: keyof ParsedCriteria, value: string) {
    setCriteria((current) => current ? { ...current, [field]: value } : current)
  }

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-6 md:p-10">
      <div><p className="text-sm font-medium text-muted-foreground">People Search</p><h1 className="text-3xl font-semibold tracking-tight">Find and reach out to candidates</h1><p className="mt-2 text-muted-foreground">Parse a job description, search for people, then start respectful outreach.</p></div>

      {error && <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {notice && <p className="rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-700">{notice}</p>}

      <section className="space-y-4 rounded-xl border bg-background p-5"><div className="flex flex-wrap items-end gap-3"><div className="min-w-64 flex-1 space-y-2"><label htmlFor="job-select" className="text-sm font-medium">Select job</label><select id="job-select" value={jobId} onChange={(event) => { const nextJobId = event.target.value; setJobId(nextJobId); const nextJob = jobs.find((job) => job.id === nextJobId); setJdRawText(nextJob?.description || "") }} className="h-9 w-full rounded-md border bg-background px-3 text-sm"><option value="">Choose a job...</option>{jobs.map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}</select></div><div className="flex flex-1 gap-2"><Input value={newJobTitle} onChange={(event) => setNewJobTitle(event.target.value)} placeholder="New job title" /><Button onClick={handleCreateJob} disabled={!newJobTitle.trim() || busy !== null}>{busy === "new-job" ? "Creating..." : "Create job"}</Button></div></div><div className="space-y-2"><label htmlFor="jd-text" className="text-sm font-medium">Job description</label><Textarea id="jd-text" value={jdRawText} onChange={(event) => setJdRawText(event.target.value)} rows={9} disabled={!jobId} placeholder="Select or create a job, then paste the job description..." /></div><Button onClick={handleSaveAndParse} disabled={!jobId || !jdRawText.trim() || busy !== null}>{busy === "parse" ? "Parsing..." : "Save + Parse"}</Button></section>

      {criteria && <section className="space-y-4"><div><h2 className="text-xl font-semibold">Parsed criteria</h2><p className="text-sm text-muted-foreground">Review and adjust the extracted criteria before searching.</p></div><div className="flex flex-wrap gap-3 rounded-xl border bg-background p-4"><label className="flex items-center gap-2 text-sm"><span className="font-medium">Title</span><Input className="h-8 w-44" value={criteria.title} onChange={(event) => updateCriteria("title", event.target.value)} /></label><label className="flex items-center gap-2 text-sm"><span className="font-medium">Seniority</span><Input className="h-8 w-36" value={criteria.seniority} onChange={(event) => updateCriteria("seniority", event.target.value)} /></label><label className="flex items-center gap-2 text-sm"><span className="font-medium">Location</span><Input className="h-8 w-44" value={criteria.location} onChange={(event) => updateCriteria("location", event.target.value)} /></label><div className="flex flex-wrap items-center gap-2"><span className="text-sm font-medium">Skills</span>{criteria.skills.map((skill, index) => <Input key={`${skill}-${index}`} className="h-8 w-32" value={skill} onChange={(event) => setCriteria((current) => current ? { ...current, skills: current.skills.map((item, itemIndex) => itemIndex === index ? event.target.value : item) } : current)} />)}</div></div></section>}

      <section className="space-y-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-semibold">Search candidates</h2><p className="text-sm text-muted-foreground">Mock results intentionally omit phone numbers so they can be completed here.</p>{!criteria && <p className="mt-1 text-sm text-amber-700">Save + Parse the job description above to enable candidate search.</p>}</div><div className="flex items-center gap-2"><Button variant="outline" onClick={handleSearch} disabled={!criteria || busy !== null}>{busy === "search" ? "Searching..." : "Search candidates"}</Button><Button onClick={handleReachout} disabled={!selectedCandidates.length || reachoutBlocked || busy !== null}>{busy === "reachout" ? "Starting..." : "Reach out to selected"}</Button></div></div><div className="rounded-xl border bg-background"><Table><TableHeader><TableRow><TableHead className="w-10">Select</TableHead><TableHead>Name</TableHead><TableHead>Phone</TableHead><TableHead>Source</TableHead><TableHead>Headline</TableHead></TableRow></TableHeader><TableBody>{candidates.length === 0 ? <TableRow><TableCell colSpan={5} className="h-20 text-center text-muted-foreground">Search results will appear here.</TableCell></TableRow> : candidates.map((candidate) => <TableRow key={candidate.id}><TableCell><input type="checkbox" checked={selected.has(candidate.id)} onChange={(event) => setSelected((current) => { const next = new Set(current); if (event.target.checked) next.add(candidate.id); else next.delete(candidate.id); return next })} aria-label={`Select ${candidate.name}`} /></TableCell><TableCell className="font-medium">{candidate.name}</TableCell><TableCell>{candidate.phone_e164 ? candidate.phone_e164 : <Input className="h-8 w-44" placeholder="+919876543210" aria-label={`Phone for ${candidate.name}`} onBlur={(event) => { if (event.target.value) void handlePhoneSave(candidate, event.target.value) }} />}</TableCell><TableCell>{candidate.source === "mock" ? <Badge title="Simulated — no live people-search API key was available within the assignment window.">mock · simulated</Badge> : <Badge variant="secondary">{candidate.source}</Badge>}</TableCell><TableCell className="max-w-sm truncate text-muted-foreground">{candidate.headline || "—"}</TableCell></TableRow>)}</TableBody></Table></div>{selectedCandidates.length > 0 && reachoutBlocked && <p className="text-sm text-amber-700">Add a valid phone number to every selected candidate before reaching out.</p>}</section>

      <section className="space-y-4"><div><h2 className="text-xl font-semibold">Reachout dashboard</h2><p className="text-sm text-muted-foreground">Statuses refresh every five seconds while calls are active.</p></div><div className="rounded-xl border bg-background"><Table><TableHeader><TableRow><TableHead>Candidate</TableHead><TableHead>Source</TableHead><TableHead>Status</TableHead><TableHead>Result</TableHead></TableRow></TableHeader><TableBody>{dashboard.length === 0 ? <TableRow><TableCell colSpan={4} className="h-20 text-center text-muted-foreground">Reachout activity will appear here.</TableCell></TableRow> : dashboard.map((candidate) => <TableRow key={candidate.id}><TableCell className="font-medium">{candidate.name}</TableCell><TableCell>{candidate.source === "mock" ? <Badge title="Simulated — no live people-search API key was available within the assignment window.">mock · simulated</Badge> : candidate.source}</TableCell><TableCell>{candidate.call_status ? <StatusBadge status={candidate.call_status} /> : <span className="text-muted-foreground">Not called</span>}</TableCell><TableCell><ResultFields result={candidate.result_json} /></TableCell></TableRow>)}</TableBody></Table></div></section>
    </div>
  )
}
