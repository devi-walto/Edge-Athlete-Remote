// @vitest-environment jsdom
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import AccountMenu from './AccountMenu.jsx'
import ChangePassword from './ChangePassword.jsx'
import Coaches from './Coaches.jsx'
import FirstRun from './FirstRun.jsx'
import FirstRunGate from './FirstRunGate.jsx'
import SignIn from './SignIn.jsx'
import { archiveAthlete } from './archiveAthlete.js'
import {
  changePassword, coachFetch, coachLogin, createCoach, listCoaches,
  resetCoachPassword, setCoachToken, updateCoach,
} from './api.js'

// These tests began as Braydon's, written for his coach-accounts screens. The screens
// were rebuilt to the Final designs (spec 01, Phase 2), so each test here is his test
// pointed at the screen that now does that job. One of his is not carried over:
// creating and editing an athlete in his separate roster page, because that page was
// not built (the workspace already has a roster). Archiving, the part that was new,
// is tested below.
vi.mock('./api.js', () => ({
  coachFetch: vi.fn(),
  coachLogin: vi.fn(),
  setCoachToken: vi.fn(),
  getCoachToken: vi.fn(),
  fetchCurrentCoach: vi.fn(),
  changePassword: vi.fn(),
  listCoaches: vi.fn(),
  createCoach: vi.fn(),
  updateCoach: vi.fn(),
  resetCoachPassword: vi.fn(),
}))
vi.mock('../router.js', () => ({ navigate: vi.fn() }))

// Node 25 and later ship their own `localStorage` global. Unless Node is started with a
// storage file it is undefined, and it hides the one jsdom provides, so these tests died
// in `beforeEach` on a newer Node while passing on an older one. Give them a plain
// in-memory store whenever a working one is missing, so the result does not depend on
// which Node runs them.
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

let container, root
beforeEach(() => {
  vi.resetAllMocks()
  localStorage.clear()
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
async function fill(input, value) {
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value)
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })
}
async function submit() {
  await act(async () => container.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })))
}
async function click(text) {
  const button = [...container.querySelectorAll('button')].find(b => b.textContent === text)
  expect(button, `button "${text}"`).toBeTruthy()
  await act(async () => button.click())
}

const ME = { username: 'head', is_staff: true, role: 'administrator', must_change_password: false }
const COACHES = [
  { id: 1, username: 'head', is_active: true, is_staff: true, must_change_password: false },
  { id: 2, username: 'assistant', is_active: true, is_staff: false, must_change_password: false },
]
const labels = () => [...container.querySelectorAll('button')].map(b => b.textContent)

// ---------- first-run setup ----------

it('requires matching passwords and the setup code before creating the first administrator', async () => {
  coachFetch.mockResolvedValueOnce({ access: 'setup-token' })
  const claimed = vi.fn()
  await render(<FirstRun codePending onRecheck={vi.fn()} onClaimed={claimed} onAlreadyClaimed={vi.fn()} />)
  const [code, username, password, again] = container.querySelectorAll('input')
  await fill(code, 'ABC234')
  await fill(username, 'firstcoach')
  await fill(password, 'unique-password')
  await fill(again, 'different')
  await submit()
  expect(container.querySelector('[role=alert]').textContent).toContain('do not match')
  expect(coachFetch).not.toHaveBeenCalled()
  await fill(again, 'unique-password')
  await submit()
  expect(coachFetch).toHaveBeenLastCalledWith('/api/auth/setup/', {
    method: 'POST',
    body: { username: 'firstcoach', password: 'unique-password', setup_code: 'ABC234' },
  })
  expect(setCoachToken).toHaveBeenCalledWith('setup-token')
  expect(claimed).toHaveBeenCalledWith('setup-token')
})

