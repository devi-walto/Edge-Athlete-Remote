// @vitest-environment jsdom
// Tests for "My sensor" on the athlete's page (spec 14, Phase 2): adding a sensor with
// a one-time code, the page noticing by itself when the sensor uses it, and removing a
// sensor. Online only: a gym's page never shows it.
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

let deployment = 'remote'
vi.mock('../useDeployment.js', () => ({
  default: () => deployment,
  useInstallationName: () => 'Demo U',
}))
vi.mock('../router.js', () => ({ navigate: vi.fn() }))

if (typeof globalThis.localStorage?.clear !== 'function') {
  const store = new Map()
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key) => (store.has(key) ? store.get(key) : null),
      setItem: (key, value) => { store.set(key, String(value)) },
      removeItem: (key) => { store.delete(key) },
      clear: () => { store.clear() },
    },
  })
}

const { default: AthleteSignIn } = await import('./AthleteSignIn.jsx')
const { schoolPart, sensorStatus } = await import('./MySensor.jsx')
const { setCoachToken, setSignedInRole } = await import('../coach/api.js')

function token(seconds) {
  const body = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + seconds }))
    .replace(/=+$/, '').replace(/\+/g, '-').replace(/\//g, '_')
  return `h.${body}.s`
}

const IN_15 = new Date(Date.now() + 15 * 60_000).toISOString()
let container, root, calls, sensors, codeStatus
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear()
  setSignedInRole('athlete')
  setCoachToken(token(3600))
  calls = []
  sensors = []
  codeStatus = { status: 'waiting', sensor: null }
  globalThis.fetch = vi.fn((url, options = {}) => {
    const method = options.method || 'GET'
    calls.push(`${method} ${url}`)
    let status = 404, body = {}
    if (url === '/api/athlete/sensors/' && method === 'GET') { status = 200; body = { sensors } }
    if (url === '/api/athlete/sensor-code/' && method === 'POST') {
      status = 201; body = { code: 'K7MQ-2XPR', expires_at: IN_15 }
    }
    if (url === '/api/athlete/sensor-code/' && method === 'GET') { status = 200; body = codeStatus }
    if (url.startsWith('/api/athlete/sensors/ea-') && method === 'DELETE') { status = 204; sensors = [] }
    return Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) })
  })
  container = document.createElement('div')
  document.body.appendChild(container)
  root = createRoot(container)
})
afterEach(() => {
  act(() => root.unmount())
  container.remove()
  vi.useRealTimers()
  deployment = 'remote'
})

async function show() {
  await act(async () => { root.render(<AthleteSignIn />) })
  await act(async () => {})
  await act(async () => {})
}
const button = (text) => [...container.querySelectorAll('button')].find((b) => b.textContent === text)
async function press(text) {
  await act(async () => { button(text).click() })
  await act(async () => {})
}

describe('whether a sensor is connected', () => {
  it('reads its last pulse', () => {
    const now = Date.parse('2026-10-20T12:00:00Z')
    expect(sensorStatus(null, now).text).toBe('Not connected yet')
    expect(sensorStatus('2026-10-20T11:59:50Z', now)).toEqual({ connected: true, text: 'Connected · seen just now' })
    expect(sensorStatus('2026-10-20T11:48:00Z', now).text).toBe('Last seen 12 min ago')
    expect(sensorStatus('2026-10-20T09:00:00Z', now).text).toBe('Last seen 3 h ago')
  })
})

describe('adding a sensor', () => {
  it('shows None yet, then the code, then notices by itself when the sensor uses it', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    await show()
    expect(container.textContent).toContain('None yet')
    await press('Add my sensor')
    expect(container.textContent).toContain('K7MQ-2XPR')
    expect(container.textContent).toContain('Waiting for your sensor…')
    expect(container.textContent).toContain('Never type your password into a sensor')

    codeStatus = { status: 'used', sensor: 'ea-3f9c' }
    await act(async () => { await vi.advanceTimersByTimeAsync(3100) })
    expect(container.textContent).toContain('ea-3f9c is added and connected')
    expect(container.textContent).toContain("Used. It won't work again.")

    sensors = [{ node_id: 'ea-3f9c', last_seen: new Date().toISOString(), is_active: true }]
    await press('Done')
    expect(container.textContent).toContain('ea-3f9c')
    expect(container.textContent).toContain('Connected · seen just now')
  })

  // The sensor's setup page fills the phone's screen, so the code is the one thing the
  // athlete copies; the school is shown to remember (F_Ath_S2, 2026-10-27).
  it('copies the code with one press', async () => {
    const writeText = vi.fn(() => Promise.resolve())
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })
    await show()
    await press('Add my sensor')
    await press('Copy')
    expect(writeText).toHaveBeenCalledWith('K7MQ-2XPR')
    expect(container.textContent).toContain('Copied ✓')
    delete navigator.clipboard
  })

  it('says when the code ran out, and a new code can be got', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    await show()
    await press('Add my sensor')
    codeStatus = { status: 'expired', sensor: null }
    await act(async () => { await vi.advanceTimersByTimeAsync(3100) })
    expect(container.textContent).toContain('This code ran out.')
    await press('Get a new code')
    expect(calls.filter((c) => c === 'POST /api/athlete/sensor-code/')).toHaveLength(2)
    expect(container.textContent).toContain('Waiting for your sensor…')
  })
})

describe('removing a sensor', () => {
  it('asks first, then removes it', async () => {
    sensors = [{ node_id: 'ea-3f9c', last_seen: null, is_active: true }]
    await show()
    await press('Remove')
    expect(container.querySelector('[role="dialog"]').textContent).toContain('Remove ea-3f9c?')
    await press('Keep it')
    expect(container.querySelector('[role="dialog"]')).toBeNull()
    expect(calls).not.toContain('DELETE /api/athlete/sensors/ea-3f9c/')
    await press('Remove')
    await press('Remove sensor')
    expect(calls).toContain('DELETE /api/athlete/sensors/ea-3f9c/')
    expect(container.textContent).toContain('None yet')
  })
})

describe('a local install', () => {
  it('never shows My sensor', async () => {
    deployment = 'local'
    await show()
    expect(container.textContent).toContain("You're signed in")
    expect(container.textContent).not.toContain('My sensor')
    expect(calls).not.toContain('GET /api/athlete/sensors/')
  })
})

describe('the school to remember', () => {
  it('is the first part of the page\'s own address', () => {
    expect(schoolPart('test.example.com')).toBe('test')
    expect(schoolPart('demo-u-k7m2qx.example.com')).toBe('demo-u-k7m2qx')
  })

  it('is left out where the address has no such part', () => {
    expect(schoolPart('localhost')).toBeNull()
    expect(schoolPart('example.com')).toBeNull()
    expect(schoolPart('10.0.0.5')).toBeNull()
  })
})
