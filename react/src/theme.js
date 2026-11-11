// theme.js — the rack screen's colours and type, for inline styles.
//
// Why this file exists: the rack screen and a few other screens set their styles in
// JavaScript (style={{ ... }}) instead of in a stylesheet, so they need the colours as
// values they can drop in. Every value here only POINTS at a colour in
// styles/tokens.css (the one place colours are defined), so changing a colour there
// changes these screens too. Never put a colour code in this file.
export const T = {
  bg: 'var(--bg)',      // the page background
  panel: 'var(--panel)',   // cards, rows, buttons
  panel2: 'var(--panel2)',  // a surface one step lighter
  line: 'var(--line)',    // borders and dividers
  ink: 'var(--ink)',     // main text
  muted: 'var(--muted)',   // secondary text, labels
  lime: 'var(--lime)',    // the brand accent: press this next
  mint: 'var(--mint)',    // status: on target  (green)
  amber: 'var(--amber)',   // status: dropping   (yellow)
  coral: 'var(--coral)',   // status: fatigued   (red)

  // Inter, bundled with the app (see main.jsx); defined in styles/tokens.css.
  sans: 'var(--font-sans)',
  mono: 'var(--font-mono)',
}

/** A see-through version of a colour, for inline styles: seeThrough(T.coral, 40) is
 *  coral at 40% over whatever is behind it. Colours here are names, not codes, so the
 *  old trick of gluing "66" onto a colour code no longer works; this does the same. */
export function seeThrough(color, percent) {
  return `color-mix(in srgb, ${color} ${percent}%, transparent)`
}
