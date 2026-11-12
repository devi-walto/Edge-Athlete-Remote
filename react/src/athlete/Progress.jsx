// Progress.jsx — /athlete/progress: My Recent Progress, the athlete's own trends.
//
// Why this file exists: an athlete wants to know if they're getting faster or stronger
// (spec 10, Phase 4; boards F_Ath_P1, P2, P2b–P2d). For a range they choose (the same
// range control as the coach's History), it shows sessions and sets done against the
// plan, then one row per movement: its top load, a small teal trend line and how much the
// speed changed (amber when it went down).
//
// Tapping a movement opens it in place (one at a time): a legend saying what one bar is,
// the LB | KG choice (remembered on this phone, every load on every page follows it), one
// bar per point (speed above, load inside, when below; lighter for a period the range only
// partly covers), then Best rep, Top load and the max their weights come from, with an ⓘ
// that explains it in place. At the bottom, their own sets in the range as a PDF.
// Built only from shared pieces (spec 06 rule 13).
import { useEffect, useState } from 'react'
import { presetRange } from '../coach/historyRange.js'
import BarChart from '../ui/BarChart.jsx'
import Button from '../ui/Button.jsx'
import RangePicker from '../ui/RangePicker.jsx'
import SectionLabel from '../ui/SectionLabel.jsx'
import Tiles from '../ui/Tiles.jsx'
import TrendLine from '../ui/TrendLine.jsx'
import UnitToggle from '../ui/UnitToggle.jsx'
import { formatLoad, useUnit } from '../units.js'
import AthletePage, { HOME_PATH, toSignIn } from './AthletePage.jsx'
import { PROGRESS, downloadFile, getJson } from './athleteApi.js'

export const PROGRESS_PATH = '/athlete/progress'
export const DEFAULT_DAYS = 30

const STEP_WORDS = { session: '1 session · its top set', week: '1 week · its best top set',
  month: '1 month · its best top set', quarter: '1 quarter · its best top set', year: '1 year · its best top set' }

/** "Each bar = 1 week · its best top set (m/s)" */
export function legendFor(step) {
  return `Each bar = ${STEP_WORDS[step] || STEP_WORDS.session} (m/s)`
}

/** "+0.03 m/s" or "−0.02 m/s"; null with nothing to compare. */
export function changeLabel(change) {
  if (change == null) return null
  const shown = Math.round(change * 100) / 100           // a change too small to show is no change
  const sign = shown > 0 ? '+' : shown < 0 ? '−' : '±'
  return `${sign}${Math.abs(shown).toFixed(2)} m/s`
}

/** Down by at least the 0.01 that shows: the change turns amber. */
export const wentDown = (change) => change != null && Math.round(change * 100) < 0

/** The max tile: EST. MAX (the app worked it out), MAX (the coach entered it), or --. */
export function maxTile(max, unit) {
  if (!max) return { label: 'Est. max', value: '--', quiet: true }
  return { label: max.source === 'manual' ? 'Max' : 'Est. max', value: formatLoad(max.weight_lbs, unit) }
}

function MovementPanel({ movement, unit }) {
  const [explaining, setExplaining] = useState(false)
  const step = movement.trend[0]?.bucket || 'session'
  const partial = movement.trend.some((p) => p.partial)
  const max = maxTile(movement.max, unit)
  return <div className="athlete-progress-panel">
    <div className="athlete-progress-legend">
      <div className="athlete-progress-legend-text">
        <span>{legendFor(step)}</span>
        <span>Speed above · load inside · when, below</span>
      </div>
      <UnitToggle />
    </div>
    <BarChart label={`${movement.name}: top set speed`} minPct={45} height={190}
      bars={movement.trend.map((p) => ({
        value: p.top_set_avg_velocity ?? 0,
        above: <>{p.top_set_avg_velocity == null ? '—' : p.top_set_avg_velocity.toFixed(2)}<br />m/s</>,
        inside: formatLoad(p.load_lbs, unit), below: p.label, faded: p.partial,
        label: `${p.label}: ${p.top_set_avg_velocity == null ? 'not measured' : `${p.top_set_avg_velocity.toFixed(2)} m/s`}`
          + (p.load_lbs ? ` at ${formatLoad(p.load_lbs, unit)}` : ''),
      }))} />
    {partial && <span className="athlete-progress-note">Lighter bars: periods the range only partly covers</span>}
    <Tiles size="small" items={[
      { label: 'Best rep', value: movement.best_rep_velocity == null ? 'not measured' : `${movement.best_rep_velocity.toFixed(2)}`,
        quiet: movement.best_rep_velocity == null },
      { label: 'Top load', value: formatLoad(movement.top_load_lbs, unit) ?? '--', quiet: movement.top_load_lbs == null },
      { ...max, info: <button type="button" className="athlete-info" aria-expanded={explaining}
        aria-label="What is this number?" onClick={() => setExplaining(!explaining)}>ⓘ</button> },
    ]} />
    {explaining && <p className="athlete-progress-explain" role="note">
      <span>This is the max your weights are worked out from.</span>
      <span>Est. max: the app worked it out from your best set when a session ended. Max: your coach entered it.</span>
    </p>}
  </div>
}

