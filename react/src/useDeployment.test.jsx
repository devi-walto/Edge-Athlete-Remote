// @vitest-environment jsdom
//
// Why these tests exist: every local/remote difference on a screen hangs off this
// hook, so it must give the server's answer, fall back to local when the server
// cannot say, and ask the server once, not once per screen or per render.
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import useDeployment, { forgetDeploymentForTests, getDeployment } from './useDeployment.js'

let container, root
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  forgetDeploymentForTests()
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
})
afterEach(async () => {
  await act(async () => root.unmount())
  container.remove()
  vi.restoreAllMocks()
})

const serverSays = (body, ok = true) => {
  globalThis.fetch = vi.fn(async () => ({ ok, json: async () => body }))
}

function Show() {
  const mode = useDeployment()
  return <span>{mode === null ? 'asking' : mode}</span>
}

it('gives the mode the server reports', async () => {
  serverSays({ deployment: 'remote', version: 'dev' })
  await act(async () => root.render(<Show />))
  expect(container.textContent).toBe('remote')
})

it('falls back to local when the server cannot say', async () => {
  globalThis.fetch = vi.fn(async () => { throw new Error('offline') })
  await act(async () => root.render(<Show />))
  expect(container.textContent).toBe('local')
})

it('treats anything it does not recognise as local', async () => {
  serverSays({ deployment: 'cloud' })
  expect(await getDeployment()).toBe('local')
})

it('asks the server once, however many screens and renders ask', async () => {
  serverSays({ deployment: 'remote' })
  await act(async () => root.render(<><Show /><Show /><Show /></>))
  await act(async () => root.render(<><Show /><Show /><Show /><Show /></>))
  expect(container.textContent).toBe('remoteremoteremoteremote')
  expect(globalThis.fetch).toHaveBeenCalledTimes(1)
})
