export type JobStatus = 'queued' | 'processing' | 'done' | 'failed'

export interface Thumbnail {
  width: number
  url: string
}

export interface Job {
  id: string
  status: JobStatus
  filename: string
  created_at: string
  started_at: string | null
  finished_at: string | null
  worker: string | null
  error: string | null
  thumbnails: Thumbnail[]
}

export const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
export const MAX_UPLOAD_MB = 10

export async function uploadImage(file: File): Promise<Job> {
  const body = new FormData()
  body.append('file', file)
  const resp = await fetch('/api/jobs', { method: 'POST', body })
  if (!resp.ok) throw new Error(await errorMessage(resp))
  return resp.json()
}

export async function listJobs(): Promise<Job[]> {
  const resp = await fetch('/api/jobs')
  if (!resp.ok) throw new Error(await errorMessage(resp))
  return (await resp.json()).jobs
}

async function errorMessage(resp: Response): Promise<string> {
  // nginx rejects some requests itself (e.g. 413 for oversize bodies) with an HTML page,
  // so the body isn't always the backend's JSON {"detail": ...}.
  try {
    const body = await resp.json()
    if (typeof body?.detail === 'string') return body.detail
  } catch {
    // not JSON
  }
  if (resp.status === 413) return `File is larger than ${MAX_UPLOAD_MB} MB`
  return `Request failed (${resp.status})`
}
