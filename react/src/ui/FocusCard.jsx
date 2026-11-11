// FocusCard.jsx — the one thing on a screen the person is working on.
//
// Why this file exists: spec 06 rule 1. Before the redesign every screen looked equally
// loud, so nothing said "this is what you're doing". Each screen now has exactly one
// focus card: a lime edge, a tinted background and a big title, with everything else
// around it kept quiet.
import './ui.css'

/** label: the small line above the title; title: the big line; children: its actions. */
export default function FocusCard({ label, title, children, as: Tag = 'section', className = '', ...rest }) {
  return <Tag className={`ui-focus${className ? ` ${className}` : ''}`} {...rest}>
    {label && <span className="ui-focus-label">{label}</span>}
    <h2 className="ui-focus-title">{title}</h2>
    {children && <div className="ui-focus-actions">{children}</div>}
  </Tag>
}
