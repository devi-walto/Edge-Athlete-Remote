// LoginLinkPage.jsx — /login-link#<link>: an athlete opens the link their coach sent.
//
// Why this file exists: it is how an athlete gets a login at all (spec 03). The page
// greets them by name ("Hi Chris"), they choose a username and password, and they
// are signed in. Built to the Final designs boards F_Ath_R1 and, for a link that no
// longer works, F_Ath_R1b.
//
// The link sits after a "#", which a browser never sends to the server, so the
// secret stays out of every request log. This page reads it, then wipes it from the
// address bar, so it isn't left in the browser's history either.

import { useEffect, useState } from 'react'
import { navigate } from '../router.js'
import { AthleteBrand } from './AthleteSignIn.jsx'
import { lookupLoginLink, redeemLoginLink } from './athleteAuth.js'
import '../coach/account.css'
import './athlete.css'

function readAndWipeLink() {
  const link = decodeURIComponent(window.location.hash.slice(1))
  if (window.location.hash) {
    window.history.replaceState(window.history.state, '', window.location.pathname)
  }
  return link
}

const firstName = (name) => name.split(' ')[0]

export default function LoginLinkPage() {
  // Read once, on the first render, before anything can wipe it.
  const [link] = useState(readAndWipeLink)
  // checking → form | dead | too-many | offline
  const [state, setState] = useState('checking')
  const [name, setName] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [again, setAgain] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [fields, setFields] = useState({})

  useEffect(() => {
    let cancelled = false
    lookupLoginLink(link).then((result) => {
      if (cancelled) return
      if (result.status === 'found') { setName(result.name); setState('form') }
      else setState(result.status)
    })
    return () => { cancelled = true }
  }, [link])

  async function submit(event) {
    event.preventDefault()
    if (busy) return
    setError('')
    setFields({})
    if (password !== again) { setFields({ again: ['The two passwords are not the same.'] }); return }
    setBusy(true)
    const result = await redeemLoginLink(link, username.trim(), password)
    setBusy(false)
    if (result.status === 'signed-in') { navigate('/athlete', { replace: true }); return }
    if (result.status === 'fields') { setFields(result.fields); setError(result.message); return }
    if (result.status === 'too-many') { setError('Too many tries. Wait a minute, then try again.'); return }
    if (result.status === 'offline') { setError('The server could not be reached. Try again.'); return }
    setState('dead')
  }

  if (state === 'checking') return <main className="acct-screen" />

  if (state !== 'form') {
    const message = state === 'too-many'
      ? ['Too many tries', 'Wait a minute, then open the link again.']
      : state === 'offline'
        ? ['Can’t reach Edge Athlete', 'Check your connection, then open the link again.']
        : ["This link doesn't work any more", 'Ask your coach for a new one.']
    return <main className="acct-screen athlete-screen">
      <section className="acct-card" role="alert">
        <AthleteBrand />
        <h1>{message[0]}</h1>
        <p className="acct-note athlete-lead">{message[1]}</p>
        <button type="button" className="acct-solid" onClick={() => navigate('/athlete')}>
          I already have a login
        </button>
      </section>
    </main>
  }

  const fieldError = (key) => fields[key] && <span className="athlete-field-error">{fields[key].join(' ')}</span>

  return <main className="acct-screen athlete-screen">
    <form className="acct-card" onSubmit={submit}>
      <AthleteBrand />
      <h1>Hi {firstName(name)}</h1>
      <p className="acct-note athlete-lead">
        Your coach sent you this link. Choose a username and password. You will use them to join
        training sessions.
      </p>
      {error && <p className="acct-error" role="alert">{error}</p>}
      <label className="acct-field">Username
        <input type="text" autoComplete="username" autoCapitalize="none" maxLength={150} required
          value={username} disabled={busy} onChange={(e) => setUsername(e.target.value)} />
        {fieldError('username')}
      </label>
      <label className="acct-field">Password
        <input type="password" autoComplete="new-password" maxLength={1024} required
          value={password} disabled={busy} onChange={(e) => setPassword(e.target.value)} />
        {fieldError('password')}
      </label>
      <label className="acct-field">Password again
        <input type="password" autoComplete="new-password" maxLength={1024} required
          value={again} disabled={busy} onChange={(e) => setAgain(e.target.value)} />
        {fieldError('again')}
      </label>
      <button className="acct-primary" disabled={busy}>{busy ? 'Creating…' : 'Create my login'}</button>
      <p className="acct-note athlete-center">This link works once.</p>
    </form>
  </main>
}
