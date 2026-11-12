// @vitest-environment jsdom
// history.test.jsx — All sessions and a past session (spec 10, Phase 3).
//
// Why this test exists: an athlete looking back must see every session once, grouped by
// month, with older ones loading as they scroll; a past session must say "not measured"
// for a set typed in by hand (never 0.00) and offer nothing to open there; a measured set
// must open its reps in place, coloured by the rack screen's rule; the back link must
// lead to wherever the page was opened from; and Home's recent rows must open sessions.
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../router.js', () => ({ navigate: vi.fn() }))
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
const { default: Sessions, byMonth } = await import('./Sessions.jsx')
const { default: PastSession, backFor, setLine } = await import('./PastSession.jsx')
const { default: Home } = await import('./Home.jsx')
const { setCoachToken, setSignedInRole } = await import('../coach/api.js')

function token(seconds) {
  const body = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + seconds })).replace(/=+$/, '')
  return `h.${body}.s`
}

const row = (id, date, title = `Day ${id}`) => ({ session_id: id, date, title, sets_done: 3, sets_planned: 3 })
const PAGE_1 = { sessions: [row(50, '2026-11-10'), row(49, '2026-11-03'), row(48, '2026-10-29')], next: '2026-10-29T18:00:00+00:00_48' }
const PAGE_2 = { sessions: [row(47, '2026-10-20'), row(46, '2026-09-30')], next: null }
const DAY = {
  session_id: 50, date: '2026-11-10', title: 'Day 1 — Lower', groups: ['Varsity Football'],
  totals: { sets_done: 3, sets_planned: 5, reps: 14, avg_velocity: 0.6 },
  movements: [
    { name: 'Back Squat', sets_planned: 3, zone_min: 0.55, sets: [
      { set_number: 1, weight_lbs: 225, reps: 5, avg_velocity: 0.6, reps_detail: [0.66, 0.63, 0.6, 0.55, 0.5] },
      { set_number: 2, weight_lbs: 225, reps: 5, avg_velocity: 0.62, reps_detail: [0.64, 0.63, 0.62, 0.61, 0.6] }] },
    { name: 'Bench Press', sets_planned: 2, zone_min: null, sets: [
      { set_number: 3, weight_lbs: 165, reps: 4, avg_velocity: null, reps_detail: [] }] },
  ],
}

let host, root, calls, watchers
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); sessionStorage.clear()
  setSignedInRole('athlete'); setCoachToken(token(3600))
  vi.mocked(navigate).mockReset()
  calls = []
  globalThis.fetch = vi.fn((url) => {
    calls.push(url)
    const body = url === '/api/athlete/sessions/' ? PAGE_1
      : url.startsWith('/api/athlete/sessions/?before=') ? PAGE_2
        : url === '/api/athlete/sessions/50/' ? DAY
          : url === '/api/athlete/home/' ? { athlete: { name: 'Chris Vale', first_name: 'Chris', groups: [] }, live: null, coming_up: [], recent: PAGE_1.sessions }
            : url === '/api/athlete/sensors/' ? { sensors: [] } : null
    return Promise.resolve({ ok: !!body, status: body ? 200 : 404, json: () => Promise.resolve(body || {}) })
  })
  // A stand-in for the browser's "is this on screen yet?" watcher, fired by the test.
  watchers = []
  globalThis.IntersectionObserver = class {
    constructor(callback) { this.callback = callback; watchers.push(this) }
    observe() {}
    disconnect() { watchers = watchers.filter((w) => w !== this) }
  }
  host = document.createElement('div'); document.body.appendChild(host); root = createRoot(host)
})
afterEach(() => { act(() => root.unmount()); host.remove(); window.history.replaceState({}, '', '/') })

async function show(page) {
  await act(async () => { root.render(page) })
  for (let i = 0; i < 3; i += 1) await act(async () => {})
}
const text = () => host.textContent
const button = (label) => [...host.querySelectorAll('button')].find((b) => b.textContent.includes(label))

