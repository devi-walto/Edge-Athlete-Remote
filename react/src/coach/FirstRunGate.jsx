// Why this file exists: nothing in the app should run on an installation nobody has
// claimed. This wraps the whole app and asks the server one question before showing
// anything: "has this installation been set up?" If not, every device sees the
// first-run screen, rack tablets included.
//
// One exception, and it is Braydon's: a device that has already seen a set-up
// installation remembers that, so a rack tablet whose network drops mid-session can
// still reopen its screen. That remembered flag only decides what is DRAWN. It grants
// nothing: every coach route still needs a login the server issued.
//
// The logic is Braydon's `FirstRunSetup`, from the coach-accounts work.
import { useEffect, useState } from 'react'
import { coachFetch } from './api.js'
import { navigate } from '../router.js'
import FirstRun from './FirstRun.jsx'
import { Mark } from './SignIn.jsx'
import './account.css'

const COMPLETE_KEY = 'edge_setup_complete'

export default function FirstRunGate({ children }) {
  const [state, setState] = useState('loading')   // loading | ready | setup | error
  const [codePending, setCodePending] = useState(false)

  async function check() {
    setState('loading')
    try {
      const reply = await coachFetch('/api/auth/setup/')
      setCodePending(Boolean(reply.setup_code_pending))
      if (reply.setup_required) localStorage.removeItem(COMPLETE_KEY)
      else localStorage.setItem(COMPLETE_KEY, 'true')
      setState(reply.setup_required ? 'setup' : 'ready')
    } catch {
      setState(localStorage.getItem(COMPLETE_KEY) === 'true' ? 'ready' : 'error')
    }
  }
  useEffect(() => { check() }, [])

  function claimed() {
    localStorage.setItem(COMPLETE_KEY, 'true')
    navigate('/coach')
    setState('ready')
  }

  if (state === 'ready') return children
  if (state === 'setup') {
    return <FirstRun codePending={codePending} onRecheck={check} onClaimed={claimed}
      onAlreadyClaimed={() => { localStorage.setItem(COMPLETE_KEY, 'true'); setState('ready') }} />
  }
  return <main className="acct-screen"><section className="acct-card">
    <div className="acct-mark-row"><Mark /><div className="acct-mark-name"><b>Edge Athlete</b><span>Starting up</span></div></div>
    <p className={state === 'error' ? 'acct-error' : 'acct-note'} role={state === 'error' ? 'alert' : 'status'}>
      {state === 'error' ? 'The server could not be reached.' : 'Checking this installation…'}
    </p>
    {state === 'error' && <button type="button" className="acct-primary" onClick={check}>Retry connection</button>}
  </section></main>
}
