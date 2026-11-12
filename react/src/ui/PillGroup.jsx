// PillGroup.jsx — a small row of pills where one is chosen: 14d · 30d · 90d, LB | KG,
// Athlete | Group.
//
// Why this file exists: spec 06 rule 13. The coach's History had two of these drawn by
// hand (the range presets and the Athlete / Group switch), and the athlete's pages need
// more; one piece keeps them alike. The chosen pill is lime, or soft grey with
// tone="quiet" for a setting beside a screen's lime (LB | KG: rule 2, one lime per screen).
import './ui.css'

/** choices [{ value, label }], value (the chosen one, or null for none), onChange(value),
 *  label (what the group is, for a screen reader). */
export default function PillGroup({ choices, value, onChange, label, tone, className = '' }) {
  return <div className={`ui-pills${tone === 'quiet' ? ' ui-pills--quiet' : ''}${className ? ` ${className}` : ''}`} role="group" aria-label={label}>
    {choices.map((c) => <button key={c.value} type="button" className={c.value === value ? 'is-on' : ''}
      aria-pressed={c.value === value} onClick={() => onChange(c.value)}>{c.label}</button>)}
  </div>
}
