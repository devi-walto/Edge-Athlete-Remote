// @vitest-environment jsdom
//
// Why these tests exist: athletes have logins now. The server refuses every coach
// action for them, so the coach workspace must not even try: an athlete who lands here
// gets a plain notice and nothing else is loaded. These also pin the two messages a
// refused sign-in can show, because "wrong password" for a login that is merely not
// set up sends someone off to reset a password that works.
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

vi.mock('../router.js', () => ({ navigate: vi.fn() }))

const { default: Dashboard } = await import('../Dashboard.jsx')
const { default: AccountPage } = await import('./AccountPage.jsx')
const { coachLogin, getCoachToken, getSignedInRole, setCoachToken, setSignedInRole } = await import('./api.js')

const reply = (status, body) => ({ ok: status >= 200 && status < 300, status, json: async () => body, text: async () => JSON.stringify(body) })
const asked = () => globalThis.fetch.mock.calls.map(([url]) => String(url))

let container, root
beforeEach(() => {
  localStorage.clear()
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  globalThis.fetch = vi.fn(async (url) => (String(url).includes('/api/auth/me/')
    ? reply(200, { username: 'lifter', is_staff: false, must_change_password: false, role: 'athlete', athlete_id: 7, athlete_name: 'Jordan Lee' })
    : reply(403, { detail: 'You do not have permission to perform this action.' })))
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
function signedInAs(role) { setCoachToken('a-token'); setSignedInRole(role) }

it('shows an athlete the notice on the coach workspace and asks the server for nothing a coach would', async () => {
  signedInAs('athlete')
  await render(<Dashboard mode="coach" />)

  expect(container.textContent).toContain('This is the coach workspace')
  expect(container.textContent).toContain('Use the session link your coach sent you')
  expect(container.querySelector('.monitor')).toBeNull()
  // "who am I" is for every role; anything else would be a coach request
  expect(asked().filter((url) => !url.includes('/api/auth/'))).toEqual([])
})

it('signs the athlete out from the notice, back to an empty sign-in form', async () => {
  signedInAs('athlete')
  await render(<Dashboard mode="coach" />)
  const button = [...container.querySelectorAll('button')].find((b) => b.textContent === 'Sign out')
  await act(async () => button.click())

  expect(getCoachToken()).toBeNull()
  expect(getSignedInRole()).toBeNull()
  expect(container.textContent).toContain('Coach sign in')
})

it('still turns an athlete away when the role was not stored, once the server says who they are', async () => {
  setCoachToken('a-token')
  await render(<AccountPage page="coaches" />)
  expect(container.textContent).toContain('This is the coach workspace')
  expect(getSignedInRole()).toBe('athlete')
})

it('shows the same notice on the account pages', async () => {
  signedInAs('athlete')
  await render(<AccountPage page="coaches" />)
  expect(container.textContent).toContain('This is the coach workspace')
  expect(asked().filter((url) => !url.includes('/api/auth/'))).toEqual([])
})

it('remembers the role the server reported at sign-in, and forgets it on sign-out', async () => {
  globalThis.fetch = vi.fn(async () => reply(200, { access: 'tok', refresh: 'r', role: 'coach', must_change_password: false }))
  expect(await coachLogin('assistant', 'pw')).toBe('tok')
  expect(getSignedInRole()).toBe('coach')
  setCoachToken(null)
  expect(getSignedInRole()).toBeNull()
})

it('tells a login that is not set up so, and a wrong password that it was not accepted', async () => {
  const sentence = 'This login is not set up as a coach or an athlete. Ask an administrator to set it up.'
  globalThis.fetch = vi.fn(async () => reply(401, { detail: sentence, code: 'no_role' }))
  await expect(coachLogin('half_made', 'pw')).rejects.toThrow(sentence)

  globalThis.fetch = vi.fn(async () => reply(401, { detail: 'No active account found with the given credentials' }))
  await expect(coachLogin('assistant', 'nope')).rejects.toThrow('The username or password was not accepted.')
  expect(getCoachToken()).toBeNull()
})

it('does not accept an athlete where only a coach will do, and keeps nothing', async () => {
  globalThis.fetch = vi.fn(async () => reply(200, { access: 'tok', role: 'athlete' }))
  await expect(coachLogin('lifter', 'pw', { persist: false, coachOnly: true })).rejects.toThrow('Only a coach can do this')
  expect(getCoachToken()).toBeNull()
})
