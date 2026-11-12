// @vitest-environment jsdom
// progress.test.jsx — My Recent Progress (spec 10, Phase 4).
//
// Why this test exists: the range must behave exactly like the coach's (a preset fills both
// dates, editing a date clears the preset, the label follows); one movement opens at a time
// with its bars and an ⓘ that explains the max in place; and with kilograms chosen every
// load on the page reads kg (nearest 0.5) while every speed still reads m/s.
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
const { default: Progress, changeLabel, legendFor, maxTile } = await import('./Progress.jsx')
const { default: Home } = await import('./Home.jsx')
const { presetRange, isoDay } = await import('../coach/historyRange.js')
const { setUnit } = await import('../units.js')
const { setCoachToken, setSignedInRole } = await import('../coach/api.js')

function token(seconds) {
  const body = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + seconds })).replace(/=+$/, '')
  return `h.${body}.s`
}

const point = (label, v, lbs, partial = false, bucket = 'session') => ({ date: '2026-10-01', label, bucket, partial, top_set_avg_velocity: v, load_lbs: lbs })
const DATA = {
  range: { from: '2026-10-13', to: '2026-11-11' },
  sessions: { done: 9, planned: 12 }, sets: { done: 40, planned: 40 },
  movements: [
    { name: 'Back Squat', top_load_lbs: 245, change: 0.04, best_rep_velocity: 0.78, max: { weight_lbs: 300, source: 'estimated' },
      trend: [point('Oct 14', 0.62, 225), point('Oct 21', 0.6, 235), point('Nov 4', 0.66, 245)] },
    { name: 'Bench Press', top_load_lbs: 165, change: -0.03, best_rep_velocity: null, max: null,
      trend: [point('Oct 6', 0.5, 155, true, 'week'), point('Oct 13', 0.47, 165, false, 'week')] },
  ],
}

let host, root, calls
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); sessionStorage.clear(); setUnit('lb')
  setSignedInRole('athlete'); setCoachToken(token(3600))
  vi.mocked(navigate).mockReset()
  calls = []
  globalThis.fetch = vi.fn((url) => {
    calls.push(url)
    const body = url.startsWith('/api/athlete/progress/') ? DATA
      : url === '/api/athlete/home/' ? { athlete: { name: 'Chris Vale', first_name: 'Chris', groups: [] }, live: null, coming_up: [], recent: [] }
        : { sensors: [] }
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })
  })
  host = document.createElement('div'); document.body.appendChild(host); root = createRoot(host)
})
afterEach(() => { act(() => root.unmount()); host.remove() })

async function show(page = <Progress />) {
  await act(async () => { root.render(page) })
  for (let i = 0; i < 3; i += 1) await act(async () => {})
}
const text = () => host.textContent
const button = (label) => [...host.querySelectorAll('button')].find((b) => b.textContent.trim().startsWith(label))
const dates = () => [...host.querySelectorAll('input[type="date"]')]
const lit = () => [...host.querySelectorAll('.ui-range .ui-pills button.is-on')].map((b) => b.textContent)
async function typeDate(input, value) {
  const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
  await act(async () => { set.call(input, value); input.dispatchEvent(new Event('input', { bubbles: true })) })
  for (let i = 0; i < 2; i += 1) await act(async () => {})
}

describe('the range', () => {
  it('starts on the last 30 days and asks the server for exactly that', async () => {
    await show()
    const want = presetRange(30)
    expect(lit()).toEqual(['30d'])
    expect(dates().map((d) => d.value)).toEqual([want.from, want.to])
    expect(text()).toContain('Last 30 days')
    expect(calls).toContain(`/api/athlete/progress/?from=${want.from}&to=${want.to}`)
  })

  it('a preset fills From and To and the label follows', async () => {
    await show()
    await act(async () => { button('90d').click() })
    const want = presetRange(90)
    expect(dates().map((d) => d.value)).toEqual([want.from, want.to])
    expect(lit()).toEqual(['90d'])
    expect(text()).toContain('Last 90 days')
  })

  it('editing a date clears the preset and the label shows the two dates', async () => {
    await show()
    const from = new Date(); from.setDate(from.getDate() - 20)
    await typeDate(dates()[0], isoDay(from))
    expect(lit()).toEqual([])
    expect(text()).not.toContain('Last 30 days')
    expect(host.querySelector('.ui-range-label').textContent).toContain('–')
    expect(calls.at(-1)).toContain(`from=${isoDay(from)}`)
  })
})

