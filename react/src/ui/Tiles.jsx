// Tiles.jsx — a row of big-number tiles: a small label over a number ("SETS / 7 / 9").
//
// Why this file exists: the athlete's pages show a day or a range as two or three tiles
// (Sets, Reps, Avg m/s; Best rep, Top load, Est. max). One piece (spec 06 rule 13).
import './ui.css'

/** size: 'normal', or 'small' for three tiles inside a narrow panel (numbers with a unit,
 *  "185 lb", stay on one line). items [{ label, value, of (a quieter "/ 9" after it), quiet (a word, not a number, e.g.
 *  "not measured"), short (amber: under plan), info (an element after the label) }] */
export default function Tiles({ items, size = 'normal', className = '' }) {
  return <div className={`ui-tiles${size === 'small' ? ' ui-tiles--small' : ''}${className ? ` ${className}` : ''}`} style={{ '--tiles': items.length }}>
    {items.map((t) => <div key={t.label}>
      <span className="ui-tile-label">{t.label}{t.info}</span>
      <b className={[t.quiet && 'is-quiet', t.short && 'is-short'].filter(Boolean).join(' ') || undefined}>
        {t.value}{t.of != null && <small> / {t.of}</small>}
      </b>
    </div>)}
  </div>
}
