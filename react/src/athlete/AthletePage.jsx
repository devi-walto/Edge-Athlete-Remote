// AthletePage.jsx — the frame around every athlete page: the top bar, and a back link on
// a page opened from somewhere else.
//
// Why this file exists: spec 06 rules 11 and 12, on every athlete page alike. The picture
// in the top bar always goes Home; the athlete's name opens their menu (Account, Sign out);
// a drill-down page (Account, Manage sensors, later All sessions and My Recent Progress)
// has one back link under the bar. It also checks the phone is still signed in: if not,
// it goes to sign-in and comes back here afterwards.
import { useEffect } from 'react'
import { navigate } from '../router.js'
import BackLink from '../ui/BackLink.jsx'
import TopBar from '../ui/TopBar.jsx'
import { RETURN_KEY, athleteSignOut, freshAthleteToken } from './athleteAuth.js'
import '../coach/account.css'
import './athlete.css'

export const HOME_PATH = '/athlete/home'
export const ACCOUNT_PATH = '/athlete/account'
export const SENSORS_PATH = '/athlete/sensors'

/** Not signed in (or no longer): off to sign-in, and back to `here` afterwards. */
export function toSignIn(here) {
  try { sessionStorage.setItem(RETURN_KEY, here) } catch { /* no storage: just sign in */ }
  navigate('/athlete', { replace: true })
}

export function signOut() {
  athleteSignOut()
  navigate('/athlete', { replace: true })   // replace: Back must not show the old page
}

/** name: who is signed in; back: { label, to } on a drill-down page; here: this page's path. */
export default function AthletePage({ name, back, here, children }) {
  useEffect(() => {
    let cancelled = false
    freshAthleteToken().then((token) => { if (!cancelled && !token) toSignIn(here) })
    return () => { cancelled = true }
  }, [here])

  return <main className="athlete-app">
    <header className="athlete-app-bar">
      <TopBar name={name || '…'} onHome={() => navigate(HOME_PATH)} menuItems={[
        { label: 'Account', hint: 'Your name, teams and sensor', onSelect: () => navigate(ACCOUNT_PATH) },
        { label: 'Sign out', hint: 'This phone only', onSelect: signOut },
      ]} />
    </header>
    {back && <BackLink label={back.label} onBack={() => navigate(back.to)} />}
    <div className="athlete-app-body">{children}</div>
  </main>
}
