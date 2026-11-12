// AthletePage.jsx — the frame around every athlete page: the top bar, and a back link on
// a page opened from somewhere else.
//
// Why this file exists: spec 06 rules 11 and 12, on every athlete page alike. The picture
// in the top bar always goes Home; the athlete's name opens their menu (Account, Sign out);
// a drill-down page (Account, Manage sensors, later All sessions and My Recent Progress)
// has one back link under the bar. It also checks the phone is still signed in: if not,
// it goes to sign-in and comes back here afterwards. And it knows the athlete's name, so a
// page never has to fetch it just for the top bar.
//
// backFor() is the one rule for where a back link goes: a page opened from somewhere other
// than Home is told so in its address (?from=account), and its back link names that place.
import { useEffect, useState } from 'react'
import { navigate } from '../router.js'
import BackLink from '../ui/BackLink.jsx'
import TopBar from '../ui/TopBar.jsx'
import { HOME, getJson } from './athleteApi.js'
import { RETURN_KEY, athleteSignOut, freshAthleteToken } from './athleteAuth.js'
import '../coach/account.css'
import './athlete.css'

export const HOME_PATH = '/athlete/home'
export const ACCOUNT_PATH = '/athlete/account'
export const SENSORS_PATH = '/athlete/sensors'
export const SENSOR_ADD_PATH = '/athlete/sensors/add'
export const SESSIONS_PATH = '/athlete/sessions'

// The places a drill-down page can be opened from, by the word its address carries.
const FROM = {
  account: { label: 'Account', to: ACCOUNT_PATH },
  sessions: { label: 'All sessions', to: SESSIONS_PATH },
  sensors: { label: 'My sensors', to: SENSORS_PATH },
}

/** The back link for a page opened with ?from=<place>: that place, or Home. My sensors can
 *  itself have been opened from Account, so ?from=sensors&up=account goes back to My sensors
 *  with its own way back kept. */
export function backFor(search) {
  const params = new URLSearchParams(search)
  const place = FROM[params.get('from')]
  if (!place) return { label: 'Home', to: HOME_PATH }
  const up = params.get('from') === 'sensors' && FROM[params.get('up')] ? `?from=${params.get('up')}` : ''
  return { ...place, to: place.to + up }
}

/** "?from=<place>" for a link opened from `place`, or nothing from Home. */
export const fromQuery = (place) => (place && FROM[place] ? `?from=${place}` : '')

/** Not signed in (or no longer): off to sign-in, and back to `here` afterwards. */
export function toSignIn(here) {
  try { sessionStorage.setItem(RETURN_KEY, here) } catch { /* no storage: just sign in */ }
  navigate('/athlete', { replace: true })
}

// The signed-in athlete's name, remembered for this tab so every page's top bar can show it
// without asking the server again. Cleared on sign out (someone else may sign in next).
const NAME_KEY = 'athlete_name'
const remembered = () => { try { return sessionStorage.getItem(NAME_KEY) } catch { return null } }

export function signOut() {
  try { sessionStorage.removeItem(NAME_KEY) } catch { /* nothing remembered */ }
  athleteSignOut()
  navigate('/athlete', { replace: true })   // replace: Back must not show the old page
}

/** name: who is signed in, when the page already has it (Home, Account); otherwise the frame
 *  finds it: remembered for this tab, or asked of the server once. back: { label, to } on a
 *  drill-down page; here: this page's path. */
export default function AthletePage({ name, back, here, children }) {
  const [known, setKnown] = useState(remembered)
  useEffect(() => {
    if (!name) return
    setKnown(name)
    try { sessionStorage.setItem(NAME_KEY, name) } catch { /* shown, just not remembered */ }
  }, [name])
  useEffect(() => {
    if (name || known) return undefined
    let cancelled = false
    getJson(HOME).then(({ status, body }) => {
      if (!cancelled && status === 200 && body.athlete?.name) setKnown(body.athlete.name)
    })
    return () => { cancelled = true }
  }, [name, known])

  useEffect(() => {
    let cancelled = false
    freshAthleteToken().then((token) => { if (!cancelled && !token) toSignIn(here) })
    return () => { cancelled = true }
  }, [here])

  return <main className="athlete-app">
    <header className="athlete-app-bar">
      <TopBar name={name || known || '…'} onHome={() => navigate(HOME_PATH)} menuItems={[
        { label: 'Account', hint: 'Your name, teams and sensor', onSelect: () => navigate(ACCOUNT_PATH) },
        { label: 'Sign out', hint: 'This phone only', onSelect: signOut },
      ]} />
    </header>
    {back && <BackLink label={back.label} onBack={() => navigate(back.to)} />}
    <div className="athlete-app-body">{children}</div>
  </main>
}