describe('All sessions', () => {
  it('groups rows by month, newest first', async () => {
    await show(<Sessions />)
    expect([...host.querySelectorAll('h2')].map((h) => h.textContent)).toEqual(['November 2026', 'October 2026'])
    expect(byMonth(PAGE_1.sessions).map((m) => m.sessions.length)).toEqual([2, 1])
  })

  it('loads the next page when the bottom comes near, then stops at the end', async () => {
    await show(<Sessions />)
    await act(async () => { watchers.at(-1).callback([{ isIntersecting: true }]) })
    for (let i = 0; i < 3; i += 1) await act(async () => {})
    expect(calls).toContain(`/api/athlete/sessions/?before=${encodeURIComponent(PAGE_1.next)}`)
    expect([...host.querySelectorAll('.athlete-session-row')]).toHaveLength(5)
    expect(text()).toContain('September 2026')
    expect(watchers).toHaveLength(0)                                   // no more pages: stops watching
  })

  it('says it is loading older sessions while the next page is on its way', async () => {
    await show(<Sessions />)
    globalThis.fetch = vi.fn(() => new Promise(() => {}))              // never answers
    await act(async () => { watchers.at(-1).callback([{ isIntersecting: true }]) })
    expect(text()).toContain('Loading older sessions…')
  })

  it('a row opens its session, telling it where it came from; the back link goes Home', async () => {
    await show(<Sessions />)
    await act(async () => { host.querySelector('.athlete-session-row').click() })
    expect(navigate).toHaveBeenCalledWith('/athlete/sessions/50?from=sessions')
    await act(async () => { host.querySelector('.ui-backlink').click() })
    expect(navigate).toHaveBeenCalledWith('/athlete/home')
  })
})

describe('a past session', () => {
  it('shows the banner, sets of planned, reps and average speed', async () => {
    await show(<PastSession sessionId={50} />)
    expect(host.querySelector('h1').textContent).toBe('Day 1 — Lower')
    expect(text()).toContain('Tue, Nov 10 · Varsity Football')
    const tiles = [...host.querySelectorAll('.athlete-tiles b')].map((b) => b.textContent)
    expect(tiles).toEqual(['3 / 5', '14', '0.60'])
    expect(host.querySelector('.athlete-tiles b').classList.contains('is-short')).toBe(true)
  })

  it('a typed-in set reads not measured, never 0.00, and has nothing to open', async () => {
    await show(<PastSession sessionId={50} />)
    expect(text()).toContain('Set 3 · 165 lb × 4 · not measured')
    expect(text()).not.toContain('0.00')
    const typed = [...host.querySelectorAll('.athlete-set')].find((r) => r.textContent.includes('Set 3'))
    expect(typed.tagName).not.toBe('BUTTON')
    expect(typed.hasAttribute('aria-expanded')).toBe(false)
    expect(setLine(DAY.movements[1].sets[0])).toBe('Set 3 · 165 lb × 4 · not measured')
  })

  it('pressing a measured set opens its reps in place, coloured like the rack screen', async () => {
    await show(<PastSession sessionId={50} />)
    expect(host.querySelector('.athlete-rep')).toBeNull()
    await act(async () => { button('Set 1 · 225 lb × 5 · 0.60 m/s').click() })
    const reps = [...host.querySelectorAll('.athlete-rep')]
    expect(reps.map((r) => r.getAttribute('aria-label'))).toEqual(
      ['Rep 1: 0.66 m/s', 'Rep 2: 0.63 m/s', 'Rep 3: 0.60 m/s', 'Rep 4: 0.55 m/s', 'Rep 5: 0.50 m/s'])
    // Zone starts at 0.55: on target, then fading (amber) below it.
    expect([...host.querySelectorAll('.athlete-rep-bar')].map((b) => b.dataset.color))
      .toEqual(['green', 'green', 'green', 'green', 'yellow'])
    expect(text()).toContain('Speed dropped 24% from first rep to last')
    await act(async () => { button('Set 1').click() })                // press again: closes
    expect(host.querySelector('.athlete-rep')).toBeNull()
  })

  it('the back link names All sessions when opened from there, Home otherwise', async () => {
    expect(backFor('?from=sessions')).toEqual({ label: 'All sessions', to: '/athlete/sessions' })
    expect(backFor('')).toEqual({ label: 'Home', to: '/athlete/home' })
    window.history.replaceState({}, '', '/athlete/sessions/50?from=sessions')
    await show(<PastSession sessionId={50} />)
    expect(host.querySelector('.ui-backlink').textContent).toContain('All sessions')
    await act(async () => { host.querySelector('.ui-backlink').click() })
    expect(navigate).toHaveBeenCalledWith('/athlete/sessions')
  })

  it('opened from Home, the back link says Home', async () => {
    window.history.replaceState({}, '', '/athlete/sessions/50')
    await show(<PastSession sessionId={50} />)
    expect(host.querySelector('.ui-backlink').textContent).toContain('Home')
  })

  it('a session that is not theirs says so', async () => {
    await show(<PastSession sessionId={999} />)
    expect(text()).toContain("This session isn't one of yours")
  })
})

describe('Home leads into history', () => {
  it('a recent row opens that session with Home as its way back; View all opens the list', async () => {
    await show(<Home />)
    await act(async () => { host.querySelector('.athlete-session-row').click() })
    expect(navigate).toHaveBeenCalledWith('/athlete/sessions/50')
    await act(async () => { button('View all sessions').click() })
    expect(navigate).toHaveBeenCalledWith('/athlete/sessions')
  })
})
