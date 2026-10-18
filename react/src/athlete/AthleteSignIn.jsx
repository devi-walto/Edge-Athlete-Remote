// AthleteSignIn.jsx — /athlete: where an athlete signs in, every time after the first.
//
// Why this file exists: an athlete's first sign-in is through the login link their
// coach sent (LoginLinkPage.jsx); after that it is a username and password, here.
// Built to the Final designs board F_Ath_R2 (spec 03, Phase 4). There is no
// "forgot password" flow on purpose: the coach sends a new login link instead.
//
// Once signed in, this page says so and points at the session link, until the
// athlete's own home page exists (spec 10).

import { useEffect, useState } from 'react'
import { Mark } from '../coach/SignIn.jsx'
import { useInstallationName } from '../useDeployment.js'
import { navigate } from '../router.js'
import { athleteSignIn, athleteSignOut, freshAthleteToken } from './athleteAuth.js'
import '../coach/account.css'
import './athlete.css'

/** The top of every athlete card: the mark, "Edge Athlete", and the school's name. */
export function AthleteBrand() {
  const school = useInstallationName()
  return <div className="acct-mark-row"><Mark />
    <div className="acct-mark-name"><b>Edge Athlete</b><span>{school || 'Athlete'}</span></div>
  </div>
}

export default function AthleteSignIn() {
  // null while checking whether this phone is already signed in.
  const [signedIn, setSignedIn] = useState(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    freshAthleteToken().then((token) => { if (!cancelled) setSignedIn(Boolean(token)) })
    return () => { cancelled = true }
  }, [])

  async function submit(event) {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError('')
    const result = await athleteSignIn(username.trim(), password)
    setBusy(false)
    setPassword('')
    if (result.status === 'signed-in') setSignedIn(true)
    else if (result.status === 'coach') setError('That is a coach login. Coaches sign in on the coach sign-in page.')
    else setError(result.message)
  }

  if (signedIn === null) return <main className="acct-screen" />

  if (signedIn) {
    return <main className="acct-screen">
      <section className="acct-card">
        <AthleteBrand />
        <h1>You're signed in</h1>
        <p className="acct-note athlete-lead">Open the session link your coach sent to join today's training.</p>
        <button type="button" className="acct-solid"
          onClick={() => { athleteSignOut(); setSignedIn(false) }}>Sign out</button>
      </section>
    </main>
  }

  return <main className="acct-screen athlete-screen">
    <form className="acct-card" onSubmit={submit}>
      <AthleteBrand />
      <h1>Athlete sign in</h1>
      {error && <p className="acct-error" role="alert">{error}</p>}
      <label className="acct-field">Username
        <input type="text" autoComplete="username" autoCapitalize="none" maxLength={150} required
          value={username} disabled={busy} onChange={(e) => setUsername(e.target.value)} />
      </label>
      <label className="acct-field">Password
        <input type="password" autoComplete="current-password" maxLength={1024} required
          value={password} disabled={busy} onChange={(e) => setPassword(e.target.value)} />
      </label>
      <button className="acct-primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
      <p className="acct-note athlete-center">Forgot it? Ask your coach for a new login link.</p>
    </form>
    <button type="button" className="acct-quiet athlete-switch" onClick={() => navigate('/coach')}>
      Coach? Coach sign in
    </button>
  </main>
}
