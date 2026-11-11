// Button.jsx — the only way to make a button on the coach and athlete screens.
//
// Why this file exists: spec 06 rule 2 gives every button one of eight jobs, and each
// job always looks the same (one lime button per screen, every End button a red outline,
// and so on). Building every button from this one piece keeps that true everywhere,
// instead of each screen styling its own. The kind must be one of the eight; a typo
// stops the app while it's being built, so a wrong-looking button never ships.
import './ui.css'

export const BUTTON_KINDS = ['primary', 'next', 'solid', 'key', 'end', 'danger', 'quiet', 'quiet-lime']

/**
 * kind:  primary     the one next step on a screen (filled lime)
 *        next        the same, ending in an arrow: moves to the next stage
 *        solid       a real but secondary action
 *        key         the main secondary action of a screen (lime edge), e.g. Copy session link
 *        end         ends something (red outline), e.g. End training day
 *        danger      inside a confirm dialog, removes something for good (filled red)
 *        quiet       row actions, Close, Cancel (text only)
 *        quiet-lime  the action inside a dashed "waiting" row, e.g. Send login link
 * icon:  optional, shown before the words
 */
export default function Button({ kind, icon, children, className = '', type = 'button', ...rest }) {
  let look = kind
  if (!BUTTON_KINDS.includes(kind)) {
    if (import.meta.env.DEV) throw new Error(`Button: unknown kind "${kind}". Use one of: ${BUTTON_KINDS.join(', ')}.`)
    look = 'solid'
  }
  return <button type={type} className={`ui-button ui-button--${look}${className ? ` ${className}` : ''}`} {...rest}>
    {icon && <span className="ui-button-icon" aria-hidden="true">{icon}</span>}
    <span>{children}</span>
    {look === 'next' && <span aria-hidden="true">→</span>}
  </button>
}
