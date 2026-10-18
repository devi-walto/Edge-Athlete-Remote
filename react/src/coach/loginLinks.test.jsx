// @vitest-environment jsdom
// Tests for login links on the roster (spec 03, Phase 3): the Login column and its
// buttons appear only on a remote school, and the link is shown once, in the
// dialog, and gone from the page when the dialog closes.
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

let deployment = 'remote'
vi.mock('../useDeployment.js', () => ({ default: () => deployment }))
vi.mock('../AthleteWorkoutPlanning.jsx', () => ({ default: () => null }))

const { default: GroupsView } = await import('./GroupsView.jsx')
const { cancelLoginLink, loginStatus, sendLoginLink, unlinkLogin } = await import('./loginLinks.js')

const LINK = 'https://demo.example.com/login-link#abc123lookup.s3cretSECRETs3cret'
const ATHLETES = [
  { id: 1, name: 'Riley Brooks', login_status: 'none', login_username: null, link_expires_at: null },
  { id: 2, name: 'Jordan Lee', login_status: 'linked', login_username: 'jordan', link_expires_at: null },
  { id: 3, name: 'Casey Morgan', login_status: 'link_sent', login_username: null,
    link_expires_at: '2026-10-21T18:10:00Z' },
]

function reply(status, body) {
  return Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) })
}

let container, root, posted
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  posted = []
  globalThis.fetch = vi.fn((url, options = {}) => {
    if (options.method === 'POST' && url.endsWith('/login-link/')) {
      posted.push(url)
      return reply(201, { link: LINK, expires_at: '2026-10-21T18:10:00Z' })
    }
    if (url === '/api/training-groups/') return reply(200, [])
    if (url === '/api/athletes/') return reply(200, ATHLETES)
    return reply(404, {})
  })
  container = document.createElement('div')
  document.body.appendChild(container)
  root = createRoot(container)
})
afterEach(() => {
  act(() => root.unmount())
  container.remove()
  deployment = 'remote'
})

async function renderRoster() {
  await act(async () => { root.render(<GroupsView accessToken="t" onLogout={() => {}} />) })
  await act(async () => {})
}

const buttonNamed = (text) => [...container.querySelectorAll('button')].find((b) => b.textContent === text)

describe('the roster on a remote school', () => {
  it('shows each athlete’s login and the right button', async () => {
    await renderRoster()
    const headers = [...container.querySelectorAll('th')].map((th) => th.textContent)
    expect(headers).toContain('Login')
    expect(container.textContent).toContain('Linked')
    expect(container.textContent).toContain('jordan')
    expect(container.textContent).toContain('Link sent')
    expect(container.textContent).toContain('No login yet')
    expect(buttonNamed('Send login link')).toBeTruthy()   // Riley, who has nothing
    expect(buttonNamed('Unlink')).toBeTruthy()            // Jordan, who is linked
    expect(container.textContent).toContain('1 with a login')
  })

  it('shows the link once, and drops it when the dialog closes', async () => {
    await renderRoster()
    await act(async () => { buttonNamed('Send login link').click() })
    await act(async () => {})

    expect(posted).toEqual(['/api/athletes/1/login-link/'])
    const dialog = container.querySelector('[role="dialog"]')
    expect(dialog.textContent).toContain('For Riley Brooks')
    expect(dialog.textContent).toContain("Don't post this in a group chat")
    expect(dialog.querySelector('input').value).toBe(LINK)

    await act(async () => { buttonNamed('Done').click() })
    expect(container.querySelector('[role="dialog"]')).toBeNull()
    expect(container.innerHTML).not.toContain('s3cretSECRETs3cret')
  })
})

describe('the roster on a local install', () => {
  it('has no login column and no login buttons', async () => {
    deployment = 'local'
    await renderRoster()
    const headers = [...container.querySelectorAll('th')].map((th) => th.textContent)
    expect(headers).not.toContain('Login')
    expect(buttonNamed('Send login link')).toBeUndefined()
    expect(buttonNamed('Unlink')).toBeUndefined()
    expect(container.textContent).not.toContain('with a login')
  })
})

describe('the calls behind the buttons', () => {
  const athlete = { id: 7, name: 'Riley Brooks' }

  it('sending gives the link and its expiry', async () => {
    const fetchImpl = vi.fn(() => reply(201, { link: LINK, expires_at: 'x' }))
    expect(await sendLoginLink(athlete, 't', { fetchImpl }))
      .toEqual({ status: 'sent', link: LINK, expiresAt: 'x' })
    expect(fetchImpl.mock.calls[0][1].method).toBe('POST')
  })

  it('a refusal comes back as a message', async () => {
    const fetchImpl = () => reply(409, { detail: 'This athlete is archived. Bring them back first.' })
    expect(await sendLoginLink(athlete, 't', { fetchImpl }))
      .toEqual({ status: 'refused', message: 'This athlete is archived. Bring them back first.' })
  })

  it('cancelling and unlinking use DELETE; unlinking asks first', async () => {
    const fetchImpl = vi.fn(() => reply(204, {}))
    expect(await cancelLoginLink(athlete, 't', { fetchImpl })).toEqual({ status: 'cancelled' })
    expect(await unlinkLogin(athlete, 't', { fetchImpl, confirm: () => false }))
      .toEqual({ status: 'cancelled' })
    expect(fetchImpl).toHaveBeenCalledTimes(1)   // a "no" sends nothing
    expect(await unlinkLogin(athlete, 't', { fetchImpl, confirm: () => true }))
      .toEqual({ status: 'unlinked' })
    expect(fetchImpl.mock.calls[1][0]).toBe('/api/athletes/7/login/')
  })

  it('a signed-out coach is told so', async () => {
    expect((await sendLoginLink(athlete, 't', { fetchImpl: () => reply(401, {}) })).status)
      .toBe('signed-out')
  })
})

describe('the Login column’s words', () => {
  it.each([
    [{ login_status: 'linked', login_username: 'riley' }, 'Linked', 'riley'],
    [{ login_status: 'none' }, 'No login yet', 'cannot join'],
    [{ login_status: undefined }, 'No login yet', 'cannot join'],
  ])('%o', (athlete, label, detail) => {
    expect(loginStatus(athlete)).toMatchObject({ label, detail })
  })

  it('a waiting link shows its expiry day', () => {
    const status = loginStatus({ login_status: 'link_sent', link_expires_at: '2026-10-21T18:10:00Z' })
    expect(status.label).toBe('Link sent')
    expect(status.detail).toMatch(/^expires Oct 2\d$/)
  })
})