describe('the movements', () => {
  it('tiles count sessions and sets against the plan, short in amber', async () => {
    await show()
    expect([...host.querySelectorAll('.ui-tiles b')].map((b) => b.textContent)).toEqual(['9 / 12', '40 / 40'])
    expect(host.querySelectorAll('.ui-tiles b.is-short')).toHaveLength(1)
  })

  it('a row: top set, a trend line, the change (amber when down)', async () => {
    await show()
    expect(text()).toContain('Top set 245 lb')
    expect(host.querySelectorAll('.ui-trend')).toHaveLength(2)
    const changes = [...host.querySelectorAll('.athlete-progress-change')]
    expect(changes.map((c) => c.textContent)).toEqual(['+0.04 m/s', '−0.03 m/s'])
    expect(changes[1].classList.contains('is-down')).toBe(true)
  })

  it('opening a movement shows its bars, legend and tiles, and closes any other', async () => {
    await show()
    await act(async () => { button('Back Squat').click() })
    expect(text()).toContain('Each bar = 1 session · its top set (m/s)')
    expect(text()).toContain('Speed above · load inside · when, below')
    expect([...host.querySelectorAll('.ui-bar-inside')].map((e) => e.textContent)).toEqual(['225 lb', '235 lb', '245 lb'])
    expect([...host.querySelectorAll('.ui-bar-below')].map((e) => e.textContent)).toEqual(['Oct 14', 'Oct 21', 'Nov 4'])
    expect(text()).toContain('Est. max')
    const values = [...host.querySelectorAll('.athlete-progress-panel .ui-tiles b')]
    expect(values.map((b) => b.textContent)).toEqual(['0.78 m/s', '245 lb', '300 lb'])
    expect(values.map((b) => b.className)).toEqual(['is-mint', '', 'is-lime'])          // as on F_Ath_P2
    await act(async () => { button('Bench Press').click() })
    expect(host.querySelectorAll('.athlete-progress-panel')).toHaveLength(1)
    expect(text()).toContain('Each bar = 1 week · its best top set (m/s)')
    expect(text()).toContain('Lighter bars: periods the range only partly covers')
    expect(host.querySelector('.ui-bar-fill.is-faded')).not.toBeNull()
    expect(text()).toContain('--')
    expect(text()).toContain('No max yet: it appears after a set of 1 to 12 reps')
  })

  it('the ⓘ opens its explanation in place', async () => {
    await show()
    await act(async () => { button('Back Squat').click() })
    expect(host.querySelector('.athlete-progress-explain')).toBeNull()
    await act(async () => { host.querySelector('.athlete-info').click() })
    expect(host.querySelector('.athlete-progress-explain').textContent).toContain('The max your weights are worked out from')
  })

  it('with kilograms chosen every load reads kg (nearest 0.5) and every speed still reads m/s', async () => {
    await show()
    await act(async () => { button('Back Squat').click() })
    await act(async () => { button('KG').click() })
    expect(text()).toContain('Top set 111 kg')
    expect([...host.querySelectorAll('.ui-bar-inside')].map((e) => e.textContent)).toEqual(['102 kg', '106.5 kg', '111 kg'])
    expect(text()).toContain('136 kg')
    expect(text()).not.toMatch(/\d lb\b/)
    expect([...host.querySelectorAll('.ui-bar-above')].every((e) => e.textContent.endsWith('m/s'))).toBe(true)
    expect(localStorage.getItem('ea_load_unit')).toBe('kg')
    // LB | KG is a setting, not the screen's action: chosen in grey, never a second lime
    expect(host.querySelector('.athlete-progress-legend .ui-pills').classList.contains('ui-pills--quiet')).toBe(true)
  })

  it('the PDF asks for the same range in the chosen unit', async () => {
    URL.createObjectURL = vi.fn(() => 'blob:x'); URL.revokeObjectURL = vi.fn()
    setUnit('kg')
    await show()
    globalThis.fetch = vi.fn(() => Promise.resolve({ ok: true, status: 200, blob: () => Promise.resolve(new Blob(['%PDF'])), json: () => Promise.resolve(DATA) }))
    await act(async () => { button('Download my report').click() })
    const want = presetRange(30)
    expect(globalThis.fetch.mock.calls.map((c) => c[0])).toContain(`/api/athlete/progress/report/?from=${want.from}&to=${want.to}&unit=kg`)
  })
})

describe('the helpers and Home', () => {
  it('words', () => {
    expect(legendFor('quarter')).toBe('Each bar = 1 quarter · its best top set (m/s)')
    expect(changeLabel(null)).toBeNull()
    expect(changeLabel(-0.003)).toBe('±0.00 m/s')                               // too small to show: not a drop
    expect(maxTile({ weight_lbs: 300, source: 'manual' }, 'lb')).toEqual({ label: 'Max', value: '300 lb', tone: 'lime' })
    expect(maxTile({ weight_lbs: 262, source: 'estimated' }, 'lb').label).toBe('Est. max')
    expect(maxTile(null, 'lb')).toEqual({ label: 'Est. max', value: '--', quiet: true })
  })

  it('Home links to My Recent Progress', async () => {
    await show(<Home />)
    await act(async () => { button('My Recent Progress').click() })
    expect(navigate).toHaveBeenCalledWith('/athlete/progress')
  })
})
