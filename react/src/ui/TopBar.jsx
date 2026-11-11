// TopBar.jsx — the top-left corner of every coach and athlete page.
//
// Why this file exists: spec 06 rule 12 (Devin, 2026-11-11). The picture always takes
// you Home, from anywhere: a coach's Home is Planning, an athlete's is their home page.
// The signed-in person's name, beside it, opens their account menu. Two separate
// targets, the same on every page, so nobody has to learn where Home is twice. When
// nobody is signed in (sign-in, first-run), the square says "EA" and nothing is pressable.
//
// The menu closes on Escape or a press anywhere else, like any other menu. What's in it
// is up to the page: the coach's has Coaches (administrators only), Change password and
// Log out; the athlete's has Account and Sign out.
import { useEffect, useRef, useState } from 'react'
import './ui.css'

function Person() {
  return <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7z" /></svg>
}

/**
 * name: who is signed in (leave out when nobody is); onHome: where the picture goes;
 * menuHeader: shown at the top of the open menu; menuItems: [{ label, hint, onSelect }].
 */
export default function TopBar({ name, onHome, menuHeader, menuItems = [] }) {
  const [open, setOpen] = useState(false)
  const box = useRef(null)
  useEffect(() => {
    if (!open) return undefined
    const away = (event) => { if (box.current && !box.current.contains(event.target)) setOpen(false) }
    const escape = (event) => { if (event.key === 'Escape') setOpen(false) }
    document.addEventListener('pointerdown', away)
    document.addEventListener('keydown', escape)
    return () => { document.removeEventListener('pointerdown', away); document.removeEventListener('keydown', escape) }
  }, [open])

  if (!name) {
    return <div className="ui-topbar">
      <span className="ui-topbar-square" aria-hidden="true">EA</span>
      <span className="ui-topbar-brand">Edge Athlete</span>
    </div>
  }
  return <div className="ui-topbar" ref={box}>
    <button type="button" className="ui-topbar-home" aria-label="Home" onClick={() => { setOpen(false); onHome?.() }}>
      <span className="ui-topbar-square"><Person /></span>
    </button>
    <button type="button" className="ui-topbar-name" aria-label={`Account menu: ${name}`} aria-haspopup="menu"
      aria-expanded={open} onClick={() => setOpen(!open)}>
      {name}<span className="ui-topbar-caret" aria-hidden="true">▾</span>
    </button>
    {open && <div className="ui-topbar-menu" role="menu">
      {menuHeader && <div className="ui-topbar-menu-header">{menuHeader}</div>}
      {menuItems.map((item) => <button type="button" role="menuitem" key={item.label}
        onClick={() => { setOpen(false); item.onSelect() }}>
        {item.label}{item.hint && <small>{item.hint}</small>}
      </button>)}
    </div>}
  </div>
}
