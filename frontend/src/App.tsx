import { useCallback, useEffect, useState } from 'react'
import { type Job, listJobs } from './api'
import { JobList } from './JobList'
import { UploadDropzone } from './UploadDropzone'

const POLL_MS = 1000

export default function App() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setJobs(await listJobs())
      setError(null)
    } catch (err) {
      setError((err as Error).message)
    }
  }, [])

  useEffect(() => {
    let timer: number
    let stopped = false
    // Schedule the next poll only after the current one finishes, so a slow API
    // can't pile up overlapping requests the way setInterval would.
    const tick = async () => {
      await refresh()
      if (!stopped) timer = window.setTimeout(tick, POLL_MS)
    }
    tick()
    return () => {
      stopped = true
      window.clearTimeout(timer)
    }
  }, [refresh])

  return (
    <main>
      <h1>Thumbnail Factory</h1>
      <UploadDropzone onUploaded={refresh} />
      <JobList jobs={jobs} error={error} />
    </main>
  )
}
