// TrendLine.jsx — a small line through a few numbers, for a glance at which way they go.
//
// Why this file exists: a collapsed row on My Recent Progress shows its trend as a little
// teal line (board F_Ath_P1); the bars are the detail when it opens. One piece for every
// such line (spec 06 rule 13). Missing numbers are skipped; one number is a dot.
import './ui.css'

/** values: numbers (null skipped), label: what it shows, for a screen reader. */
export default function TrendLine({ values, label, width = 72, height = 24 }) {
  const points = values.map((v, i) => [i, v]).filter(([, v]) => v != null)
  if (points.length === 0) return null
  const ys = points.map(([, v]) => v)
  const low = Math.min(...ys)
  const span = Math.max(...ys) - low || 1
  const last = values.length - 1 || 1
  const xy = points.map(([i, v]) => [2 + (i / last) * (width - 4), height - 2 - ((v - low) / span) * (height - 4)])
  return <svg className="ui-trend" width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={label}>
    {xy.length > 1
      ? <polyline points={xy.map((p) => p.join(',')).join(' ')} fill="none" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
      : <circle cx={xy[0][0]} cy={xy[0][1]} r="2.5" />}
  </svg>
}