it('says how to get a setup code when none has been issued, and lets the operator check again', async () => {
  const recheck = vi.fn()
  await render(<FirstRun codePending={false} onRecheck={recheck} onClaimed={vi.fn()} onAlreadyClaimed={vi.fn()} />)
  expect(container.querySelector('[role=note]').textContent).toContain('manage.py setup_code')
  await click('I’ve run it — check again')
  expect(recheck).toHaveBeenCalledTimes(1)
  await render(<FirstRun codePending onRecheck={recheck} onClaimed={vi.fn()} onAlreadyClaimed={vi.fn()} />)
  expect(container.querySelector('[role=note]')).toBeNull()
})

it('steps aside when another browser finishes setup first', async () => {
  coachFetch.mockResolvedValueOnce({ setup_required: true, setup_code_pending: true })
    .mockRejectedValueOnce(Object.assign(new Error('Setup is complete.'), { status: 409 }))
  await render(<FirstRunGate><p>the app</p></FirstRunGate>)
  expect(container.textContent).toContain('Set up this installation')
  const [code, username, password, again] = container.querySelectorAll('input')
  await fill(code, 'ABC234'); await fill(username, 'late'); await fill(password, 'unique-password'); await fill(again, 'unique-password')
  await submit()
  expect(container.textContent).toBe('the app')
  expect(setCoachToken).not.toHaveBeenCalled()
})

it('does not show the app before it knows whether the installation is set up, and offers a retry', async () => {
  let answer
  coachFetch.mockReturnValueOnce(new Promise((resolve) => { answer = resolve }))
  await render(<FirstRunGate><p>the app</p></FirstRunGate>)
  expect(container.textContent).not.toContain('the app')
  expect(container.querySelector('[role=status]')).toBeTruthy()
  await act(async () => answer({ setup_required: false }))
  expect(container.textContent).toBe('the app')
})

it('offers a retry when the server cannot be reached on a device that has never seen it set up', async () => {
  coachFetch.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ setup_required: false })
  await render(<FirstRunGate><p>the app</p></FirstRunGate>)
  expect(container.querySelector('[role=alert]').textContent).toContain('could not be reached')
  expect(container.textContent).not.toContain('the app')
  await click('Retry connection')
  expect(container.textContent).toBe('the app')
})

it('lets a rack that has already seen a set-up installation reopen while the server is unreachable', async () => {
  localStorage.setItem('edge_setup_complete', 'true')
  coachFetch.mockRejectedValueOnce(new Error('offline'))
  await render(<FirstRunGate><p>the rack screen</p></FirstRunGate>)
  expect(container.textContent).toBe('the rack screen')
})

// ---------- sign in ----------

it('starts empty, shows a sign-in error, and accepts valid credentials', async () => {
  coachLogin.mockRejectedValueOnce(new Error('The username or password was not accepted.')).mockResolvedValueOnce('login-token')
  const signedIn = vi.fn()
  await render(<SignIn onSignedIn={signedIn} />)
  const [username, password] = container.querySelectorAll('input')
  expect(container.querySelectorAll('input')).toHaveLength(2)
  expect(username.value).toBe('')          // no "coach" / "coachpass" waiting in the form
  expect(password.value).toBe('')
  await fill(username, 'coach')
  await fill(password, 'password')
  await submit()
  expect(container.querySelector('[role=alert]').textContent).toContain('not accepted')
  expect(signedIn).not.toHaveBeenCalled()
  await fill(password, 'password')
  await submit()
  expect(coachLogin).toHaveBeenLastCalledWith('coach', 'password')
  expect(signedIn).toHaveBeenCalledWith('login-token')
})

// ---------- change password ----------

