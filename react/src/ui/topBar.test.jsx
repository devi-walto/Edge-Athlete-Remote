// @vitest-environment jsdom
// topBar.test.jsx — the top-left corner (spec 06, Phase 3, rule 12) and the back link.
//
// Why this test exists: the picture must always take a coach to Planning without ending
// a running day, the name must open the account menu (with Coaches only for an
// administrator), both must be real, finger-sized buttons a keyboard can reach, and a
// drill-down page's back link must go where it's told.
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { navigate } from '../router.js'
import AccountMenu from '../coach/AccountMenu.jsx'
import { pathForCoachState } from '../coach/coachState.js'
import BackLink from './BackLink.jsx'
import TopBar from './TopBar.jsx'

vi.mock('../router.js', () => ({ navigate: vi.fn() }))

globalThis.IS_REACT_ACT_ENVIRONMENT = true
let host, root
beforeEach(() => {
  host = document.createElement('div'); document.body.appendChild(host); root = createRoot(host)
  vi.mocked(navigate).mockClear()
  globalThis.fetch = vi.fn()
})
afterEach(() => { act(() => root.unmount()); host.remove() })
const render = (node) => act(() => root.render(node))
const home = () => host.querySelector('button[aria-label="Home"]')
const name = () => host.querySelector('button[aria-haspopup="menu"]')
const items = () => [...host.querySelectorAll('[role="menuitem"]')].map((b) => b.textContent)

const ADMIN = { username: 'dwalton', role: 'administrator' }
const COACH = { username: 'assistant', role: 'coach' }

describe("the coach's corner", () => {
  it('the picture goes to Planning, and asks the server nothing (a running day keeps running)', () => {
    render(<AccountMenu me={COACH} onLogout={vi.fn()} />)
    act(() => home().click())
    expect(navigate).toHaveBeenCalledWith(pathForCoachState('planning'))
    expect(pathForCoachState('planning')).toBe('/coach/planning')
    expect(fetch).not.toHaveBeenCalled()
  })

  it("the coach's name opens the menu: Coaches for an administrator", () => {
    render(<AccountMenu me={ADMIN} onLogout={vi.fn()} />)
    expect(name().textContent).toBe('dwalton▾')
    expect(host.querySelector('[role="menu"]')).toBeNull()
    act(() => name().click())
    expect(name().getAttribute('aria-expanded')).toBe('true')
    expect(host.querySelector('.acct-badge').textContent).toBe('Administrator')
    expect(items()).toEqual(['Coachesadministrators only', 'Change password', 'Log out'])
  })

  it('a coach who is not an administrator gets no Coaches item', () => {
    render(<AccountMenu me={COACH} onLogout={vi.fn()} />)
    act(() => name().click())
    expect(items()).toEqual(['Change password', 'Log out'])
    expect(host.querySelector('.acct-badge')).toBeNull()
  })

  it('Escape and a press elsewhere close the menu', () => {
    render(<AccountMenu me={COACH} onLogout={vi.fn()} />)
    act(() => name().click())
    act(() => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })))
    expect(host.querySelector('[role="menu"]')).toBeNull()
    act(() => name().click())
    act(() => document.body.dispatchEvent(new Event('pointerdown', { bubbles: true })))
    expect(host.querySelector('[role="menu"]')).toBeNull()
  })

  it('the menu items do their jobs', () => {
    const onLogout = vi.fn()
    render(<AccountMenu me={ADMIN} onLogout={onLogout} />)
    act(() => name().click())
    act(() => [...host.querySelectorAll('[role="menuitem"]')][1].click())
    expect(navigate).toHaveBeenCalledWith('/coach/account/password')
    act(() => name().click())
    act(() => [...host.querySelectorAll('[role="menuitem"]')][2].click())
    expect(onLogout).toHaveBeenCalledOnce()
  })

  it('both parts are real buttons a keyboard reaches, each with its own name', () => {
    render(<AccountMenu me={COACH} onLogout={vi.fn()} />)
    for (const button of [home(), name()]) {
      expect(button.tagName).toBe('BUTTON')
      expect(button.tabIndex).toBe(0)
    }
    expect(home().getAttribute('aria-label')).toBe('Home')
    expect(name().getAttribute('aria-label')).toBe('Account menu: assistant')
  })
})

describe('the shared top bar', () => {
  it('works the same for an athlete: picture to their Home, name to their menu', () => {
    const goHome = vi.fn(); const signOut = vi.fn()
    render(<TopBar name="Chris Vale" onHome={goHome} menuItems={[
      { label: 'Account', onSelect: vi.fn() }, { label: 'Sign out', onSelect: signOut }]} />)
    act(() => home().click())
    expect(goHome).toHaveBeenCalledOnce()
    act(() => name().click())
    expect(items()).toEqual(['Account', 'Sign out'])
  })

  it('with nobody signed in, the square says EA and nothing can be pressed', () => {
    render(<TopBar />)
    expect(host.querySelector('.ui-topbar-square').textContent).toBe('EA')
    expect(host.querySelector('button')).toBeNull()
  })
})

describe('BackLink', () => {
  it('shows where it goes back to, and goes there', () => {
    const onBack = vi.fn()
    render(<BackLink label="All sessions" onBack={onBack} />)
    expect(host.querySelector('button.ui-backlink').textContent).toBe('‹ All sessions')
    act(() => host.querySelector('button').click())
    expect(onBack).toHaveBeenCalledOnce()
  })
})
