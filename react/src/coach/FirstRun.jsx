// Why this file exists: a brand-new installation has no logins at all, so somebody has
// to become its first administrator. If the website simply let the first visitor do it,
// a student who found the address first would own the gym's system. So the first
// administrator has to type a one-time setup code, and that code is only ever printed
// by a command run on the machine itself (`manage.py setup_code`).
//
// This is that screen. It appears instead of the whole app while the installation is
// unclaimed, and never again afterwards.
//
// The checks and the submit logic are Braydon's, from the coach-accounts work; the
// layout follows the Final design board `F_FirstRun`.
import { useState } from 'react'
import { coachFetch, setCoachToken } from './api.js'
import { Mark } from './SignIn.jsx'
import useDeployment, { useInstallationName } from '../useDeployment.js'
import './account.css'

// Only shown on a local install: there, whoever installed it can run this on the
// box. Online, nobody claiming a school has access to the server, so the screen
// tells them to ask Edge Athlete support instead.
const COMMAND = 'docker compose exec django python manage.py setup_code'

export default function FirstRun({ codePending, onRecheck, onClaimed, onAlreadyClaimed }) {
  const remote = useDeployment() === 'remote'
  // "Welcome to Demo U": which installation is being claimed, when the server
  // knows its name (set per school online; a local install has none).
  const installationName = useInstallationName()
  const [code, setCode] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [again, setAgain] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(event) {
    event.preventDefault()
    if (busy) return
    if (password !== again) { setError('The passwords do not match.'); return }
    setBusy(true)
    setError('')
    try {
      const reply = await coachFetch('/api/auth/setup/', {
        method: 'POST',
        body: { username: username.trim(), password, setup_code: code.trim() },
      })
      setCoachToken(reply.access)
      setPassword(''); setAgain(''); setCode('')
      onClaimed(reply.access)
    } catch (err) {
      // 409: someone else finished setup while this form was open. Nothing is lost;
      // this device just needs the sign-in screen instead.
      if (err.status === 409) { onAlreadyClaimed(); return }
      // The server names the field it is unhappy with ("setup_code: …"). The form
      // already shows which field is which, so drop the label and keep the sentence.
      setError((err.message || 'Setup could not be completed. Please try again.').replace(/^(setup_code|username|password):\s*/i, ''))
    } finally {
      setBusy(false)
    }
  }

  return <main className="acct-screen"><div className="acct-setup">
    <div className="acct-setup-why">
      <Mark large />
      <h1>{installationName ? `Welcome to ${installationName}` : 'Set up this installation'}</h1>
      <p>Nobody has claimed this installation yet. Enter its one-time setup code to create the first administrator.</p>
      <div className="acct-steps">
        <span className="acct-label">Where the code comes from</span>
        <div className="acct-step"><b>1</b><span>It is printed by a command run on the machine itself, never shown on this site.</span></div>
        <div className="acct-step"><b>2</b><span>On a gym base station, whoever installed it has the code. Online, the person who created your installation sends it to you.</span></div>
        <div className="acct-step"><b>3</b><span>It works once and expires. After that this screen never appears again.</span></div>
      </div>
    </div>
    <form className="acct-card" onSubmit={submit}>
      {!codePending && <p className="acct-hint" role="note">
        {remote
          ? <>No setup code has been issued yet. Ask Edge Athlete support to issue one.<br /></>
          : <>No setup code has been issued yet. On the machine, run:<br /><code>{COMMAND}</code><br /></>}
        <button type="button" className="acct-quiet is-strong" style={{ paddingLeft: 0 }} disabled={busy} onClick={onRecheck}>I&rsquo;ve run it — check again</button>
      </p>}
      {error && <p className="acct-error" role="alert">{error}</p>}
      <label className="acct-field">Setup code
        <input className="is-code" type="text" autoComplete="one-time-code" placeholder="XXXX-XXXX" maxLength={64} required value={code} disabled={busy} onChange={(e) => setCode(e.target.value)} />
      </label>
      <label className="acct-field">Choose a username
        <input type="text" autoComplete="username" maxLength={150} required value={username} disabled={busy} onChange={(e) => setUsername(e.target.value)} />
      </label>
      <label className="acct-field">Choose a password
        <input type="password" autoComplete="new-password" maxLength={1024} required value={password} disabled={busy} onChange={(e) => setPassword(e.target.value)} />
      </label>
      <label className="acct-field">Type the password again
        <input type="password" autoComplete="new-password" required value={again} disabled={busy} onChange={(e) => setAgain(e.target.value)} />
      </label>
      <button className="acct-primary" disabled={busy}>{busy ? 'Please wait…' : 'Create administrator'}</button>
      <p className="acct-note">You will be the first administrator. You can add the other coaches afterwards.</p>
    </form>
  </div></main>
}
