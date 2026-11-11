// RiskTag.jsx — marks an athlete who is Behind (trending down).
//
// Why this file exists: spec 06 rules 3 and 5. Who is at risk must be visible without
// drilling, and red means only Behind (or ending something). The full tag ("Behind 4/5")
// sits on a row; the compact form is just the small red triangle beside a name, where
// there's no room for words. Both say "Behind" to a screen reader.
import './ui.css'

function Triangle() {
  return <svg width="9" height="9" viewBox="0 0 10 10" aria-hidden="true"><path d="M1 2h8L5 9z" /></svg>
}

/** detail: e.g. "4/5" (sets below target); compact: only the triangle. */
export default function RiskTag({ detail, compact = false }) {
  if (compact) {
    return <svg className="ui-risk-mark" width="10" height="10" viewBox="0 0 10 10" role="img"
      aria-label={detail ? `Behind ${detail}` : 'Behind'}><path d="M1 2h8L5 9z" /></svg>
  }
  return <span className="ui-risk"><Triangle />Behind{detail ? ` ${detail}` : ''}</span>
}
