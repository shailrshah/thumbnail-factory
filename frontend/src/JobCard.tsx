import type { Job } from './api'

export function JobCard({ job }: { job: Job }) {
  return (
    <li className="job">
      <div className="job-header">
        <span className={`badge ${job.status}`}>{job.status}</span>
        <span className="filename">{job.filename}</span>
      </div>
      <dl className="meta">
        <dt>worker</dt>
        <dd>{job.worker ?? '—'}</dd>
        <dt>took</dt>
        <dd>{duration(job)}</dd>
      </dl>
      {job.error && <p className="error">{job.error}</p>}
      {job.thumbnails.length > 0 && (
        <div className="thumbs">
          {job.thumbnails.map((t) => (
            <a key={t.width} href={t.url} target="_blank" rel="noreferrer">
              <img src={t.url} alt={`${job.filename} at ${t.width}px`} loading="lazy" />
              <span>{t.width}px</span>
            </a>
          ))}
        </div>
      )}
    </li>
  )
}

function duration(job: Job): string {
  if (!job.started_at || !job.finished_at) return '—'
  const ms = Date.parse(job.finished_at) - Date.parse(job.started_at)
  return `${(ms / 1000).toFixed(0)} s`
}
