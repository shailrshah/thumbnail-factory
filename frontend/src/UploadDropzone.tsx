import { useRef, useState } from 'react'
import { ACCEPTED_TYPES, MAX_UPLOAD_MB, uploadImage } from './api'

interface Props {
  onUploaded: () => void
}

export function UploadDropzone({ onUploaded }: Props) {
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState<string[]>([])

  async function upload(files: FileList | null) {
    if (!files?.length) return
    setBusy(true)
    setErrors([])
    const failures: string[] = []
    for (const file of Array.from(files)) {
      try {
        await uploadImage(file)
        onUploaded()
      } catch (err) {
        failures.push(`${file.name}: ${(err as Error).message}`)
      }
    }
    setErrors(failures)
    setBusy(false)
    if (input.current) input.current.value = ''
  }

  return (
    <section
      className={`dropzone${dragging ? ' dragging' : ''}`}
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        upload(e.dataTransfer.files)
      }}
    >
      <p>
        Drop images here or{' '}
        <button type="button" onClick={() => input.current?.click()} disabled={busy}>
          choose files
        </button>
      </p>
      <p className="hint">
        JPEG, PNG, or WebP · up to {MAX_UPLOAD_MB} MB each{busy && ' · uploading…'}
      </p>
      <input
        ref={input}
        type="file"
        accept={ACCEPTED_TYPES.join(',')}
        multiple
        hidden
        onChange={(e) => upload(e.target.files)}
      />
      {errors.map((msg) => (
        <p key={msg} className="error" role="alert">
          {msg}
        </p>
      ))}
    </section>
  )
}
