// Why this file exists: Coaches and Change password are about a coach's LOGIN, not about
// training, so they do not belong under Planning, Session or Analytics. This is the
// small frame those two pages sit in: the same top bar and bottom navbar as the rest of
// the coach workspace, so a coach never feels they have left it, and one press on the
// navbar takes them back.
//
// It also owns the two checks every page here needs: is somebody signed in, and (for
// Coaches) are they an administrator. Neither check is security. The server decides
// who may do what; these only choose what to draw.
import { useEffect, useState } from 'react'
import { navigate } from '../router.js'
import { fetchCurrentCoach, getCoachToken, setCoachToken } from './api.js'
import { pathForCoachState, resumeCoachState } from './coachState.js'
import AccountMenu, { COACHES_PATH, PASSWORD_PATH } from './AccountMenu.jsx'
import ChangePassword from './ChangePassword.jsx'
import Coaches from './Coaches.jsx'
import SignIn from './SignIn.jsx'
import StateNavbar from './StateNavbar.jsx'
import './account.css'

export default function AccountPage({ page }) {
  const [token, setToken] = useState(() => getCoachToken())
  const [me, setMe] = useState(null)
  const [error, setError] = useState('')

  const back = () => navigate(pathForCoachState(resumeCoachState()))
  // Logging out here goes back to the workspace's address, so whoever signs in next
  // lands on the workspace, not on a page about the previous coach's account.
  function signOut() { setCoachToken(null); setToken(null); setMe(null); back() }

  useEffect(() => {
    if (!token) return undefined
    let cancelled = false
    setError('')
    fetchCurrentCoach(token)
      .then((reply) => { if (!cancelled) setMe(reply) })
      .catch((err) => { if (cancelled) return; if (err.status === 401) signOut(); else setError(err.message || 'The server could not be reached.') })
    return () => { cancelled = true }
  }, [token])

  if (!token) return <SignIn onSignedIn={setToken} />
  // A temporary password comes first, whatever page was asked for.
  if (me?.must_change_password) {
    return <ChangePassword accessToken={token} forced onLogout={signOut}
      onChanged={() => setMe({ ...me, must_change_password: false })} />
  }
  if (page === 'password') {
    return <ChangePassword accessToken={token} onChanged={back} onCancel={back} />
  }

  return <main className="acct-page">
    <header className="acct-topbar">
      <AccountMenu me={me} onLogout={signOut} />
      <div className="acct-topbar-title"><span className="acct-label">Account</span><b>Coaches</b></div>
    </header>
    {error && <section className="acct-body"><p className="acct-error" role="alert">{error}</p></section>}
    {me && !me.is_staff && <section className="acct-body">
      <p className="acct-note" role="alert">Only an administrator can manage coach logins. Ask an administrator if you need a password reset.</p>
      <div><button type="button" className="acct-solid" onClick={back}>Back to the workspace</button></div>
    </section>}
    {me?.is_staff && <Coaches accessToken={token} me={me} onLogout={signOut} onChangePassword={() => navigate(PASSWORD_PATH)} />}
    <StateNavbar current={null} onSelect={(key) => navigate(pathForCoachState(key))} daySet />
  </main>
}

export function accountPageFromPath(pathname) {
  if (pathname === COACHES_PATH) return 'coaches'
  if (pathname === PASSWORD_PATH) return 'password'
  return null
}