it('changes a temporary password and reports success', async () => {
  changePassword.mockResolvedValue(null)
  const changed = vi.fn()
  await render(<ChangePassword accessToken="token" forced onChanged={changed} onLogout={vi.fn()} />)
  expect(container.textContent).toContain('Temporary password')
  const [current, next, again] = container.querySelectorAll('input')
  await fill(current, 'temp-pass')
  await fill(next, 'my-own-password')
  await fill(again, 'not-the-same')
  await submit()
  expect(container.querySelector('[role=alert]').textContent).toContain('do not match')
  expect(changePassword).not.toHaveBeenCalled()
  await fill(again, 'my-own-password')
  await submit()
  expect(changePassword).toHaveBeenCalledWith('token', 'temp-pass', 'my-own-password')
  expect(changed).toHaveBeenCalledTimes(1)
})

it('shows why a password change was refused', async () => {
  changePassword.mockRejectedValue(new Error('That password is incorrect.'))
  const changed = vi.fn()
  await render(<ChangePassword accessToken="token" onChanged={changed} onCancel={vi.fn()} />)
  const [current, next, again] = container.querySelectorAll('input')
  await fill(current, 'wrong'); await fill(next, 'my-own-password'); await fill(again, 'my-own-password')
  await submit()
  expect(container.querySelector('[role=alert]').textContent).toContain('incorrect')
  expect(changed).not.toHaveBeenCalled()
})

// ---------- the Coaches page ----------

it('creates a coach and shows the temporary password exactly once', async () => {
  listCoaches.mockResolvedValue(COACHES)
  createCoach.mockResolvedValue({ username: 'newcoach', temporary_password: 'Temp-Pass-123!' })
  await render(<Coaches accessToken="token" me={ME} onLogout={vi.fn()} onChangePassword={vi.fn()} />)
  await click('Add coach')
  await fill(container.querySelector('form input'), 'newcoach')
  await submit()
  expect(createCoach).toHaveBeenCalledWith('token', 'newcoach')
  expect(container.querySelector('[role=status]').textContent).toContain('Temp-Pass-123!')
  expect(container.querySelector('[role=status]').textContent).toContain('cannot be shown again')
  await click('Done')
  expect(container.textContent).not.toContain('Temp-Pass-123!')
})

it('does not let an administrator deactivate, demote or reset themselves from the list', async () => {
  listCoaches.mockResolvedValue([COACHES[0]])
  const changeOwn = vi.fn()
  await render(<Coaches accessToken="token" me={ME} onLogout={vi.fn()} onChangePassword={changeOwn} />)
  expect(labels()).toEqual(['Add coach', 'Change password'])
  await click('Change password')
  expect(changeOwn).toHaveBeenCalledTimes(1)
})

it('deactivates another coach after asking, and reactivates them', async () => {
  listCoaches.mockResolvedValueOnce(COACHES)
    .mockResolvedValueOnce([COACHES[0], { ...COACHES[1], is_active: false }])
    .mockResolvedValue(COACHES)
  updateCoach.mockResolvedValue({})
  const confirm = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValue(true)
  await render(<Coaches accessToken="token" me={ME} onLogout={vi.fn()} onChangePassword={vi.fn()} />)
  await click('Deactivate')
  expect(updateCoach).not.toHaveBeenCalled()             // said no: nothing happens
  await click('Deactivate')
  expect(confirm.mock.calls[1][0]).toContain('Nothing they recorded is removed')
  expect(updateCoach).toHaveBeenLastCalledWith('token', 2, { is_active: false })
  expect(container.textContent).toContain('Deactivated')
  await click('Reactivate')
  expect(updateCoach).toHaveBeenLastCalledWith('token', 2, { is_active: true })
})

it('makes a coach an administrator and shows the Administrator badge', async () => {
  listCoaches.mockResolvedValueOnce(COACHES).mockResolvedValue([COACHES[0], { ...COACHES[1], is_staff: true }])
  updateCoach.mockResolvedValue({})
  await render(<Coaches accessToken="token" me={ME} onLogout={vi.fn()} onChangePassword={vi.fn()} />)
  expect(container.querySelectorAll('.acct-row .acct-badge')).toHaveLength(1)
  await click('Make administrator')
  expect(updateCoach).toHaveBeenCalledWith('token', 2, { is_staff: true })
  expect(container.querySelectorAll('.acct-row .acct-badge')).toHaveLength(2)
  expect(labels()).toContain('Remove administrator')
})

