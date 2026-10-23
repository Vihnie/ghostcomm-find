import { useState } from 'react'

export default function ReportForm({ api, onSaved, existing }) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const body = Object.fromEntries(form)
    if (existing) delete body.kind
    setBusy(true)
    setError('')
    try {
      const item = await api(existing ? `/items/${existing.id}` : '/items', {
        method: existing ? 'PATCH' : 'POST', body,
      })
      onSaved(item)
    } catch (error) {
      setError(error.message)
    } finally {
      setBusy(false)
    }
  }
  const localDate = existing?.occurred_at?.slice(0, 16) || ''
  return (
    <form className="form-stack" onSubmit={submit}>
      {!existing && <label>Report type<select name="kind" defaultValue="lost">
        <option value="lost">I lost an item</option><option value="found">I found an item</option>
      </select></label>}
      <label>Title<input name="title" defaultValue={existing?.title} required minLength={3} maxLength={150} /></label>
      <label>Description<textarea name="description" defaultValue={existing?.description} required minLength={10} maxLength={5000} rows={4} /></label>
      <label>Category<input name="category" defaultValue={existing?.category} required maxLength={60} list="categories" /></label>
      <datalist id="categories">{['Electronics', 'Personal items', 'Books', 'Bags', 'Clothing', 'Documents', 'Other'].map(category => <option key={category}>{category}</option>)}</datalist>
      <label>Location<input name="location" defaultValue={existing?.location} required maxLength={200} /></label>
      <label>Date and time on campus<input name="occurred_at" type="datetime-local" defaultValue={localDate} required /></label>
      <small>Use campus local time. Add pictures or a video after saving. Keep private identifying details for the recovery conversation.</small>
      {error && <p className="error-message" role="alert">{error}</p>}
      <button className="button primary" disabled={busy}>{busy ? 'Saving...' : existing ? 'Save changes' : 'Save report'}</button>
    </form>
  )
}
