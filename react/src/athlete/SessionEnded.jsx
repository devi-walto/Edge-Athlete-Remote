// SessionEnded.jsx — what an athlete sees when their coach ends the session (spec 10, Phase 2).
//
// Why this file exists: ending the session releases the athlete's rack, and before this the
// phone just said the session had ended. Now it shows what they did (board F_Ath_R10): sets,
// reps and average speed for the day, then each movement with how many of its sets were done,
// and Back to home. A set still open when the coach ended the day was closed and kept by the
// server, so it's counted. The numbers are the athlete's own sets from
// GET /api/athlete/sessions/<id>/, the same count the daily report keeps.
import { useEffect, useState } from 'react'
import { navigate } from '../router.js'
import Button from '../ui/Button.jsx'
import QuietRow from '../ui/QuietRow.jsx'
import SectionLabel from '../ui/SectionLabel.jsx'
import { HOME_PATH } from './AthletePage.jsx'
import { getJson } from './athleteApi.js'

/** "0.61", or "not measured" when no set had a speed (every set typed in). */
export function speedLabel(v) {
  return v == null ? 'not measured' : v.toFixed(2)
}

/** Sets, reps, average speed: three tiles (also used by the past session page). */
export function DayTiles({ totals }) {
  return <div className="athlete-tiles">
    <div><span>Sets</span><b>{totals.sets_done}</b></div>
    <div><span>Reps</span><b>{totals.reps}</b></div>
    <div><span>Avg m/s</span><b className={totals.avg_velocity == null ? 'is-quiet' : ''}>{speedLabel(totals.avg_velocity)}</b></div>
  </div>
}

/** One movement: "3 sets · 225 lb" with Done, or "3 of 4 sets · 140 lb" with "3 of 4" in amber. */
export function MovementDone({ movement }) {
  const done = movement.sets.length
  const planned = movement.sets_planned
  const top = Math.max(0, ...movement.sets.map((s) => s.weight_lbs || 0))
  const full = !planned || done >= planned
  const count = full ? `${done} sets` : `${done} of ${planned} sets`
  return <QuietRow name={movement.name} meta={top ? `${count} · ${top} lb` : count}
    badge={<span className={`athlete-sets${full ? '' : ' is-short'}`}>{full ? 'Done' : `${done} of ${planned}`}</span>} />
}

export default function SessionEnded({ sessionId, label }) {
  const [day, setDay] = useState(null)
  useEffect(() => {
    let cancelled = false
    getJson(`/api/athlete/sessions/${sessionId}/`).then(({ status, body }) => {
      if (!cancelled && status === 200) setDay(body)
    })
    return () => { cancelled = true }
  }, [sessionId])

  return <>
    <section className="athlete-card athlete-ended">
      <span>Session ended</span>
      {(day?.title || label) && <h2>{day?.title || label}</h2>}
      <p>Your coach ended the session. Everything is saved.</p>
    </section>
    {day && <>
      <DayTiles totals={day.totals} />
      <section aria-labelledby="did-label">
        <SectionLabel as="h2"><span id="did-label">What you did</span></SectionLabel>
        {day.movements.map((m) => <MovementDone key={m.name} movement={m} />)}
      </section>
    </>}
    <Button kind="solid" onClick={() => navigate(HOME_PATH)}>Back to home</Button>
  </>
}
