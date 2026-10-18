// @vitest-environment jsdom
// Tests for the athlete's two pages (spec 03, Phase 4): opening a login link, and
// signing in after that. Plus staying signed in: the 30-day renewal.
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

let deployment = 'remote'
vi.mock('../useDeployment.js', () => ({
  default: () => deployment,
  useInstallationName: () => 'Demo U',
}))
vi.mock('../router.js', () => ({ navigate: vi.fn() }))

// Same in-memory store as the coach tests, for Node versions without a working one.
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

const { navigate } = await import('../router.js')
const { default: LoginLinkPage } = await import('./LoginLinkPage.jsx')
const { default: AthleteSignIn } = await import('./AthleteSignIn.jsx')
const { default: SignIn } = await import('../coach/SignIn.jsx')
const { freshAthleteToken } = await import('./athleteAuth.js')
const { getCoachToken, getRefreshToken, getSignedInRole, setCoachToken, setRefreshToken,
  setSignedInRole } = await import('../coach/api.js')

/** A sign-in token that runs out `seconds` from now (only its expiry is read). */
function token(seconds) {
  const body = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + seconds }))
    .replace(/=+$/, '').replace(/\+/g, '-').replace(/\//g, '_')
  return `h.${body}.s`
}

function reply(status, body) {
  return Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) })
}

let container, root, calls, answers
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear()
  vi.mocked(navigate).mockReset()
  calls = []
  answers = {}
  globalThis.fetch = vi.fn((url, options = {}) => {
    calls.push({ url, body: options.body ? JSON.parse(options.body) : null })
    const answer = answers[url]
    return answer ? reply(...answer) : reply(404, {})
  })
  container = document.createElement('div')
  document.body.appendChild(container)
  root = createRoot(container)
})
afterEach(() => {
  act(() => root.unmount())
  container.remove()
  window.history.replaceState(null, '', '/')
  deployment = 'remote'
})

async function show(element) {
  await act(async () => { root.render(element) })
  await act(async () => {})
}
const input = (label) => [...container.querySelectorAll('label')]
  .find((l) => l.textContent.startsWith(label)).querySelector('input')
const button = (text) => [...container.querySelectorAll('button')].find((b) => b.textContent === text)
async function type(label, value) {
  const field = input(label)
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
  await act(async () => {
    setter.call(field, value)
    field.dispatchEvent(new Event('input', { bubbles: true }))
  })
}
async function submit() {
  await act(async () => { container.querySelector('form').requestSubmit() })
  await act(async () => {})
}

describe('opening a login link', () => {
  const LINK = 'abc123lookup.s3cret'
  beforeEach(() => {
    window.history.replaceState(null, '', `/login-link#${LINK}`)
    answers['/api/auth/login-link/lookup/'] = [200, { athlete_name: 'Riley Brooks' }]
  })

  it('greets the athlete by first name, and wipes the link from the address bar', async () => {
    await show(<LoginLinkPage />)
    expect(container.querySelector('h1').textContent).toBe('Hi Riley')
    expect(container.textContent).toContain('Demo U')
    expect(calls[0].body).toEqual({ link: LINK })
    expect(window.location.hash).toBe('')
  })

  it('two different passwords are caught before anything is sent', async () => {
    await show(<LoginLinkPage />)
    await type('Username', 'riley')
    await type('Password again', 'two')
    await type('Password', 'one')
    await submit()
    expect(container.textContent).toContain('The two passwords are not the same.')
    expect(calls.map((c) => c.url)).not.toContain('/api/auth/login-link/redeem/')
  })

  it('a taken username shows next to the field, and the link stays usable', async () => {
    answers['/api/auth/login-link/redeem/'] = [400, {
      detail: 'Please fix the highlighted fields.', fields: { username: ['That username is already taken.'] },
    }]
    await show(<LoginLinkPage />)
    await type('Username', 'coach')
    await type('Password', 'Long-enough-2026')
    await type('Password again', 'Long-enough-2026')
    await submit()
    expect(container.textContent).toContain('That username is already taken.')
    expect(container.querySelector('h1').textContent).toBe('Hi Riley')
  })

  it('creating the login signs the athlete in for 30 days and goes to /athlete', async () => {
    answers['/api/auth/login-link/redeem/'] = [201, {
      access: token(3600), refresh: 'renewal-token', role: 'athlete', athlete_name: 'Riley Brooks',
    }]
    await show(<LoginLinkPage />)
    await type('Username', 'riley')
    await type('Password', 'Long-enough-2026')
    await type('Password again', 'Long-enough-2026')
    await submit()
    expect(calls.at(-1).body).toEqual({ link: LINK, username: 'riley', password: 'Long-enough-2026' })
    expect(getSignedInRole()).toBe('athlete')
    expect(getRefreshToken()).toBe('renewal-token')
    expect(navigate).toHaveBeenCalledWith('/athlete', { replace: true })
  })

  it('a link that doesn’t work says so, and offers sign in', async () => {
    answers['/api/auth/login-link/lookup/'] = [404, { detail: 'x' }]
    await show(<LoginLinkPage />)
    expect(container.querySelector('h1').textContent).toBe("This link doesn't work any more")
    await act(async () => { button('I already have a login').click() })
    expect(navigate).toHaveBeenCalledWith('/athlete')
  })

  it('no link at all is a link that doesn’t work, without asking the server', async () => {
    window.history.replaceState(null, '', '/login-link')
    await show(<LoginLinkPage />)
    expect(container.querySelector('h1').textContent).toBe("This link doesn't work any more")
    expect(calls).toEqual([])
  })
})