export default function Progress() {
  const unit = useUnit()
  const [range, setRange] = useState(() => presetRange(DEFAULT_DAYS))
  const [data, setData] = useState(null)
  const [failed, setFailed] = useState(false)
  const [open, setOpen] = useState(null)               // the movement showing its bars
  const [pdf, setPdf] = useState(null)                 // null | 'working' | 'failed'

  useEffect(() => {
    let cancelled = false
    getJson(`${PROGRESS}?from=${range.from}&to=${range.to}`).then(({ status, body }) => {
      if (cancelled) return
      if (status === 401 || status === 403) { toSignIn(PROGRESS_PATH); return }
      if (status !== 200) { setFailed(true); return }
      setFailed(false)
      setData(body)
    })
    return () => { cancelled = true }
  }, [range])

  const download = async () => {
    setPdf('working')
    const status = await downloadFile(`${PROGRESS}report/?from=${range.from}&to=${range.to}&unit=${unit}`,
      `my-report-${range.from}-to-${range.to}.pdf`)
    setPdf(status === 200 ? null : 'failed')
  }

  return <AthletePage here={PROGRESS_PATH} back={{ label: 'Home', to: HOME_PATH }}>
    <h1 className="athlete-page-title">My Recent Progress</h1>
    <section className="athlete-progress-range" aria-label="Date range">
      <RangePicker value={range} onChange={setRange} />
    </section>
    {failed && <p className="acct-error" role="alert">The school's server didn't answer.</p>}
    {data && <>
      <Tiles items={[
        { label: 'Sessions', value: data.sessions.done, of: data.sessions.planned || null,
          short: data.sessions.planned > 0 && data.sessions.done < data.sessions.planned },
        { label: 'Sets done', value: data.sets.done, of: data.sets.planned || null,
          short: data.sets.planned > 0 && data.sets.done < data.sets.planned },
      ]} />
      <section aria-labelledby="movements-label">
        <SectionLabel as="h2"><span id="movements-label">Movements</span></SectionLabel>
        {data.movements.length === 0 && <p className="athlete-empty">Nothing lifted in this range.</p>}
        {data.movements.map((m) => {
          const isOpen = open === m.name
          const change = changeLabel(m.change)
          return <div key={m.name} className={`athlete-progress-item${isOpen ? ' is-open' : ''}`}>
            <button type="button" className="ui-row athlete-progress-row" aria-expanded={isOpen}
              onClick={() => setOpen(isOpen ? null : m.name)}>
              <span className="ui-row-text">
                <b className="ui-row-name">{m.name}</b>
                <span className="ui-row-meta">Top set {formatLoad(m.top_load_lbs, unit) ?? '--'}</span>
              </span>
              <TrendLine values={m.trend.map((p) => p.top_set_avg_velocity)} label={`${m.name} speed trend`} />
              {change && <span className={`athlete-progress-change${wentDown(m.change) ? ' is-down' : ''}`}>{change}</span>}
              <span className="athlete-chevron" aria-hidden="true">{isOpen ? '⌃' : '⌄'}</span>
            </button>
            {isOpen && <MovementPanel movement={m} unit={unit} />}
          </div>
        })}
      </section>
      <Button kind="solid" onClick={download} disabled={pdf === 'working'}>
        {pdf === 'working' ? 'Making your report…' : 'Download my report (PDF)'}
      </Button>
      {pdf === 'failed' && <p className="acct-error" role="alert">The report couldn't be made. Try a shorter range.</p>}
    </>}
  </AthletePage>
}
