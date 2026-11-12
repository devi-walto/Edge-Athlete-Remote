// BarChart.jsx — the one bar chart in Edge Athlete: a row of bars, each with an optional
// number above, text inside and label below.
//
// Why this file exists: the same chart was drawn by hand in three places (the coach's live
// rep chart, the coach's history sparkline, the athlete's past session), with more on the
// way (My Recent Progress, the rack screen's set summary). Copies drift, the way the
// colours did before tokens.css. So every bar chart is this one piece, set up with options
// (spec 06 rule 13). The screen using it decides what the bars mean and their colours; the
// chart only draws them.
//
// Three sizes, same code:
//   spark    tiny, no words: a glance beside a row (the coach's history list).
//   normal   the athlete's pages and the rack screen: fits the width, never scrolls.
//   large    the coach's live view: taller, wider bars on a dark track, scrolls sideways
//            when a long set doesn't fit.
import './ui.css'

// What a bar's colour means. The rep colours are the rack screen's rule (rack/velocity.js:
// green on target, yellow fading, red well under); grey is a rep with no rule to judge it.
export const TONES = ['green', 'yellow', 'red', 'grey']

const SIZES = {
  spark: { minPct: 10, scroll: false },
  normal: { minPct: 12, scroll: false },
  large: { minPct: 8, scroll: true },
}

/**
 * bars     [{ value, above, inside, below, tone, faded, label }]
 *            value   how tall (any unit; the tallest is the top unless `max` is given)
 *            above   the number over the bar ("0.66", or two lines as an element)
 *            inside  text written upward inside the bar ("225 lb")
 *            below   the label under it ("R1", "Nov 4")
 *            tone    one of TONES (default green, the teal)
 *            faded   drawn lighter (a period the range only partly covers)
 *            label   what a screen reader says for the bar
 * size     'spark' | 'normal' | 'large'
 * max      the value at full height (default: the tallest bar)
 * minPct   the shortest a bar is drawn, in % (so a slow rep stays visible)
 * legend   lines over the chart saying what a bar is ("Each bar = 1 week · …")
 * height   the chart's height in px, when the size's own isn't right (tall bars to hold
 *          text inside)
 * scroll   scroll sideways instead of shrinking bars (default: only large)
 * label    what the whole chart is, for a screen reader
 */
export default function BarChart({ bars, size = 'normal', max, minPct, legend, scroll, height: rowHeight, label, className = '' }) {
  const look = SIZES[size]
  if (!look && import.meta.env?.DEV) throw new Error(`BarChart: unknown size "${size}"`)
  const top = max ?? Math.max(0, ...bars.map((b) => b.value || 0))
  const floor = minPct ?? look.minPct
  const words = size !== 'spark'
  const height = (v) => `${top > 0 ? Math.min(100, Math.max(floor, ((v || 0) / top) * 100)) : floor}%`
  const scrolls = scroll ?? look.scroll

  return <figure className={`ui-bars ui-bars--${size}${className ? ` ${className}` : ''}`}>
    {words && legend?.length > 0 && <figcaption className="ui-bars-legend">
      {legend.map((line) => <span key={line}>{line}</span>)}
    </figcaption>}
    <div className={`ui-bars-row${scrolls ? ' is-scroll' : ''}`} role="list" aria-label={label}
      style={rowHeight ? { height: rowHeight } : undefined}>
      {bars.map((bar, i) => <div key={i} className="ui-bar" role="listitem" aria-label={bar.label}>
        {words && bar.above != null && <span className="ui-bar-above">{bar.above}</span>}
        <span className="ui-bar-track">
          <span className={`ui-bar-fill is-${bar.tone || 'green'}${bar.faded ? ' is-faded' : ''}`}
            data-tone={bar.tone || 'green'} style={{ height: height(bar.value) }}>
            {words && bar.inside != null && <span className="ui-bar-inside">{bar.inside}</span>}
          </span>
        </span>
        {words && bar.below != null && <span className="ui-bar-below">{bar.below}</span>}
      </div>)}
    </div>
  </figure>
}
