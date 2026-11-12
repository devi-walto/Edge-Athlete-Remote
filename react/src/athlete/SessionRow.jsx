// SessionRow.jsx — one past session in a list: "Wed, Nov 11 · Day 1 — Lower" and "7 / 9 sets".
//
// Why this file exists: Home's Recent sessions and the All sessions page show the same row
// (spec 10, Phase 3), and pressing it opens that session. One piece keeps the two alike.
// The page it opens is told where it was opened from, so its back link can say so.
import { navigate } from '../router.js'
import QuietRow from '../ui/QuietRow.jsx'
import { SESSIONS_PATH } from './AthletePage.jsx'
import { dayLabel } from './athleteApi.js'

export { SESSIONS_PATH }

/** "9 / 9 sets", amber when short of the plan. */
export function SetsCount({ done, planned }) {
  if (!planned) return <span className="athlete-sets">{done} sets</span>
  return <span className={`athlete-sets${done < planned ? ' is-short' : ''}`}>{done} / {planned} sets</span>
}

/** from: 'sessions' when the row sits on All sessions (the past session's back link then
 *  says All sessions); left out on Home. */
export default function SessionRow({ session, from }) {
  const to = `${SESSIONS_PATH}/${session.session_id}${from ? `?from=${from}` : ''}`
  return <QuietRow as="button" type="button" className="athlete-session-row" onClick={() => navigate(to)}
    name={`${dayLabel(session.date)} · ${session.title}`}
    badge={<SetsCount done={session.sets_done} planned={session.sets_planned} />}
    actions={<span className="athlete-chevron" aria-hidden="true">›</span>} />
}
