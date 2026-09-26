import type { Job } from './api'
import { JobCard } from './JobCard'

interface Props {
  jobs: Job[]
  error: string | null
}

export function JobList({ jobs, error }: Props) {
  return (
    <section>
      <h2>Recent jobs</h2>
      {error && (
        <p className="error" role="alert">
          Can't reach the API: {error}
        </p>
      )}
      {jobs.length === 0 && !error ? (
        <p className="hint">No jobs yet. Upload an image to start one.</p>
      ) : (
        <ul className="jobs">
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </ul>
      )}
    </section>
  )
}