describe('athlete sign in', () => {
  it('signs an athlete in', async () => {
    answers['/api/auth/login/'] = [200, { access: token(3600), refresh: 'r', role: 'athlete' }]
    await show(<AthleteSignIn />)
    expect(container.querySelector('h1').textContent).toBe('Athlete sign in')
    expect(container.textContent).toContain('Forgot it? Ask your coach for a new login link.')
    await type('Username', 'riley')
    await type('Password', 'pw')
    await submit()
    expect(container.querySelector('h1').textContent).toBe("You're signed in")
  })

  it('turns a coach login away, and keeps nothing', async () => {
    answers['/api/auth/login/'] = [200, { access: token(3600), refresh: 'r', role: 'coach' }]
    await show(<AthleteSignIn />)
    await type('Username', 'coach')
    await type('Password', 'pw')
    await submit()
    expect(container.textContent).toContain('That is a coach login.')
    expect(getCoachToken()).toBeNull()
  })

  it('a phone that is still signed in goes straight to the signed-in page', async () => {
    setCoachToken(token(3600))
    setSignedInRole('athlete')
    await show(<AthleteSignIn />)
    expect(container.querySelector('h1').textContent).toBe("You're signed in")
    await act(async () => { button('Sign out').click() })
    expect(container.querySelector('h1').textContent).toBe('Athlete sign in')
    expect(getCoachToken()).toBeNull()
  })
})

describe('staying signed in (30 days)', () => {
  beforeEach(() => {
    setCoachToken(token(-10))   // the short token has run out
    setSignedInRole('athlete')
    setRefreshToken('renewal-token')
  })

  it('renews a run-out sign-in with the renewal token', async () => {
    const fresh = token(3600)
    answers['/api/auth/refresh/'] = [200, { access: fresh, refresh: 'renewal-token-2' }]
    expect(await freshAthleteToken()).toBe(fresh)
    expect(calls.at(-1).body).toEqual({ refresh: 'renewal-token' })
    expect(getRefreshToken()).toBe('renewal-token-2')
  })

  it('a refused renewal (30 days up, or a new link used) signs out', async () => {
    answers['/api/auth/refresh/'] = [401, {}]
    expect(await freshAthleteToken()).toBeNull()
    expect(getCoachToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
  })

  it('a coach’s stored sign-in is never treated as an athlete’s', async () => {
    setSignedInRole('coach')
    expect(await freshAthleteToken()).toBeNull()
    expect(calls).toEqual([])
  })
})

describe('the coach sign-in page', () => {
  it('points athletes to their own sign-in on a remote school', async () => {
    await show(<SignIn onSignedIn={() => {}} />)
    await act(async () => { button('Athlete? Athlete sign in').click() })
    expect(navigate).toHaveBeenCalledWith('/athlete')
  })

  it('has no athlete link on a local install', async () => {
    deployment = 'local'
    await show(<SignIn onSignedIn={() => {}} />)
    expect(button('Athlete? Athlete sign in')).toBeUndefined()
  })
})
