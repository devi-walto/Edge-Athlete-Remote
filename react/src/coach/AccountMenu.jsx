// AccountMenu.jsx — the coach's top-left corner: the picture goes to Planning, the
// name opens the account menu.
//
// Why this file exists: the corner of every coach screen is the coach's own account.
// Spec 06 rule 12 split it in two (Devin, 2026-11-11): the picture is always the way
// Home, and a coach's Home is Planning, whether or not a training day is running (going
// there leaves the day running). The coach's name opens the menu: who is signed in,
// whether they are an administrator, and the three things a coach does to their own
// login. The corner itself is the shared TopBar (ui/TopBar.jsx), the same one the
// athlete's pages use.
//
// "Coaches" is shown to administrators only. That is a courtesy, not the lock: the
// server refuses a regular coach on those routes whether or not they can see the button.
import { navigate } from '../router.js'
import TopBar from '../ui/TopBar.jsx'
import { pathForCoachState } from './coachState.js'
import './account.css'

export const COACHES_PATH = '/coach/account/coaches'
export const PASSWORD_PATH = '/coach/account/password'

export default function AccountMenu({ me, onLogout }) {
  const admin = me?.role === 'administrator'
  const header = <>
    <span className="acct-label">Signed in as</span>
    <span className="acct-signed-in"><b>{me?.username || '…'}</b>{admin && <em className="acct-badge">Administrator</em>}</span>
  </>
  const items = [
    ...(admin ? [{ label: 'Coaches', hint: 'administrators only', onSelect: () => navigate(COACHES_PATH) }] : []),
    { label: 'Change password', onSelect: () => navigate(PASSWORD_PATH) },
    { label: 'Log out', onSelect: onLogout },
  ]
  return <TopBar name={me?.username || '…'} onHome={() => navigate(pathForCoachState('planning'))}
    menuHeader={header} menuItems={items} />
}
