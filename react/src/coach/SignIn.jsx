// Why this file exists: this is the one place a coach types a username and password.
// It replaces two older forms, one of which arrived with "coach" and "coachpass" already
// typed in. That was fine on a closed gym network and is an open door on the internet,
// so this form always starts empty.
//
// There is no "forgot password" link on purpose. An administrator resets a coach's
// password from the Coaches page and hands over a temporary one; no email is collected.
//
// The sign-in logic (and its plain-language error messages) is Braydon's, from the
// coach-accounts work; the layout follows the Final design board `F_SignIn`.
import { useState } from 'react'
import { coachLogin } from './api.js'
import './account.css'

export function Mark({ large = false }) {
  return <span className={`acct-mark${large ? ' is-large' : ''}`} aria-hidden="true">EA</span>
}

export default function SignIn({ onSignedIn, embedded = false }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(event) {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError('')
    try {
      const token = await coachLogin(username.trim(), password)
      setPassword('')
      onSignedIn(token)
    } catch (err) {
      setError(err.message || 'Unable to sign in. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const card = <form className={`acct-card${embedded ? ' is-embedded' : ''}`} onSubmit={submit}>
    <div className="acct-mark-row"><Mark /><div className="acct-mark-name"><b>Edge Athlete</b><span>Coach workspace</span></div></div>
    <h1>Coach sign in</h1>
    {error && <p className="acct-error" role="alert">{error}</p>}
    <label className="acct-field">Username
      <input type="text" autoComplete="username" maxLength={150} required value={username} disabled={busy} onChange={(e) => setUsername(e.target.value)} />
    </label>
    <label className="acct-field">Password
      <input type="password" autoComplete="current-password" maxLength={1024} required value={password} disabled={busy} onChange={(e) => setPassword(e.target.value)} />
    </label>
    <button className="acct-primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
    <p className="acct-note">Forgot your password? Ask an administrator to reset it. They will give you a temporary one to change when you sign in.</p>
  </form>
  return embedded ? card : <main className="acct-screen">{card}</main>
}
