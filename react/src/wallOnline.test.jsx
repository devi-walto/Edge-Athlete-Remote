// @vitest-environment jsdom
//
// Why these tests exist: the room display (/dashboard) was built for a gym, where
// anyone on the Wi-Fi may see it, so it never sent a login. Online the server only
// shows the room to a signed-in coach, so the display was turned away and, worse, the
// refusal signed out any coach in that browser. Online it now asks a coach to sign in
// and sends that login; in a gym it must behave exactly as before, login or not.
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

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

vi.mock('./router.js', () => ({ navigate: vi.fn() }))
// No broker in a test: a client that connects to nothing.
vi.mock('mqtt', () => ({ default: { connect: () => ({ on: () => {}, subscribe: () => {}, end: () => {} }) } }))

const { default: Dashboard } = await import('./Dashboard.jsx')
const { forgetDeploymentForTests } = await import('./useDeployment.js')
const { setCoachToken, setSignedInRole } = await import('./coach/api.js')

const reply = (status, body) => ({ ok: status >= 200 && status < 300, status, json: async () => body, text: async () => JSON.stringify(body) })
const roomStateCalls = () => globalThis.fetch.mock.calls.filter(([url]) => String(url).startsWith('/api/room-state/'))
const authOf = ([, options]) => options?.headers?.Authorization

let container, root
function serverIs(deployment) {
  globalThis.fetch = vi.fn(async (url, options) => {
    const u = String(url)
    if (u.includes('/api/system/info/')) return reply(200, { deployment })
    if (u.includes('/api/auth/me/')) {
      const athlete = String(options?.headers?.Authorization || '').includes('athlete')
      return reply(200, athlete
        ? { username: 'lifter', is_staff: false, must_change_password: false, role: 'athlete', athlete_id: 7 }
        : { username: 'coach', is_staff: true, must_change_password: false, role: 'coach' })
    }
    if (u.startsWith('/api/room-state/')) return reply(200, { revision: 1, session: null, racks: [] })
    return reply(404, {})
  })
}
beforeEach(() => {
  localStorage.clear()
  forgetDeploymentForTests()
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
})
afterEach(async () => {
  await act(async () => root.unmount())
  container.remove()
  vi.restoreAllMocks()
})
async function render(element) { await act(async () => root.render(element)) }

it('online with nobody signed in: asks a coach to sign in and asks the server for no room', async () => {
  serverIs('remote')
  await render(<Dashboard mode="wall" />)
  expect(container.textContent).toContain('Coach sign in')
  expect(roomStateCalls()).toEqual([])
})

it('online with a coach signed in: shows the display, asking for the names-only room with the login', async () => {
  serverIs('remote')
  setCoachToken('coach-token'); setSignedInRole('coach')
  await render(<Dashboard mode="wall" />)
  const calls = roomStateCalls()
  expect(calls.length).toBeGreaterThan(0)
  expect(calls.every(([url]) => String(url) === '/api/room-state/')).toBe(true)
  expect(calls.every((call) => authOf(call) === 'Bearer coach-token')).toBe(true)
  expect(container.textContent).not.toContain('Coach sign in')
})

it('online with an athlete signed in: the notice, not the room', async () => {
  serverIs('remote')
  setCoachToken('athlete-token'); setSignedInRole('athlete')
  await render(<Dashboard mode="wall" />)
  expect(container.textContent).toContain('This is the coach workspace')
  expect(roomStateCalls()).toEqual([])
})

it('in a gym: the display opens with no sign-in and sends no login, as before', async () => {
  serverIs('local')
  await render(<Dashboard mode="wall" />)
  const calls = roomStateCalls()
  expect(calls.length).toBeGreaterThan(0)
  expect(calls.every((call) => authOf(call) === undefined)).toBe(true)
  expect(container.textContent).not.toContain('Coach sign in')
})

it('in a gym with a coach login left in the browser: still sends no login, so a stale one cannot break the display', async () => {
  serverIs('local')
  setCoachToken('old-token'); setSignedInRole('coach')
  await render(<Dashboard mode="wall" />)
  const calls = roomStateCalls()
  expect(calls.length).toBeGreaterThan(0)
  expect(calls.every((call) => authOf(call) === undefined)).toBe(true)
})
