import { useEffect, useState } from 'react'
import MediaFile from './MediaFile'
import ReportForm from './ReportForm'
import Conversation from './Conversation'

export default function ItemDetail({ initialItem, api, userId, onChanged, onOpenItem, onDeleted }) {
  const [item, setItem] = useState(initialItem)
  const [media, setMedia] = useState([])
  const [matches, setMatches] = useState([])
  const [matched, setMatched] = useState(false)
  const [conversation, setConversation] = useState(null)
  const [editing, setEditing] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const owned = item.owner_id === userId
  useEffect(() => {
    const controller = new AbortController()
    Promise.all([
      api(`/items/${item.id}`, { signal: controller.signal }),
      api(`/items/${item.id}/media`, { signal: controller.signal }),
      owned ? api(`/items/${item.id}/matches`, { signal: controller.signal }) : Promise.resolve([]),
    ]).then(([latest, files, suggestions]) => {
      setItem(latest)
      setMedia(files)
      setMatches(suggestions)
      setMatched(suggestions.length > 0)
      setLoaded(true)
    }).catch(error => { if (error.name !== 'AbortError') setError(error.message) })
    return () => controller.abort()
  }, [api, item.id, owned])
  async function perform(action) {
    setBusy(true)
    setError('')
    try { await action() } catch (error) { setError(error.message) } finally { setBusy(false) }
  }
  async function upload(event) {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    await perform(async () => {
      const record = await api(`/items/${item.id}/media`, { method: 'POST', body: data })
      setMedia(previous => [...previous, record])
      setMatches([])
      setMatched(false)
      form.reset()
    })
  }
  if (editing) return <ReportForm api={api} existing={item} onSaved={updated => {
    setItem(updated)
    setEditing(false)
    setMatches([])
    setMatched(false)
    onChanged()
  }} />
  return <div className="detail-view">
    {!loaded && !error && <p role="status">Loading report...</p>}
    <span className={`inline-status ${item.kind}`}>{item.kind} - {item.status}</span>
    <h3>{item.title}</h3>
    <p className="preserve-lines">{item.description}</p>
    <p>{item.category} | {item.location}</p>
    <p>Campus time: {item.occurred_at.replace('T', ' ')}</p>
    <div className="media-grid">{media.map(record => <MediaFile key={record.id} api={api} record={record}
      onDelete={owned && !busy ? id => perform(async () => {
        await api(`/media/${id}`, { method: 'DELETE' })
        setMedia(previous => previous.filter(entry => entry.id !== id))
        setMatches([])
        setMatched(false)
      }) : undefined} />)}</div>
    {owned && <>
      <div className="action-row">
        <button className="button secondary" disabled={busy} onClick={() => setEditing(true)}>Edit report</button>
        <button className="button secondary" disabled={busy} onClick={() => perform(async () => {
          const updated = await api(`/items/${item.id}`, { method: 'PATCH', body: {
            status: item.status === 'open' ? 'resolved' : 'open',
          } })
          setItem(updated)
          setMatches([])
          setMatched(false)
          onChanged()
        })}>{item.status === 'open' ? 'Mark resolved' : 'Reopen report'}</button>
        <button className="button danger" disabled={busy} onClick={() => {
          if (window.confirm('Delete this report, its uploads, conversations, and messages? This cannot be undone.')) {
            perform(async () => {
              await api(`/items/${item.id}`, { method: 'DELETE' })
              onDeleted()
            })
          }
        }}>Delete report</button>
      </div>
      <form className="form-stack upload-form" onSubmit={upload}>
        <label>Add a picture or video<input name="file" type="file" required
          accept="image/jpeg,image/png,image/webp,video/mp4,video/webm" /></label>
        <small>Up to five files. Default limit: 10 MiB per file.</small>
        <button className="button secondary" disabled={busy || !loaded || media.length >= 5}>Upload file</button>
      </form>
      {item.status === 'open' && <div className="matching-panel">
        <h3>AI matching</h3>
        <p>Gemini compares descriptions and attached pictures with other open reports. These details will be sent to Gemini when you request matches.</p>
        <button className="button primary" disabled={busy} onClick={() => perform(async () => {
          const hits = await api(`/items/${item.id}/matches`, { method: 'POST' })
          setMatches(hits)
          setMatched(true)
        })}>{busy ? 'Please wait...' : 'Find possible matches'}</button>
        {matched && matches.length === 0 && <p>No possible matches were found.</p>}
        {matches.map(hit => <article className="match" key={hit.target_id}>
          <strong>Similarity: {Math.round(hit.score * 100)}%</strong><p>{hit.reason}</p>
          <button className="details-link" disabled={busy} onClick={() => perform(async () => {
            onOpenItem(await api(`/items/${hit.target_id}`))
          })}>View matching report</button>
        </article>)}
      </div>}
    </>}
    {!owned && item.status === 'open' && !conversation && <button className="button primary" disabled={busy}
      onClick={() => perform(async () => {
        setConversation(await api('/conversations', { method: 'POST', body: { item_id: item.id } }))
      })}>Contact reporter</button>}
    {conversation && <Conversation api={api} conversation={conversation} userId={userId} />}
    {error && <p role="alert" className="error-message">{error}</p>}
  </div>
}
