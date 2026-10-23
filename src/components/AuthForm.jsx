import { useState } from 'react'
import { createApi } from '../api'

export default function AuthForm({ onLogin }) {
  const [register, setRegister] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [accountCreated, setAccountCreated] = useState(false)
  async function submit(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setBusy(true)
    setError('')
    try {
      const api = createApi()
      if (register) {
        await api('/auth/register', { method: 'POST', body: {
          name: form.get('name'), email: form.get('email'), password: form.get('password'),
        } })
        setRegister(false)
        setAccountCreated(true)
      }
      const result = await api('/auth/login', { method: 'POST', body: new URLSearchParams({
        username: form.get('email'), password: form.get('password'),
      }) })
      onLogin(result.access_token)
    } catch (error) {
      setError(error.message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <form className="form-stack" onSubmit={submit}>
      <p>{accountCreated ? 'Account created. Sign in if automatic login did not complete.' :
        'Sign in to browse campus reports, share an item, and contact its reporter.'}</p>
      {register && <label>Full name<input name="name" required maxLength={100} autoComplete="name" /></label>}
      <label>Email<input name="email" type="email" required autoComplete="username" /></label>
      <label>Password<input name="password" type="password" required minLength={register ? 12 : 1}
        maxLength={128} autoComplete={register ? 'new-password' : 'current-password'} /></label>
      {register && <small>Use at least 12 characters for your password.</small>}
      {error && <p className="error-message" role="alert">{error}</p>}
      <button className="button primary" disabled={busy}>{busy ? 'Please wait...' : register ? 'Create account' : 'Sign in'}</button>
      <button type="button" className="details-link" disabled={busy} onClick={() => {
        setRegister(!register)
        setError('')
      }}>{register ? 'Already have an account? Sign in' : 'New here? Create an account'}</button>
    </form>
  )
}
