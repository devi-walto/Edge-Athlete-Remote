// @vitest-environment jsdom
//
// Why these tests exist: the connection test is the one screen that publishes to the
// live-update broker, so a remote installation must not serve it. It asks the server
// which kind of installation it is on before it connects to anything.
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

const connect = vi.fn(() => ({ on: vi.fn(), subscribe: vi.fn(), end: vi.fn(), publish: vi.fn() }))
vi.mock('mqtt', () => ({ default: { connect }, connect }))

const { default: ConnectionTest } = await import('./ConnectionTest.jsx')

let container, root
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  connect.mockClear()
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
})
afterEach(async () => {
  await act(async () => root.unmount())
  container.remove()
  vi.restoreAllMocks()
})

function serverSays(info, ok = true) {
  globalThis.fetch = vi.fn(async (url) => (String(url).includes('/api/system/info/')
    ? { ok, json: async () => info }
    : { ok: true, json: async () => ({}), text: async () => '{}' }))
}

it('shows a notice on a remote installation and never connects to the broker', async () => {
  serverSays({ deployment: 'remote', version: 'dev' })
  await act(async () => root.render(<ConnectionTest />))
  expect(container.textContent).toContain('Not available here')
  expect(connect).not.toHaveBeenCalled()
})

it('shows the page on a local installation', async () => {
  serverSays({ deployment: 'local', version: 'dev' })
  await act(async () => root.render(<ConnectionTest />))
  expect(container.textContent).not.toContain('Not available here')
  expect(container.textContent.length).toBeGreaterThan(50)
})

it('behaves as local when the server cannot say', async () => {
  serverSays({}, false)
  await act(async () => root.render(<ConnectionTest />))
  expect(container.textContent).not.toContain('Not available here')
})
