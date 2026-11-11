// @vitest-environment jsdom
// contextTabs.test.jsx — a row of tabs appears only when there are two or more tabs.
//
// Why this test exists: spec 06 rule 7. SESSION has a single tab (Room), and a tab row
// with one tab in it is a button that does nothing. PLANNING and ANALYTICS keep theirs.
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import ContextTabs, { STATE_TABS } from './ContextTabs.jsx'

globalThis.IS_REACT_ACT_ENVIRONMENT = true
let host, root
beforeEach(() => { host = document.createElement('div'); document.body.appendChild(host); root = createRoot(host) })
afterEach(() => { act(() => root.unmount()); host.remove() })
const render = (state) => act(() => root.render(
  <ContextTabs tabs={STATE_TABS[state]} active={STATE_TABS[state][0]} onChoose={() => {}} />))

it('SESSION shows no tab row', () => {
  render('session')
  expect(host.querySelector('[role="tablist"]')).toBeNull()
})

it.each(['planning', 'analytics'])('%s shows its tab row, with the first tab open', (state) => {
  render(state)
  const tabs = [...host.querySelectorAll('[role="tab"]')]
  expect(tabs).toHaveLength(STATE_TABS[state].length)
  expect(tabs[0].getAttribute('aria-selected')).toBe('true')
})

it('a tab press asks for that tab', () => {
  const onChoose = vi.fn()
  act(() => root.render(<ContextTabs tabs={STATE_TABS.planning} active="design" onChoose={onChoose} />))
  act(() => host.querySelectorAll('[role="tab"]')[3].click())
  expect(onChoose).toHaveBeenCalledWith('calendar')
})
