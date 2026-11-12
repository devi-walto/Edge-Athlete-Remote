// Sessions.jsx — /athlete/sessions: every session the athlete has lifted in.
//
// Why this file exists: Home shows only the last five. This page lists them all, newest
// first, under a heading per month (spec 10, Phase 3; board F_Ath_L1). The server sends 20
// at a time; the next 20 load by themselves when the athlete scrolls near the bottom
// ("Loading older sessions…"). Pressing a row opens that session, whose back link then
// leads back here. The page's only way out is its back link to Home (spec 06 rule 11).
import { useCallback, useEffect, useRef, useState } from 'react'
import Button from '../ui/Button.jsx'
import SectionLabel from '../ui/SectionLabel.jsx'
import AthletePage, { HOME_PATH, toSignIn } from './AthletePage.jsx'
import { SESSIONS, getJson, monthLabel } from './athleteApi.js'
import SessionRow, { SESSIONS_PATH } from './SessionRow.jsx'

/** [{ month: 'November 2026', sessions: [...] }, ...] in the order given (newest first). */
export function byMonth(sessions) {
  const months = []
  for (const s of sessions) {
    const month = monthLabel(s.date)
    if (months.at(-1)?.month !== month) months.push({ month, sessions: [] })
    months.at(-1).sessions.push(s)
  }
  return months
}

export default function Sessions() {
  const [sessions, setSessions] = useState([])
  const [next, setNext] = useState(undefined)      // undefined: first page not here yet; null: no more
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(false)
  const busy = useRef(false)
  const end = useRef(null)

  const loadMore = useCallback(async () => {
    if (busy.current || next === null) return
    busy.current = true
    setLoading(true)
    const url = next ? `${SESSIONS}?before=${encodeURIComponent(next)}` : SESSIONS
    const { status, body } = await getJson(url)
    busy.current = false
    setLoading(false)
    if (status === 401 || status === 403) { toSignIn(SESSIONS_PATH); return }
    if (status !== 200) { setFailed(true); return }
    setFailed(false)
    setSessions((had) => [...had, ...body.sessions])
    setNext(body.next)
  }, [next])

  useEffect(() => { if (next === undefined) loadMore() }, [next, loadMore])

  // Load the next page when the bottom of the list comes near the screen.
  useEffect(() => {
    if (!next || failed || typeof IntersectionObserver === 'undefined' || !end.current) return undefined
    const watcher = new IntersectionObserver((seen) => { if (seen.some((e) => e.isIntersecting)) loadMore() },
      { rootMargin: '300px' })
    watcher.observe(end.current)
    return () => watcher.disconnect()
  }, [next, failed, loadMore])

  return <AthletePage here={SESSIONS_PATH} back={{ label: 'Home', to: HOME_PATH }}>
    <h1 className="athlete-page-title">All sessions</h1>
    {next !== undefined && sessions.length === 0 && <p className="athlete-empty">Your sessions will show here after you lift.</p>}
    {byMonth(sessions).map(({ month, sessions: rows }) => <section key={month} aria-label={month}>
      <SectionLabel as="h2">{month}</SectionLabel>
      {rows.map((s) => <SessionRow key={s.session_id} session={s} from="sessions" />)}
    </section>)}
    <div ref={end} />
    {loading && <p className="athlete-empty" role="status">{sessions.length ? 'Loading older sessions…' : 'Loading…'}</p>}
    {failed && <p className="acct-error" role="alert">The school's server didn't answer.</p>}
    {/* Without automatic loading (an old browser) or after a failed try, a button does it. */}
    {!loading && next && (failed || typeof IntersectionObserver === 'undefined')
      && <Button kind="solid" onClick={loadMore}>{failed ? 'Try again' : 'Show older sessions'}</Button>}
  </AthletePage>
}
