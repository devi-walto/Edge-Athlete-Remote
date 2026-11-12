// PastSession.jsx — /athlete/sessions/<id>: one past session, set by set, rep by rep.
//
// Why this file exists: an athlete wants to look back at a day and see what they lifted and
// how fast (spec 10, Phase 3; board F_Ath_L2). The page shows the day's banner (date,
// group, title), three tiles (sets done of planned, reps, average speed), and a card per
// movement with a row per set: "Set 2 · 225 lb × 5 · 0.66 m/s".
//
// Pressing a measured set opens its reps right there: one bar per rep with its speed,
// drawn by the shared ui/BarChart, coloured by the same rule as the rack screen (rack/velocity.js: on target, fading in
// amber, well under in red), and how much the speed dropped from first rep to last. A set
// typed in by hand has no speeds: it reads "not measured" and has nothing to open.
//
// Its back link leads to wherever it was opened from: All sessions, or Home.
import { useEffect, useState } from 'react'
import { velocityColor } from '../rack/velocity.js'
import BarChart from '../ui/BarChart.jsx'
import { formatLoad, useUnit } from '../units.js'
import SectionLabel from '../ui/SectionLabel.jsx'
import AthletePage, { SESSIONS_PATH, backFor, toSignIn } from './AthletePage.jsx'
import { SESSIONS, dayLabel, getJson } from './athleteApi.js'
import { DayTiles, speedLabel } from './SessionEnded.jsx'

/** "Set 2 · 225 lb × 5 · 0.66 m/s", or "… · not measured" for a typed-in set. The load is in
 *  the phone's chosen unit ("102 kg × 5"); the speed is always m/s. */
export function setLine(s, unit) {
  const load = s.weight_lbs ? `${formatLoad(s.weight_lbs, unit)} × ${s.reps}` : `${s.reps} reps`
  const speed = s.avg_velocity == null ? 'not measured' : `${s.avg_velocity.toFixed(2)} m/s`
  return `Set ${s.set_number} · ${load} · ${speed}`
}

/** One bar per rep, tallest = fastest, coloured by the rack screen's rule, and the drop. */
export function RepBars({ speeds, zoneMin }) {
  const drop = speeds.length > 1 && speeds[0] > 0 ? Math.round((1 - speeds.at(-1) / speeds[0]) * 100) : null
  return <div className="athlete-reps">
    <BarChart label="Speed of each rep" bars={speeds.map((v, i) => ({
      value: v, above: v.toFixed(2), tone: velocityColor(v, zoneMin), label: `Rep ${i + 1}: ${v.toFixed(2)} m/s`,
    }))} />
    {drop !== null && <span className="athlete-rep-drop">
      {drop > 0 ? `Speed dropped ${drop}% from first rep to last` : 'No drop from first rep to last'}
    </span>}
  </div>
}

function SetRow({ set, zoneMin, open, onToggle }) {
  const unit = useUnit()
  const measured = set.reps_detail.length > 0
  if (!measured) {
    return <div className="ui-row athlete-set"><span className="ui-row-name">{setLine(set, unit)}</span></div>
  }
  return <div className={`athlete-set-wrap${open ? ' is-open' : ''}`}>
    <button type="button" className="ui-row athlete-set is-pressable" aria-expanded={open} onClick={onToggle}>
      <span className="ui-row-name">{setLine(set, unit)}</span>
      <span className="athlete-chevron" aria-hidden="true">{open ? '⌃' : '⌄'}</span>
    </button>
    {open && <RepBars speeds={set.reps_detail} zoneMin={zoneMin} />}
  </div>
}

export default function PastSession({ sessionId }) {
  const [day, setDay] = useState(null)
  const [missing, setMissing] = useState(false)
  const [open, setOpen] = useState(null)            // "movement:set" of the set showing its reps
  const here = `${SESSIONS_PATH}/${sessionId}`

  useEffect(() => {
    let cancelled = false
    setDay(null); setMissing(false); setOpen(null)
    getJson(`${SESSIONS}${sessionId}/`).then(({ status, body }) => {
      if (cancelled) return
      if (status === 401 || status === 403) toSignIn(here + window.location.search)
      else if (status === 200) setDay(body)
      else setMissing(true)
    })
    return () => { cancelled = true }
  }, [sessionId, here])

  return <AthletePage here={here} back={backFor(window.location.search)}>
    {missing && <p className="athlete-empty" role="alert">This session isn't one of yours, or it couldn't be loaded.</p>}
    {day && <>
      <section className="athlete-greeting">
        <span className="athlete-greeting-label">{[day.date && dayLabel(day.date), ...day.groups].filter(Boolean).join(' · ')}</span>
        <h1>{day.title}</h1>
      </section>
      <DayTiles totals={day.totals} withPlanned />
      {day.movements.map((m) => <section key={m.name} className="athlete-movement" aria-label={m.name}>
        <SectionLabel as="h2">{m.name}{m.sets_planned ? ` · ${m.sets.length} of ${m.sets_planned} sets` : ''}</SectionLabel>
        {m.sets.length === 0
          ? <p className="athlete-empty">Not lifted this day.</p>
          : m.sets.map((s) => {
            const key = `${m.name}:${s.set_number}`
            return <SetRow key={key} set={s} zoneMin={m.zone_min} open={open === key}
              onToggle={() => setOpen(open === key ? null : key)} />
          })}
      </section>)}
      {day.totals.avg_velocity == null && <p className="athlete-empty">Speeds show for sets lifted with your sensor; sets typed in by hand read {speedLabel(null)}.</p>}
    </>}
  </AthletePage>
}