it('resets another coach password only after confirmation', async () => {
  listCoaches.mockResolvedValue(COACHES)
  resetCoachPassword.mockResolvedValue({ username: 'assistant', temporary_password: 'Fresh-Temp-9!' })
  vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValue(true)
  await render(<Coaches accessToken="token" me={ME} onLogout={vi.fn()} onChangePassword={vi.fn()} />)
  await click('Reset password')
  expect(resetCoachPassword).not.toHaveBeenCalled()
  await click('Reset password')
  expect(resetCoachPassword).toHaveBeenCalledWith('token', 2)
  expect(container.querySelector('[role=status]').textContent).toContain('Fresh-Temp-9!')
})

it('hands back to sign in when the server says this login may not manage coaches', async () => {
  listCoaches.mockRejectedValue(Object.assign(new Error('forbidden'), { status: 403 }))
  const logout = vi.fn()
  await render(<Coaches accessToken="token" me={ME} onLogout={logout} onChangePassword={vi.fn()} />)
  expect(logout).toHaveBeenCalledTimes(1)
})

it('never calls the administrator a head coach', async () => {
  listCoaches.mockResolvedValue(COACHES)
  await render(<Coaches accessToken="token" me={ME} onLogout={vi.fn()} onChangePassword={vi.fn()} />)
  expect(container.textContent.toLowerCase()).not.toContain('head coach')
  expect(container.textContent).toContain('Administrator')
})

// ---------- the account menu ----------

it('shows Coaches in the account menu to an administrator only', async () => {
  await render(<AccountMenu me={ME} onLogout={vi.fn()} />)
  await click('Edge Athlete')
  expect(container.textContent).toContain('head')
  expect(container.querySelector('.acct-badge').textContent).toBe('Administrator')
  expect(labels().some(l => l.startsWith('Coaches'))).toBe(true)

  await render(<AccountMenu me={{ username: 'assistant', is_staff: false, role: 'coach' }} onLogout={vi.fn()} />)
  expect(container.textContent).toContain('assistant')
  expect(container.querySelector('.acct-badge')).toBeNull()
  expect(labels().some(l => l.startsWith('Coaches'))).toBe(false)
  expect(labels()).toContain('Change password')
  expect(labels()).toContain('Log out')
})

// ---------- archiving an athlete ----------

const reply = (status, body) => ({ status, json: async () => body })

it('archives an athlete only after a question that says their history is kept', async () => {
  const fetchImpl = vi.fn().mockResolvedValue(reply(204))
  const confirm = vi.fn().mockReturnValueOnce(false).mockReturnValue(true)
  const athlete = { id: 7, name: 'Jordan Avery' }
  expect(await archiveAthlete(athlete, 'token', { confirm, fetchImpl })).toEqual({ status: 'cancelled' })
  expect(fetchImpl).not.toHaveBeenCalled()
  expect(await archiveAthlete(athlete, 'token', { confirm, fetchImpl })).toEqual({ status: 'archived' })
  expect(confirm.mock.calls[0][0]).toContain('Jordan Avery')
  expect(confirm.mock.calls[0][0]).toContain('is kept')
  expect(fetchImpl).toHaveBeenCalledWith('/api/athletes/7/', expect.objectContaining({ method: 'DELETE' }))
})

it('passes on the reason when the server refuses to archive during a session', async () => {
  const fetchImpl = vi.fn().mockResolvedValue(reply(409, { detail: 'End the active training session before removing this athlete.' }))
  const result = await archiveAthlete({ id: 7, name: 'Jordan Avery' }, 'token', { confirm: () => true, fetchImpl })
  expect(result).toEqual({ status: 'refused', message: 'End the active training session before removing this athlete.' })
})
