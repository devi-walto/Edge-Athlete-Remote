// SessionPage.jsx — /session/<id>: an athlete opens the session link their coach shared.
//
// Why this file exists: this is the online athlete's whole workout (spec 04, Phase 3).
// Opening the link: not signed in → sign in, then straight back here. Signed in →
// join the session, which gives the athlete their own rack, already checked in
// (services/session_join.py on the server), and then the SAME rack screen a gym uses
// (RackScreen.jsx). There is no second rack screen: a rack with an owner simply skips
// choosing a lifter.
//
// Before the rack, joining can answer three other ways, each its own page from the
// Final designs boards:
//   F_Ath_R4   the coach hasn't started the session yet: wait here, it checks again
//   F_Ath_R4b  you're not on this session
//   F_Ath_R10  the session has ended (also shown when the coach ends it mid-workout)
// The plan list on R4 and the summary on R10 come with the athlete's home page
// (spec 10); these pages say what happened and what to do.
//
// Unlike a gym rack tablet (RackLive in App.jsx), this never signs anyone out and
// never turns the phone into a rack tablet: no rack setup, no device role.

import { useCallback, useEffect, useRef, useState } from 'react'
import RackScreen from '../rack/RackScreen.jsx'
import RackObserver from '../rack/RackObserver.jsx'
import { useRackController } from '../rack/controller.js'
import { getActiveSession, getSessionStatus, signInHeaders } from '../api/client.js'
import { getDeviceId } from '../device.js'
import { navigate } from '../router.js'
import { Centered } from '../ui.jsx'
import { T } from '../theme.js'
import { RETURN_KEY, athleteSignOut, freshAthleteToken } from './athleteAuth.js'
import '../coach/account.css'
import './athlete.css'


export function sessionIdFromPath(pathname) {
  const match = /^\/session\/(\d+)\/?$/.exec(pathname)
  return match ? Number(match[1]) : null
}

const WAIT_RECHECK_MS = 5000      // R4: how often to ask "has it started?"
const ENDED_CHECK_MS = 10000      // while lifting: how often to ask "is it still on?"

async function call(url, method = 'GET') {
  try {
    const response = await fetch(url, {
      method, headers: { Accept: 'application/json', ...(await signInHeaders()) },
    })
    return { status: response.status, body: await response.json().catch(() => ({})) }
  } catch {
    return { status: 0, body: {} }
  }
}

/** The top bar every athlete page shares: their mark and their name. */
function AthleteBar({ name }) {
  return <header className="athlete-bar">
    <span className="athlete-avatar" aria-hidden="true">●</span>
    <b>{name || ''}</b>
  </header>
}

function Notice({ title, children }) {
  return <section className="athlete-notice" role="status"><h1>{title}</h1><p>{children}</p></section>
}

