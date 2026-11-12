// RangePicker.jsx — a stretch of whole days: presets (14d · 30d · 90d), From and To, and a
// label saying what's chosen ("Last 30 days", or the two dates).
//
// Why this file exists: the coach's History and the athlete's My Recent Progress ask the
// same question the same way (spec 10 Phase 4: "works exactly as the coach's Analytics
// range does"). The rules live in coach/historyRange.js; this is the one way to draw them
// (spec 06 rule 13). Choosing a preset fills both dates; editing a date clears the preset
// (no pill stays lit); dates the wrong way round are swapped, never refused.
import { matchesPreset, normaliseRange, presetRange, RANGE_PRESETS, rangeLabel } from '../coach/historyRange.js'
import PillGroup from './PillGroup.jsx'
import './ui.css'

/** value { from, to } (YYYY-MM-DD), onChange(range). */
export default function RangePicker({ value, onChange, className = '' }) {
  const lit = RANGE_PRESETS.find((p) => matchesPreset(value, p.days))?.days ?? null
  return <div className={`ui-range${className ? ` ${className}` : ''}`}>
    <PillGroup label="Date range presets" value={lit}
      choices={RANGE_PRESETS.map((p) => ({ value: p.days, label: `${p.days}d` }))}
      onChange={(days) => onChange(presetRange(days))} />
    <label>From<input type="date" value={value.from} max={value.to}
      onChange={(e) => onChange(normaliseRange(e.target.value, value.to) || value)} /></label>
    <label>To<input type="date" value={value.to} min={value.from}
      onChange={(e) => onChange(normaliseRange(value.from, e.target.value) || value)} /></label>
    <span className="ui-range-label">{rangeLabel(value)}</span>
  </div>
}
