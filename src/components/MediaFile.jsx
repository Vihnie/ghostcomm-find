import { useEffect, useState } from 'react'

export default function MediaFile({ record, api, onDelete }) {
  const [url, setUrl] = useState('')
  const [error, setError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    let objectUrl
    api(`/media/${record.id}`, { blob: true, signal: controller.signal }).then(blob => {
      if (controller.signal.aborted) return
      objectUrl = URL.createObjectURL(blob)
      setUrl(objectUrl)
    }).catch(error => { if (error.name !== 'AbortError') setError(error.message) })
    return () => {
      controller.abort()
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [api, record.id])
  return <div className="media-file">
    {error && <p role="alert">{error}</p>}
    {url && (record.content_type.startsWith('image/') ? <img src={url} alt="Reported item" /> :
      <video src={url} controls preload="metadata" aria-label="Reported item video" />)}
    {url && <a href={url} download={`item-${record.id}`}>Download file</a>}
    {onDelete && <button className="details-link" onClick={() => onDelete(record.id)}>Remove file</button>}
  </div>
}
