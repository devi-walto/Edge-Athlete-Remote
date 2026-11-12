// @vitest-environment jsdom
// home.test.jsx — the athlete's Home and the frame around their pages (spec 10, Phase 1).
//
// Why this test exists: Home's one focus card must take the right form (live with Join,
// next, or nothing planned) with a lime button only when Join is real; a short day must
// read amber; the picture must go Home and the name must open a menu of exactly Account
// and Sign out on every athlete page; the page must ask again every 15 seconds while it's
// on screen, and not while hidden; and signing out must leave nothing to go Back to.
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../router.js', () => ({ navigate: vi.fn() }))

// Some test setups have no working browser storage; give each test a plain one.
for (const name of ['localStorage', 'sessionStorage']) {
  if (typeof globalThis[name]?.clear !== 'function') {
    const store = new Map()
    Object.defineProperty(globalThis, name, { configurable: true, value: {
      getItem: (key) => (store.has(key) ? store.get(key) : null),
      setItem: (key, value) => { store.set(key, String(value)) },
      removeItem: (key) => { store.delete(key) },
      clear: () => { store.clear() },
    } })
  }
}
vi.mock('../useDeployment.js', () => ({ default: () => 'remote', useInstallationName: () => 'Demo U' }))

const { navigate } = await import('../router.js')
const { default: Home, REFRESH_MS } = await import('./Home.jsx')
const { default: Account } = await import('./Account.jsx')
const { setCoachToken, setSignedInRole, getCoachToken } = await import('../coach/api.js')

function token(seconds) {
  const body = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + seconds })).replace(/=+$/, '')
  return `h.${body}.s`
}

const ATHLETE = { name: 'Chris Vale', first_name: 'Chris', groups: ['Varsity Football', 'Receivers'] }
const LIVE = { session_id: 41, title: 'Day 2 — Pull', groups: ['Varsity Football'], movements: ['Deadlift', 'RDL'], started_at: '2026-11-11T18:02:00' }
const NEXT = [{ date: '2026-11-11', title: 'Day 2 — Pull', groups: ['Varsity Football'], movements: ['Deadlift'], session_id: null },
  { date: '2026-11-13', title: 'Day 3 — Power', groups: ['Varsity Football'], movements: [], session_id: null }]
const RECENT = [{ session_id: 38, date: '2026-11-10', title: 'Day 1 — Lower', sets_done: 6, sets_planned: 8 },
  { session_id: 37, date: '2026-11-08', title: 'Day 0', sets_done: 9, sets_planned: 9 }]

let host, root, reply, homeCalls
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); sessionStorage.clear()
  setSignedInRole('athlete'); setCoachToken(token(3600))
  vi.mocked(navigate).mockReset()
  homeCalls = 0
  reply = { athlete: ATHLETE, live: null, coming_up: NEXT, recent: RECENT }
  globalThis.fetch = vi.fn((url) => {
    if (url === '/api/athlete/home/') homeCalls += 1
    const body = url === '/api/athlete/home/' ? reply : url === '/api/athlete/sensors/' ? { sensors: [] } : {}
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })
  })
  host = document.createElement('div'); document.body.appendChild(host); root = createRoot(host)
})
afterEach(() => { act(() => root.unmount()); host.remove(); vi.useRealTimers() })

async function show(page = <Home />) {
  await act(async () => { root.render(page) })
  await act(async () => {}); await act(async () => {})
}
const limeButtons = () => host.querySelectorAll('.ui-button--primary, .ui-button--next')
const text = () => host.textContent

describe('the focus card', () => {
  it('live: Live now, the day, and Join session as the one lime button', async () => {
    reply = { ...reply, live: LIVE }
    await show()
    expect(text()).toContain('Live now · started')
    expect(text()).toContain('Day 2 — Pull')
    expect(text()).toContain('Varsity Football · Deadlift · RDL')
    expect(limeButtons()).toHaveLength(1)
    expect(limeButtons()[0].textContent).toBe('Join session')
    await act(async () => { limeButtons()[0].click() })
    expect(navigate).toHaveBeenCalledWith('/session/41')
  })

  it('next: the date, the day, the Join hint and the day after, with no lime button', async () => {
    await show()
    expect(text()).toContain('Next · Wed, Nov 11')
    expect(text()).toContain('A Join button appears here when your coach starts it.')
    expect(text()).toContain('Then: Fri, Nov 13 · Day 3 — Power')
    expect(limeButtons()).toHaveLength(0)
  })

  it('nothing planned says so, with no lime button', async () => {
    reply = { ...reply, coming_up: [] }
    await show()
    expect(text()).toContain('Nothing scheduled yet')
    expect(text()).toContain('Your coach will add your sessions here.')
    expect(limeButtons()).toHaveLength(0)
  })
})

describe('the rest of Home', () => {
  it('greets them by first name with their groups', async () => {
    await show()
    expect(host.querySelector('h1').textContent).toBe('Hi Chris')
    expect(text()).toContain('Varsity Football · Receivers')
  })

  it('a short day reads amber, a full one does not', async () => {
    await show()
    const counts = [...host.querySelectorAll('.athlete-sets')]
    expect(counts.map((c) => c.textContent)).toEqual(['6 / 8 sets', '9 / 9 sets'])
    expect(counts[0].classList.contains('is-short')).toBe(true)
    expect(counts[1].classList.contains('is-short')).toBe(false)
  })

  it('asks again every 15 seconds while on screen, and not while hidden', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    await show()
    const first = homeCalls
    reply = { ...reply, live: LIVE }
    await act(async () => { await vi.advanceTimersByTimeAsync(REFRESH_MS) })
    expect(homeCalls).toBe(first + 1)
    expect(text()).toContain('Join session')

    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' })
    await act(async () => { await vi.advanceTimersByTimeAsync(REFRESH_MS * 2) })
    expect(homeCalls).toBe(first + 1)
    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' })
  })
})

describe('the top bar on every athlete page', () => {
  it.each([['Home', <Home key="h" />], ['Account', <Account key="a" />]])('on %s: picture goes Home, name opens Account and Sign out', async (_, page) => {
    await show(page)
    await act(async () => { host.querySelector('button[aria-label="Home"]').click() })
    expect(navigate).toHaveBeenCalledWith('/athlete/home')
    await act(async () => { host.querySelector('button[aria-haspopup="menu"]').click() })
    const items = [...host.querySelectorAll('[role="menuitem"]')].map((b) => b.firstChild.textContent)
    expect(items).toEqual(['Account', 'Sign out'])
  })

  it('a drill-down page has one back link, to Home', async () => {
    await show(<Account />)
    const back = host.querySelector('.ui-backlink')
    expect(back.textContent).toBe('‹ Home')
    await act(async () => { back.click() })
    expect(navigate).toHaveBeenCalledWith('/athlete/home')
  })

  it('Sign out forgets the login and replaces the page, so Back cannot show Home', async () => {
    await show()
    await act(async () => { host.querySelector('button[aria-haspopup="menu"]').click() })
    await act(async () => { [...host.querySelectorAll('[role="menuitem"]')][1].click() })
    expect(getCoachToken()).toBeNull()
    expect(navigate).toHaveBeenCalledWith('/athlete', { replace: true })
  })

  it('a phone that is not signed in goes to sign-in, and back to Home afterwards', async () => {
    localStorage.clear()
    await show()
    expect(navigate).toHaveBeenCalledWith('/athlete', { replace: true })
    expect(sessionStorage.getItem('athlete_after_sign_in')).toBe('/athlete/home')
  })
})
