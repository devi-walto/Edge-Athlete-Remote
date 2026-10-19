// @vitest-environment jsdom
// Where "/" lands (spec 04, section 3f). Online, a person is a coach or an athlete,
// known from their login, so nobody lands on "Set up this device", even with a
// device role saved in the browser. A local install keeps the picker exactly as is.
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

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

let deployment = 'remote'
vi.mock('./useDeployment.js', () => ({ default: () => deployment, useInstallationName: () => null }))
vi.mock('./router.js', () => ({ navigate: vi.fn(), usePathname: () => '/' }))
vi.mock('./mqtt/client.js', () => ({ subscribeRackCommand: vi.fn(() => () => {}) }))
vi.mock('./WifiChangeOverlay.jsx', () => ({ default: () => null }))

const { default: App } = await import('./App.jsx')
const { navigate } = await import('./router.js')
const { setSignedInRole } = await import('./coach/api.js')

let container, root
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear()
  vi.mocked(navigate).mockReset()
  container = document.createElement('div')
  document.body.appendChild(container)
  root = createRoot(container)
})
afterEach(() => {
  act(() => root.unmount())
  container.remove()
  deployment = 'remote'
})

async function openHome() {
  await act(async () => { root.render(<App />) })
  await act(async () => {})
}

describe('online', () => {
  it('a signed-in athlete goes to their page', async () => {
    setSignedInRole('athlete')
    await openHome()
    expect(navigate).toHaveBeenCalledWith('/athlete', expect.anything())
  })

  it('anyone else goes to coach sign-in, never the picker', async () => {
    await openHome()
    expect(navigate).toHaveBeenCalledWith('/coach', expect.anything())
    expect(container.textContent).not.toContain('Set up this device')
  })

  it('a device role saved in the browser is ignored', async () => {
    localStorage.setItem('device_role', 'rack')
    localStorage.setItem('rack_number', '1')
    await openHome()
    expect(navigate).toHaveBeenCalledWith('/coach', expect.anything())
    expect(navigate).not.toHaveBeenCalledWith('/rack/1', expect.anything())
  })

  it('shows nothing, not the picker, before it knows which kind of install this is', async () => {
    deployment = null
    await openHome()
    expect(container.textContent).not.toContain('Set up this device')
    expect(navigate).not.toHaveBeenCalled()
  })
})

describe('a local install', () => {
  it('keeps the picker', async () => {
    deployment = 'local'
    await openHome()
    expect(container.textContent).toContain('Set up this device')
  })
})
