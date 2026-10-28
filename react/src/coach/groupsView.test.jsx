// @vitest-environment jsdom
// Why these tests exist: on the Groups tab, opening a group and picking an athlete
// used to close again seconds later. The coach screen redraws on every live-room
// refresh and handed the tab a new copy of its sign-out function each time, and the
// opened group took that as "something changed": it reloaded and dropped the athlete.
// These pin that a redraw keeps the athlete open and asks the server for nothing.
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

vi.mock('../useDeployment.js', () => ({ default: () => 'remote' }))
vi.mock('../AthleteWorkoutPlanning.jsx', () => ({
  default: ({ athlete }) => <p data-testid="plans">Plans for {athlete.name}</p>,
}))

const { default: GroupsView } = await import('./GroupsView.jsx')

const GROUP = { id: 5, name: 'Varsity', athlete_count: 2, head_coach: null, coaches: [] }
const MEMBERS = [{ id: 1, name: 'Riley Brooks' }, { id: 2, name: 'Jordan Lee' }]

function reply(status, body) {
  return Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) })
}

let container, root
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  globalThis.fetch = vi.fn((url) => {
    if (url === '/api/training-groups/') return reply(200, [GROUP])
    if (url === '/api/training-groups/5/athletes/') return reply(200, MEMBERS)
    if (url === '/api/athletes/') return reply(200, MEMBERS)
    return reply(404, {})
  })
  container = document.createElement('div')
  document.body.appendChild(container)
  root = createRoot(container)
})
afterEach(() => {
  act(() => root.unmount())
  container.remove()
})

// Each call hands down a NEW sign-out function, the way a redraw of the coach
// screen did before it kept one.
async function draw() {
  await act(async () => { root.render(<GroupsView accessToken="t" onLogout={() => {}} />) })
  await act(async () => {})
}
const buttonNamed = (text) => [...container.querySelectorAll('button')].find((b) => b.textContent === text)
const rosterRequests = () =>
  globalThis.fetch.mock.calls.filter(([url]) => url === '/api/training-groups/5/athletes/').length

it('keeps the athlete a coach opened when the screen redraws', async () => {
  await draw()
  await act(async () => { buttonNamed('Open').click() })
  await act(async () => {})
  await act(async () => { buttonNamed('Riley Brooks').click() })
  expect(container.querySelector('[data-testid="plans"]').textContent).toBe('Plans for Riley Brooks')
  const before = rosterRequests()

  await draw()
  await draw()

  expect(container.querySelector('[data-testid="plans"]')?.textContent).toBe('Plans for Riley Brooks')
  expect(buttonNamed('Riley Brooks').getAttribute('aria-pressed')).toBe('true')
  expect(rosterRequests()).toBe(before)
})

it('still signs the coach out when the server turns the roster away', async () => {
  const onLogout = vi.fn()
  globalThis.fetch = vi.fn((url) => {
    if (url === '/api/training-groups/') return reply(200, [GROUP])
    if (url === '/api/athletes/') return reply(200, MEMBERS)
    if (url === '/api/training-groups/5/athletes/') {
      // the tab's own first load answers; the opened group's load is refused
      return globalThis.fetch.mock.calls.filter(([u]) => u === url).length > 1
        ? reply(401, {}) : reply(200, MEMBERS)
    }
    return reply(404, {})
  })
  await act(async () => { root.render(<GroupsView accessToken="t" onLogout={onLogout} />) })
  await act(async () => {})
  await act(async () => { buttonNamed('Open').click() })
  await act(async () => {})

  expect(onLogout).toHaveBeenCalled()
})
