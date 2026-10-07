// Why this file exists: the top-left corner of every coach screen is the coach's own
// account. Pressing it opens a small menu: who is signed in, whether they are an
// administrator, and the three things a coach does to their own login. It was a bare
// "Log out" before coach accounts existed; now there is more than one coach, so the menu
// has to say which one is signed in.
//
// "Coaches" is shown to administrators only. That is a courtesy, not the lock: the
// server refuses a regular coach on those routes whether or not they can see the button.
import { useEffect, useRef, useState } from 'react'
import { navigate } from '../router.js'
import './account.css'

export const COACHES_PATH = '/coach/account/coaches'
export const PASSWORD_PATH = '/coach/account/password'

export function ProfileImage() {
  return <span className="acct-avatar" aria-hidden="true">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="#071006"><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7z" /></svg>
  </span>
}

export default function AccountMenu({ me, onLogout }) {
  const [open, setOpen] = useState(false)
  const box = useRef(null)
  // Close on a press anywhere else, and on Escape, like any other menu.
  useEffect(() => {
    if (!open) return undefined
    const away = (event) => { if (box.current && !box.current.contains(event.target)) setOpen(false) }
    const escape = (event) => { if (event.key === 'Escape') setOpen(false) }
    document.addEventListener('pointerdown', away)
    document.addEventListener('keydown', escape)
    return () => { document.removeEventListener('pointerdown', away); document.removeEventListener('keydown', escape) }
  }, [open])
  const go = (path) => { setOpen(false); navigate(path) }

  return <div className="acct-menu" ref={box}>
    <button type="button" className="acct-menu-button" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)}>
      <ProfileImage /><span>Edge Athlete</span>
    </button>
    {open && <div className="acct-menu-panel" role="menu">
      <div className="acct-menu-who">
        <span className="acct-label">Signed in as</span>
        <span><b>{me?.username || '…'}</b>{me?.role === 'administrator' && <em className="acct-badge" style={{ fontStyle: 'normal' }}>Administrator</em>}</span>
      </div>
      {me?.role === 'administrator' && <button type="button" role="menuitem" onClick={() => go(COACHES_PATH)}>Coaches<small>administrators only</small></button>}
      <button type="button" role="menuitem" onClick={() => go(PASSWORD_PATH)}>Change password</button>
      <button type="button" role="menuitem" onClick={() => { setOpen(false); onLogout() }}>Log out</button>
    </div>}
  </div>
}
