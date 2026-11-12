// Home.jsx — /athlete/home: the first thing an online athlete sees after signing in.
//
// Why this file exists: before it, signing in landed on a page telling the athlete to go
// find the session link their coach sent. Home answers what they open the app for, from
// their own groups only (spec 10, Phase 1; boards F_Ath_H1, H1b, H1c):
//   - a greeting with their groups;
//   - the one focus card: the session that's live now with Join session inside it, or the
//     next one coming up, or "nothing scheduled yet";
//   - My sensor;
//   - their last five sessions, sets done against sets planned (amber when short); each
//     opens that session, and View all sessions lists every one (Phase 3).
// It asks the server again every 15 seconds while it's on screen, so the card turns live
// by itself when the coach starts the day, and stops asking while the tab is hidden.
import { useCallback, useEffect, useState } from 'react'
import { navigate } from '../router.js'
import Button from '../ui/Button.jsx'
import FocusCard from '../ui/FocusCard.jsx'
import SectionLabel from '../ui/SectionLabel.jsx'
import AthletePage, { HOME_PATH, toSignIn } from './AthletePage.jsx'
import { HOME, dayLabel, getJson, timeLabel } from './athleteApi.js'
import SensorRow from './SensorRow.jsx'
import SessionRow, { SESSIONS_PATH, SetsCount } from './SessionRow.jsx'

export { SetsCount }

export const REFRESH_MS = 15000

const join = (...parts) => parts.flat().filter(Boolean).join(' · ')

/** The focus card: live, next, or nothing planned. */
export function Banner({ live, comingUp }) {
  if (live) {
    return <FocusCard className="athlete-banner"
      label={<span className="athlete-live"><span className="athlete-live-dot" aria-hidden="true" />Live now · started {timeLabel(live.started_at)}</span>}
      title={live.title} detail={join(live.groups, live.movements)}>
      <Button kind="primary" className="athlete-join" onClick={() => navigate(`/session/${live.session_id}`)}>Join session</Button>
    </FocusCard>
  }
  const [next, then] = comingUp || []
  if (!next) {
    return <FocusCard className="athlete-banner" label="Next" title="Nothing scheduled yet"
      detail="Your coach will add your sessions here." />
  }
  return <FocusCard className="athlete-banner" label={`Next · ${dayLabel(next.date)}`} title={next.title}
    detail={<>
      <span>{join(next.groups, next.movements)}</span>
      <span className="athlete-banner-hint">A Join button appears here when your coach starts it.
        {then && ` Then: ${dayLabel(then.date)} · ${then.title}`}</span>
    </>} />
}

export default function Home() {
  const [home, setHome] = useState(null)
  const [offline, setOffline] = useState(false)

  const load = useCallback(async () => {
    const { status, body } = await getJson(HOME)
    if (status === 401 || status === 403) { toSignIn(HOME_PATH); return }
    if (status !== 200) { setOffline(true); return }
    setOffline(false)
    setHome(body)
  }, [])

  useEffect(() => {
    load()
    const tick = setInterval(() => { if (document.visibilityState === 'visible') load() }, REFRESH_MS)
    const back = () => { if (document.visibilityState === 'visible') load() }
    document.addEventListener('visibilitychange', back)
    return () => { clearInterval(tick); document.removeEventListener('visibilitychange', back) }
  }, [load])

  return <AthletePage name={home?.athlete.name} here={HOME_PATH}>
    {offline && <p className="acct-error" role="alert">The school's server didn't answer. Trying again…</p>}
    {home && <>
      <section className="athlete-greeting">
        <span className="athlete-greeting-label">Signed in</span>
        <h1>Hi {home.athlete.first_name}</h1>
        <span className="athlete-greeting-groups">{home.athlete.groups.join(' · ')}</span>
      </section>
      <Banner live={home.live} comingUp={home.coming_up} />
      <SensorRow />
      <section aria-labelledby="recent-label">
        <SectionLabel as="h2"><span id="recent-label">Recent sessions</span></SectionLabel>
        {home.recent.length === 0
          ? <p className="athlete-empty">Your sessions will show here after you lift.</p>
          : <>
            {home.recent.map((s) => <SessionRow key={s.session_id} session={s} />)}
            <Button kind="quiet" className="athlete-view-all" onClick={() => navigate(SESSIONS_PATH)}>View all sessions ›</Button>
          </>}
      </section>
    </>}
  </AthletePage>
}
