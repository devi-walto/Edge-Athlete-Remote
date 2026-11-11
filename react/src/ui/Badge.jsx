// Badge.jsx — a small status label: is a program scheduled, what is a rack doing, is
// its sensor answering.
//
// Why this file exists: spec 06 rule 3 says these states must be visible without
// drilling, and the Final designs draw each one a fixed way (a mint pill for Scheduled,
// an amber chip for a sensor that stopped answering). One piece, so the same state looks
// the same on every screen.
import './ui.css'

const LABELS = {
  scheduled: 'Scheduled',
  'not-scheduled': 'Not scheduled',
  lifting: 'Lifting',
  idle: 'Idle',
  'sensor-on': 'Sensor',
  'sensor-off': 'Sensor not responding',
}
export const BADGE_KINDS = Object.keys(LABELS)

function WarningMark() {
  return <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6"
    strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 3 2 20h20L12 3z" /><path d="M12 10v5" /><path d="M12 18h.01" /></svg>
}

/** kind: one of BADGE_KINDS; children: different words, when the default doesn't fit. */
export default function Badge({ kind, children }) {
  if (!LABELS[kind]) {
    if (import.meta.env.DEV) throw new Error(`Badge: unknown kind "${kind}". Use one of: ${BADGE_KINDS.join(', ')}.`)
    return null
  }
  return <span className={`ui-badge ui-badge--${kind}`}>
    {kind === 'sensor-off' ? <WarningMark /> : <span className="ui-badge-dot" aria-hidden="true" />}
    {children ?? LABELS[kind]}
  </span>
}
