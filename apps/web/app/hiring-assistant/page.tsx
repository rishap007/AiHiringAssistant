"use client"

import Link from "next/link"
import { useEffect, useState } from "react"

import { createJob, getJobs, type Job } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"

export default function HiringAssistantPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getJobs().then(setJobs).catch((err) => setError(err.message)).finally(() => setLoading(false))
  }, [])

  async function handleCreateJob(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const job = await createJob({ title, description })
      setJobs((current) => [job, ...current])
      setTitle("")
      setDescription("")
      setOpen(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create job")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8 p-6 md:p-10">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-muted-foreground">Hiring Assistant</p>
          <h1 className="text-3xl font-semibold tracking-tight">Jobs</h1>
          <p className="mt-2 text-muted-foreground">Create a role and manage its screening workflow.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <Button type="button" onClick={() => setOpen(true)}>New job</Button>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create a new job</DialogTitle>
              <DialogDescription>Add the role details to start screening candidates.</DialogDescription>
            </DialogHeader>
            <form id="new-job-form" className="space-y-4" onSubmit={handleCreateJob}>
              <div className="space-y-2">
                <label htmlFor="job-title" className="text-sm font-medium">Title</label>
                <Input id="job-title" value={title} onChange={(event) => setTitle(event.target.value)} required placeholder="Senior Product Designer" />
              </div>
              <div className="space-y-2">
                <label htmlFor="job-description" className="text-sm font-medium">Description</label>
                <Textarea id="job-description" value={description} onChange={(event) => setDescription(event.target.value)} required rows={6} placeholder="Paste the job description here..." />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={saving}>{saving ? "Creating..." : "Create job"}</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {error && <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      <div className="rounded-xl border bg-background">
        <Table>
          <TableHeader><TableRow><TableHead>Title</TableHead><TableHead>Description</TableHead><TableHead>Created</TableHead></TableRow></TableHeader>
          <TableBody>
            {loading && <TableRow><TableCell colSpan={3} className="h-24 text-center text-muted-foreground">Loading jobs...</TableCell></TableRow>}
            {!loading && jobs.length === 0 && <TableRow><TableCell colSpan={3} className="h-24 text-center text-muted-foreground">No jobs yet. Create your first job.</TableCell></TableRow>}
            {jobs.map((job) => (
              <TableRow key={job.id}>
                <TableCell className="font-medium"><Link className="hover:underline" href={`/hiring-assistant/${job.id}`}>{job.title}</Link></TableCell>
                <TableCell className="max-w-xl truncate text-muted-foreground">{job.description}</TableCell>
                <TableCell className="text-muted-foreground">{new Date(job.created_at).toLocaleDateString()}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
