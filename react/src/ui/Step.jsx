// Step.jsx — a numbered step in a sequence (Build a block → Create a program → Schedule).
//
// Why this file exists: spec 06 rule 1. The step the coach is in is loud (a filled lime
// number, a big title, a lime rail down its contents); every other step shrinks to one
// thin row, so the screen shows one thing at a time without hiding where you are in the
// sequence. StepLink is a step that takes you to another page instead of opening here.
import './ui.css'

/**
 * number, title; active: whether this is the open step; summary: what's inside, shown on
 * the thin row; onOpen: makes the thin row a button that opens it; children: the open
 * step's contents.
 */
export default function Step({ number, title, active = false, summary, onOpen, children }) {
  const row = <>
    <span className="ui-step-number" aria-hidden="true">{number}</span>
    <span className="ui-step-title">{title}</span>
    {!active && summary && <span className="ui-step-summary">{summary}</span>}
  </>
  return <section className={`ui-step${active ? ' is-active' : ''}`} aria-label={`Step ${number}: ${title}`}>
    {!active && onOpen
      ? <button type="button" className="ui-step-row" onClick={onOpen} aria-expanded="false">{row}</button>
      : <div className="ui-step-row" aria-current={active ? 'step' : undefined}>{row}</div>}
    {active && children && <div className="ui-step-body">{children}</div>}
  </section>
}

/** A step that goes to another page: the thin row, with an arrow, as a button. */
export function StepLink({ number, title, onClick }) {
  return <section className="ui-step" aria-label={`Step ${number}: ${title}`}>
    <button type="button" className="ui-step-row" onClick={onClick}>
      <span className="ui-step-number" aria-hidden="true">{number}</span>
      <span className="ui-step-title">{title}</span>
      <span className="ui-step-arrow" aria-hidden="true">→</span>
    </button>
  </section>
}
