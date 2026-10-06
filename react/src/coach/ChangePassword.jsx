// Why this file exists: a coach's first password is chosen by an administrator and read
// out or written down, so two people know it. This screen is where the coach replaces it
// with one only they know. It appears on its own, in place of the workspace, straight
// after signing in with a temporary password (`forced`), and the server refuses every
// coach route until it is done. The same screen is reachable any time from the account
// menu, for a coach who simply wants a new password.
//
// The logic is Braydon's, from the coach-accounts work. There is no Final design board
// for this screen, so it uses the sign-in card.
import { useState } from 'react'
import { changePassword } from './api.js'
import { Mark } from './SignIn.jsx'
import './account.css'

export default function ChangePassword({ accessToken, forced = false, onChanged, onCancel, onLogout }) {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [again, setAgain] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(event) {
    event.preventDefault()
    if (busy) return
    if (next !== again) { setError('The new passwords do not match.'); return }
    setBusy(true)
    setError('')
    try {
      await changePassword(accessToken, current, next)
      setCurrent(''); setNext(''); setAgain('')
      onChanged()
    } catch (err) {
      setError(err.message || 'The password could not be changed.')
    } finally {
      setBusy(false)
    }
  }

  return <main className="acct-screen"><form className="acct-card" onSubmit={submit}>
    <div className="acct-mark-row"><Mark /><div className="acct-mark-name"><b>Edge Athlete</b><span>Coach workspace</span></div></div>
    <h1>{forced ? 'Choose your own password' : 'Change password'}</h1>
    <p className="acct-note">{forced
      ? 'Your login was created with a temporary password. Replace it before continuing.'
      : 'Update the password you use to sign in.'}</p>
    {error && <p className="acct-error" role="alert">{error}</p>}
    <label className="acct-field">{forced ? 'Temporary password' : 'Current password'}
      <input type="password" autoComplete="current-password" required value={current} disabled={busy} onChange={(e) => setCurrent(e.target.value)} />
    </label>
    <label className="acct-field">New password
      <input type="password" autoComplete="new-password" maxLength={1024} required value={next} disabled={busy} onChange={(e) => setNext(e.target.value)} />
    </label>
    <label className="acct-field">New password again
      <input type="password" autoComplete="new-password" required value={again} disabled={busy} onChange={(e) => setAgain(e.target.value)} />
    </label>
    <button className="acct-primary" disabled={busy}>{busy ? 'Saving…' : 'Save password'}</button>
    {!forced && onCancel && <button type="button" className="acct-quiet" disabled={busy} onClick={onCancel}>Cancel</button>}
    {forced && onLogout && <button type="button" className="acct-quiet" disabled={busy} onClick={onLogout}>Sign in as someone else</button>}
  </form></main>
}
