// Hero.jsx — the header card at the top of a tab: a small lime line, a big title and a
// sentence under it.
//
// Why this file exists: spec 06 rule 6 keeps this card on every tab, exactly as it is.
// It was written out by hand on each tab (Design, Calendar, Groups); this is the same
// markup in one place, using the same styles (`.workout-catalog-heading` in
// styles/planning.css), so it looks identical wherever it's used.

/** eyebrow: the small lime line; title; children: the sentence; aside: optional note on the right. */
export default function Hero({ eyebrow, title, children, aside }) {
  return <header className="workout-catalog-heading">
    <div>
      {eyebrow && <span>{eyebrow}</span>}
      <h2>{title}</h2>
      {children && <p>{children}</p>}
    </div>
    {aside && <b>{aside}</b>}
  </header>
}
