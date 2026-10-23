import { useEffect, useState } from 'react'
import Conversation from './Conversation'

export default function Inbox({ api, userId }) {
  const [threads, setThreads] = useState([])
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      const all = []
      let page
      do {
        page = await api(`/conversations?offset=${all.length}&limit=100`, { signal: controller.signal })
        const resolved = await Promise.all(page.map(async thread => ({ ...thread,
          title: (await api(`/items/${thread.item_id}`, { signal: controller.signal })).title,
        })))
        all.push(...resolved)
      } while (page.length === 100)
      if (!controller.signal.aborted) setThreads(all)
    }
    load().catch(error => { if (error.name !== 'AbortError') setError(error.message) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [api])
  if (selected) return <><button className="details-link" onClick={() => setSelected(null)}>Back to conversations</button>
    <h3>{selected.title}</h3><Conversation api={api} conversation={selected} userId={userId} /></>
  return <div className="form-stack">
    {loading && <p role="status">Loading conversations...</p>}
    {error && <p className="error-message" role="alert">{error}</p>}
    {!loading && !error && threads.length === 0 && <p>No conversations yet. Open a report to contact its owner.</p>}
    {threads.map(thread => <button className="button secondary" key={thread.id} onClick={() => setSelected(thread)}>
      {thread.title} - {thread.owner_id === userId ? 'Your report' : 'Your enquiry'}
    </button>)}
  </div>
}
