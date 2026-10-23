import { useEffect, useState } from 'react'

export default function Conversation({ api, conversation, userId }) {
  const [messages, setMessages] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const path = `/conversations/${conversation.id}/messages`
  useEffect(() => {
    const controller = new AbortController()
    async function refresh() {
      try {
        const collected = []
        let page
        do {
          page = await api(`${path}?offset=${collected.length}&limit=100`, { signal: controller.signal })
          collected.push(...page)
        } while (page.length === 100)
        if (!controller.signal.aborted) {
          setMessages(collected)
          setError('')
        }
      } catch (error) {
        if (error.name !== 'AbortError') setError(error.message)
      }
    }
    refresh()
    const timer = setInterval(refresh, 10000)
    return () => { controller.abort(); clearInterval(timer) }
  }, [api, path])
  async function send(event) {
    event.preventDefault()
    const form = event.currentTarget
    const body = new FormData(form).get('body')
    setBusy(true)
    try {
      const message = await api(path, { method: 'POST', body: { body } })
      setMessages(previous => previous.some(entry => entry.id === message.id) ? previous : [...previous, message])
      form.reset()
      setError('')
    } catch (error) { setError(error.message) } finally { setBusy(false) }
  }
  return <section className="conversation">
    <h3>Recovery conversation</h3>
    <p>Only you and the other participant can read these messages. Verify ownership before arranging a handover.</p>
    <div className="message-list" aria-live="polite">
      {messages.length === 0 && <p>No messages yet.</p>}
      {messages.map(message => <article key={message.id} className={message.sender_id === userId ? 'message own' : 'message'}>
        <strong>{message.sender_id === userId ? 'You' : 'Other participant'}</strong>
        <p>{message.body}</p><small>{new Date(message.created_at).toLocaleString()}</small>
      </article>)}
    </div>
    <form className="form-stack" onSubmit={send}>
      <label>Message<textarea name="body" required maxLength={4000} rows={2} /></label>
      {error && <p className="error-message" role="alert">{error}</p>}
      <button className="button primary" disabled={busy}>{busy ? 'Sending...' : 'Send message'}</button>
    </form>
  </section>
}
