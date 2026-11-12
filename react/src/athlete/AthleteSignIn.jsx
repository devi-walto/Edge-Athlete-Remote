// AthleteSignIn.jsx — /athlete: where an athlete signs in, every time after the first.
//
// Why this file exists: an athlete's first sign-in is through the login link their
// coach sent (LoginLinkPage.jsx); after that it is a username and password, here.
// Built to the Final designs board F_Ath_R2 (spec 03, Phase 4). There is no
// "forgot password" flow on purpose: the coach sends a new login link instead.
//
// Once signed in, the athlete goes on to their Home (spec 10), or back to the page they
// were opening when sign-in was needed.

import { useEffect, useState } from 'react'
import { Mark } from '../coach/SignIn.jsx'
import { useInstallationName } from '../useDeployment.js'
import { navigate } from '../router.js'
import { RETURN_KEY, athleteSignIn, freshAthleteToken } from './athleteAuth.js'
import { HOME_PATH } from './AthletePage.jsx'
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

  // Signed in: straight back to the page they were opening (a session link, or one of
  // their pages), else to Home. Replace, so Back doesn't return to the sign-in form.
  useEffect(() => {
    if (!signedIn) return
    let back = null
    try { back = sessionStorage.getItem(RETURN_KEY); sessionStorage.removeItem(RETURN_KEY) } catch { /* no storage */ }
    navigate(back || HOME_PATH, { replace: true })
  }, [signedIn])

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

  // Checking, or already signed in and on the way to Home.
  if (signedIn !== false) return <main className="acct-screen" />

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
