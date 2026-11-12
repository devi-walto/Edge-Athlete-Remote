// @vitest-environment jsdom
// account.test.jsx — the athlete's Account page (spec 10, Phase 5).
//
// Why this test exists: Account is read-only by design. Nothing on it may edit anything
// except through Manage (the sensor); the password help must open and close in place
// (there's no password change here, on purpose); and Sign out of this phone must sign out
// and leave nothing to go Back to.
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
const { default: Account } = await import('./Account.jsx')
const { setCoachToken, setSignedInRole, getCoachToken } = await import('../coach/api.js')

function token(seconds) {
  const body = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + seconds })).replace(/=+$/, '')
  return `h.${body}.s`
}
const ME = { name: 'Chris Vale', first_name: 'Chris', username: 'chris', groups: ['Varsity Football', 'Receivers'] }
const SENSOR = { node_id: 'ea-3f9c', last_seen: new Date().toISOString() }

let host, root, writes
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); sessionStorage.clear()
  setSignedInRole('athlete'); setCoachToken(token(3600))
  vi.mocked(navigate).mockReset()
  writes = []
  globalThis.fetch = vi.fn((url, options = {}) => {
    if (options.method && options.method !== 'GET') writes.push([options.method, url])
    const body = url === '/api/athlete/home/' ? { athlete: ME, live: null, coming_up: [], recent: [] }
      : url === '/api/athlete/sensors/' ? { sensors: [SENSOR] } : {}
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })
  })
  host = document.createElement('div'); document.body.appendChild(host); root = createRoot(host)
})
afterEach(() => { act(() => root.unmount()); host.remove() })

async function show() {
  await act(async () => { root.render(<Account />) })
  for (let i = 0; i < 3; i += 1) await act(async () => {})
}
const text = () => host.textContent
const button = (label) => [...host.querySelectorAll('button')].find((b) => b.textContent.trim().startsWith(label))

describe('Account', () => {
  it('shows name, username and teams, and says the coach manages them', async () => {
    await show()
    expect(host.querySelector('h1').textContent).toBe('Your account')
    expect(text()).toContain('Your coach manages your name and teams.')
    const rows = [...host.querySelectorAll('.athlete-account-rows .ui-row')].map((r) => r.textContent)
    expect(rows).toEqual(['Chris ValeName', 'chrisUsername', 'Varsity Football · ReceiversTeams'])
    expect(text()).toContain('ea-3f9c')
  })

  it('nothing on the page edits anything except through Manage', async () => {
    await show()
    expect(host.querySelectorAll('input, textarea, select, [contenteditable]')).toHaveLength(0)
    // Every button is one of: the top bar's two, the back link, Manage, the password help, sign out.
    const labels = [...host.querySelectorAll('main button')].map((b) => b.textContent.trim())
    expect(labels).toEqual(['', 'Chris Vale▾', '‹ Home', 'Manage', 'Changing your password? ▾', 'Sign out of this phone'])
    await act(async () => { button('Manage').click() })
    expect(navigate).toHaveBeenCalledWith('/athlete/sensors')
    await act(async () => { button('Changing your password?').click() })
    expect(writes).toEqual([])                                                   // nothing was sent anywhere
  })

  it('the password help opens and closes in place', async () => {
    await show()
    const help = button('Changing your password?')
    expect(help.getAttribute('aria-expanded')).toBe('false')
    expect(host.querySelector('#password-help')).toBeNull()
    await act(async () => { help.click() })
    expect(help.getAttribute('aria-expanded')).toBe('true')
    expect(host.querySelector('#password-help').textContent).toContain('Ask your coach in person for a new login link')
    expect(navigate).not.toHaveBeenCalled()                                      // in place, not a new page
    await act(async () => { help.click() })
    expect(host.querySelector('#password-help')).toBeNull()
  })

  it('Sign out of this phone signs out and leaves nothing to go Back to', async () => {
    await show()
    await act(async () => { button('Sign out of this phone').click() })
    expect(getCoachToken()).toBeFalsy()
    expect(navigate).toHaveBeenCalledWith('/athlete', { replace: true })
  })
})
