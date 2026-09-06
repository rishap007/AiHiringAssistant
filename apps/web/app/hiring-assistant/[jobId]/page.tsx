"use client"

import Link from "next/link"
import { useParams } from "next/navigation"
import { useCallback, useEffect, useState } from "react"

import { addCandidate, createScreeningAgent, getJobCandidates, getJobCalls, getJobs, triggerCall, type Agent, type Candidate, type Job, type JobCall } from "@/lib/api"
import { StatusBadge } from "@/components/status-badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

const phonePattern = /^\+[1-9]\d{6,14}$/
const terminalStatuses = new Set(["COMPLETED", "NOT_CONNECTED", "FAILED", "CANCELLED"])

function ResultFields({ result }: { result: Record<string, unknown> | null }) {
  if (!result || Object.keys(result).length === 0) return <span className="text-muted-foreground">—</span>
  return <dl className="space-y-1 text-xs">{Object.entries(result).map(([key, value]) => <div key={key}><dt className="inline font-medium">{key}: </dt><dd className="inline text-muted-foreground">{typeof value === "object" ? JSON.stringify(value) : String(value)}</dd></div>)}</dl>
}

export default function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const [job, setJob] = useState<Job | null>(null)
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [calls, setCalls] = useState<JobCall[]>([])
  const [agent, setAgent] = useState<Agent | null>(null)
  const [name, setName] = useState("")
  const [phone, setPhone] = useState("")
  const [phoneError, setPhoneError] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)

  const refreshCalls = useCallback(async () => {
    setCalls(await getJobCalls(jobId))
  }, [jobId])

  useEffect(() => {
    Promise.all([getJobs(), getJobCandidates(jobId), getJobCalls(jobId)])
      .then(([jobs, loadedCandidates, loadedCalls]) => {
        const loadedJob = jobs.find((item) => item.id === jobId)
        if (!loadedJob) throw new Error("Job not found")
        setJob(loadedJob)
        setCandidates(loadedCandidates)
        setCalls(loadedCalls)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [jobId])

  useEffect(() => {
    if (calls.length === 0 || calls.every((call) => terminalStatuses.has(call.status.toUpperCase()))) return
    const interval = window.setInterval(() => { refreshCalls().catch((err) => setError(err.message)) }, 5000)
    return () => window.clearInterval(interval)
  }, [calls, refreshCalls])

  async function handleAddCandidate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!phonePattern.test(phone)) { setPhoneError("Use an E.164 number, for example +919876543210"); return }
    setBusy("candidate")
    setPhoneError("")
    try {
      const candidate = await addCandidate(jobId, { name, phone_e164: phone })
      setCandidates((current) => [candidate, ...current])
      setName(""); setPhone("")
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to add candidate") }
    finally { setBusy(null) }
  }

  async function handleCreateAgent() {
    setBusy("agent")
    try {
      const created = await createScreeningAgent(jobId)
      setAgent(created)
      setJob((current) => current ? { ...current, agent_id: created.id } : current)
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to create agent") }
    finally { setBusy(null) }
  }

  async function handleCall(candidate: Candidate) {
    setBusy(candidate.id)
    try {
      await triggerCall(jobId, candidate.id)
      await refreshCalls()
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to start call") }
    finally { setBusy(null) }
  }

  if (loading) return <div className="p-10 text-muted-foreground">Loading job...</div>
  if (!job) return <div className="p-10">{error || "Job not found"}</div>
  const hasAgent = Boolean(agent || job.agent_id)

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-6 md:p-10">
      <div><Link href="/hiring-assistant" className="text-sm text-muted-foreground hover:underline">← All jobs</Link><div className="mt-4 flex flex-wrap items-start justify-between gap-4"><div><h1 className="text-3xl font-semibold tracking-tight">{job.title}</h1><p className="mt-2 max-w-3xl whitespace-pre-wrap text-muted-foreground">{job.description}</p></div><Button onClick={handleCreateAgent} disabled={hasAgent || busy !== null}>{hasAgent ? "Screening agent ready" : busy === "agent" ? "Creating..." : "Create screening agent"}</Button></div></div>
      {error && <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <section className="space-y-4"><div><h2 className="text-xl font-semibold">Add candidate</h2><p className="text-sm text-muted-foreground">Phone numbers must be in E.164 format so Hunar can call them.</p></div><form onSubmit={handleAddCandidate} className="grid gap-3 rounded-xl border bg-background p-4 md:grid-cols-[1fr_1fr_auto]"><Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Candidate name" required /><div><Input value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+919876543210" aria-invalid={Boolean(phoneError)} required />{phoneError && <p className="mt-1 text-xs text-red-600">{phoneError}</p>}</div><Button type="submit" disabled={busy !== null}>{busy === "candidate" ? "Adding..." : "Add candidate"}</Button></form></section>

      <section className="space-y-4"><h2 className="text-xl font-semibold">Candidates</h2><div className="rounded-xl border bg-background"><Table><TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Phone</TableHead><TableHead>Source</TableHead><TableHead className="text-right">Action</TableHead></TableRow></TableHeader><TableBody>{candidates.length === 0 ? <TableRow><TableCell colSpan={4} className="h-20 text-center text-muted-foreground">No candidates yet.</TableCell></TableRow> : candidates.map((candidate) => <TableRow key={candidate.id}><TableCell className="font-medium">{candidate.name}</TableCell><TableCell>{candidate.phone_e164 || <span className="text-muted-foreground">Missing phone</span>}</TableCell><TableCell>{candidate.source}</TableCell><TableCell className="text-right"><Button size="sm" onClick={() => handleCall(candidate)} disabled={!hasAgent || !candidate.phone_e164 || busy !== null}>{busy === candidate.id ? "Calling..." : "Call"}</Button></TableCell></TableRow>)}</TableBody></Table></div></section>

      <section className="space-y-4"><div className="flex items-center justify-between"><h2 className="text-xl font-semibold">Calls</h2><span className="text-sm text-muted-foreground">{calls.length} total</span></div><div className="rounded-xl border bg-background"><Table><TableHeader><TableRow><TableHead>Candidate</TableHead><TableHead>Status</TableHead><TableHead>Duration</TableHead><TableHead>Result</TableHead><TableHead>Recording</TableHead></TableRow></TableHeader><TableBody>{calls.length === 0 ? <TableRow><TableCell colSpan={5} className="h-20 text-center text-muted-foreground">Calls will appear here.</TableCell></TableRow> : calls.map((call) => <TableRow key={call.id}><TableCell className="font-medium">{call.candidate_name}</TableCell><TableCell><StatusBadge status={call.status} /></TableCell><TableCell>{call.duration_seconds != null ? `${call.duration_seconds}s` : "—"}</TableCell><TableCell><ResultFields result={call.result_json} /></TableCell><TableCell>{call.recording_url ? <audio controls className="h-8 max-w-[220px]" src={call.recording_url} /> : <span className="text-muted-foreground">—</span>}</TableCell></TableRow>)}</TableBody></Table></div></section>
    </div>
  )
}