export default function SessionPage({ sessionId }) {
  const [name, setName] = useState('')
  // checking | joined | waiting | not-on-session | ended | offline
  const [state, setState] = useState({ kind: 'checking' })
  const retryRef = useRef(null)

  const join = useCallback(async () => {
    clearTimeout(retryRef.current)
    const token = await freshAthleteToken()
    if (!token) {
      // Not signed in (or the 30 days ran out): sign in, then come straight back.
      sessionStorage.setItem(RETURN_KEY, `/session/${sessionId}`)
      navigate('/athlete', { replace: true })
      return
    }
    const { status, body } = await call(`/api/sessions/${sessionId}/join/`, 'POST')
    if (status === 200) {
      const sensor = body.sensor
      setState({
        kind: 'joined',
        rackNumber: body.rack_number,
        // The rack screen's view of a sensor; online the server named it at join.
        node: sensor ? { id: sensor.id, node_id: sensor.node_id, rack_number: body.rack_number,
          acquisition_kind: 'mqtt', is_active: true } : null,
      })
    } else if (status === 409 && body.code === 'not_started') {
      setState({ kind: 'waiting', session: body.session })
      retryRef.current = setTimeout(join, WAIT_RECHECK_MS)
    } else if (status === 409 && body.code === 'ended') {
      setState({ kind: 'ended', session: body.session })
    } else if (status === 403) {
      setState({ kind: 'not-on-session' })
    } else if (status === 401) {
      athleteSignOut()
      sessionStorage.setItem(RETURN_KEY, `/session/${sessionId}`)
      navigate('/athlete', { replace: true })
    } else {
      setState({ kind: 'offline' })
      retryRef.current = setTimeout(join, WAIT_RECHECK_MS)
    }
  }, [sessionId])

  // Stable, so the "is it still on?" check in SessionRack isn't restarted on each render.
  const showEnded = useCallback(() => setState({ kind: 'ended' }), [])

  useEffect(() => {
    join()
    call('/api/auth/me/').then(({ body }) => setName(body.athlete_name || ''))
    return () => clearTimeout(retryRef.current)
  }, [join])

  if (state.kind === 'joined') {
    return <SessionRack sessionId={sessionId} rackNumber={state.rackNumber} node={state.node}
      onEnded={showEnded} />
  }

  const label = state.session?.label
  return <main className="athlete-page">
    <AthleteBar name={name} />
    <div className="athlete-body">
      {state.kind === 'checking' && <p className="acct-note">Opening your rack…</p>}

      {state.kind === 'waiting' && <>
        {label && <section className="athlete-card"><span>Training session</span><h2>{label}</h2></section>}
        <Notice title="Your coach hasn't started this session yet">
          Stay on this page. It checks again every few seconds and opens your rack when the
          session starts.
        </Notice>
      </>}

      {state.kind === 'not-on-session' && <>
        <Notice title="You're not on this session">
          This link is for a session you are not part of. Ask your coach.
        </Notice>
        <button type="button" className="acct-solid" onClick={() => navigate('/athlete')}>Back</button>
      </>}

      {state.kind === 'ended' && <>
        <section className="athlete-card">
          <span>Session ended</span>
          {label && <h2>{label}</h2>}
          <p>Your coach ended the session. Everything is saved.</p>
        </section>
        <button type="button" className="acct-quiet athlete-signout"
          onClick={() => { athleteSignOut(); navigate('/athlete') }}>Sign out</button>
      </>}

      {state.kind === 'offline' && <Notice title="Can’t reach Edge Athlete">
        Check your connection. This page tries again by itself.
      </Notice>}
    </div>
  </main>
}

/** The athlete's own rack: the gym's rack screen, on a rack the server made for them. */
function SessionRack({ sessionId, rackNumber, node, onEnded }) {
  const controller = useRackController(rackNumber, getDeviceId(), true, true)
  const [session, setSession] = useState(null)
  const [sessionError, setSessionError] = useState(false)

  useEffect(() => {
    if (controller.mode !== 'controller' || session) return
    getActiveSession().then(setSession).catch(() => setSessionError(true))
  }, [controller.mode, session])

  // Ending the session removes this rack on the server. Ask now and then whether
  // our session is still the one running, and say so when it isn't.
  useEffect(() => {
    const check = () => getSessionStatus()
      .then((status) => { if (status.session_id !== sessionId) onEnded() })
      .catch(() => {})
    const interval = setInterval(check, ENDED_CHECK_MS)
    return () => clearInterval(interval)
  }, [sessionId, onEnded])

  if (controller.mode === 'observer') {
    // Another tab of theirs holds the rack; this one takes it back by itself.
    return <RackObserver snapshot={controller.snapshot} reason={controller.reason}
      canRecover={controller.canRecover} onRecover={controller.recover} />
  }
  if (controller.mode === 'checking' || (session == null && !sessionError)) {
    return <Centered><div style={{ fontSize: 16, color: T.muted }}>Opening your rack…</div></Centered>
  }
  return <RackScreen rackNumber={rackNumber} session={session} node={node} controller={controller} />
}
