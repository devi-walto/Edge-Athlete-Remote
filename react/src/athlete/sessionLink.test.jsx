// @vitest-environment jsdom
// Tests for spec 04, Phase 3: the session link, and the gym's rack screen on a rack an
// online athlete owns. The server calls and the live connection are replaced by
// stand-ins; what is checked is what each screen shows and asks for.
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// Same in-memory store as the other tests, for Node versions without a working one.
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

vi.mock('../api/client.js', () => ({
  getAthleteProgress: vi.fn(() => Promise.resolve({ movements: [{
    exercise_id: 1, name: 'Back Squat', planned_sets: 3, completed_sets: 0, next_set_number: 1,
    target_reps: 5, target_weight_lbs: 225, velocity_zone_min: 0.55, velocity_zone_max: 0.7,
  }] })),
  getActiveSession: vi.fn(() => Promise.resolve({ id: 7, label: 'Thursday', roster: [
    { athlete_id: 1, name: 'Riley Brooks' }, { athlete_id: 2, name: 'Jordan Lee' }] })),
  getRackHotList: vi.fn(() => Promise.resolve({ athletes: [] })),
  getSessionStatus: vi.fn(() => Promise.resolve({ session_id: 7, athletes: [] })),
  checkInAthlete: vi.fn(), consumeNfcTap: vi.fn(), createSet: vi.fn(), completeSet: vi.fn(),
  signInHeaders: vi.fn(() => Promise.resolve({ Authorization: 'Bearer t' })),
}))
vi.mock('../mqtt/client.js', () => ({ subscribeNodeReps: vi.fn(() => () => {}) }))
vi.mock('../rack/nfc.js', () => ({ pollLocalNfcTap: vi.fn(() => Promise.resolve(null)),
  handleNfcPollResult: vi.fn() }))
vi.mock('../db/repBuffer.js', () => ({ addRep: vi.fn(), clearBuffer: vi.fn(),
  getBufferedReps: vi.fn(() => Promise.resolve([])) }))
vi.mock('../router.js', () => ({ navigate: vi.fn(), usePathname: () => '/' }))
let joined = { mode: 'controller' }
vi.mock('../rack/controller.js', async (original) => ({
  ...(await original()),
  useRackController: () => joined,
}))
vi.mock('./athleteAuth.js', async (original) => ({
  ...(await original()),
  freshAthleteToken: vi.fn(() => Promise.resolve('token')),
}))

const { default: RackScreen } = await import('../rack/RackScreen.jsx')
const { default: SessionPage } = await import('./SessionPage.jsx')
const { pollLocalNfcTap } = await import('../rack/nfc.js')
const { navigate } = await import('../router.js')
const { freshAthleteToken, RETURN_KEY } = await import('./athleteAuth.js')

let container, root
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  vi.useRealTimers()
  vi.mocked(navigate).mockReset()
  vi.mocked(pollLocalNfcTap).mockClear()
  sessionStorage.clear()
  container = document.createElement('div')
  document.body.appendChild(container)
  root = createRoot(container)
})
afterEach(() => {
  act(() => root.unmount())
  container.remove()
})

async function show(element) {
  await act(async () => { root.render(element) })
  await act(async () => {})
  await act(async () => {})
}

function controllerFor(snapshot) {
  return {
    mode: 'controller', canControl: true, snapshot,
    runControlled: vi.fn(), runMutation: vi.fn(), updateState: vi.fn(() => Promise.resolve()),
  }
}

const RILEY = { id: 1, name: 'Riley Brooks' }

describe('the rack screen on a rack an online athlete owns', () => {
  const snapshot = { rack_number: 10000, phase: 'idle', state_version: 3, owner_athlete: RILEY,
    selected_athlete: RILEY, selected_exercise: null, current_set: null, rep_count: 0 }

  it('is named after them, with no lifter to choose and no wristband reader', async () => {
    await show(<RackScreen rackNumber={10000} session={{ label: 'Thursday', roster: [] }}
      node={{ id: 4, node_id: 'sim-riley-brooks', acquisition_kind: 'mqtt' }}
      controller={controllerFor(snapshot)} />)
    expect(container.textContent).toContain('Riley Brooks')
    expect(container.textContent).not.toContain('Rack 10000')
    expect(container.textContent).not.toContain('Not here?')
    expect(container.textContent).not.toContain('Rack check-in')
    expect(container.textContent).not.toContain('Jordan Lee')          // no list of names
    expect(pollLocalNfcTap).not.toHaveBeenCalled()
    for (const word of ['phase', 'node', 'buffered']) expect(container.textContent).toContain(word)
  })
})

describe('the same rack screen on a gym rack', () => {
  it('is unchanged: rack number, check-in list', async () => {
    const gym = { rack_number: 1, phase: 'idle', state_version: 1, owner_athlete: null,
      selected_athlete: null, selected_exercise: null, current_set: null, rep_count: 0 }
    await show(<RackScreen rackNumber={1} session={{ label: 'Thursday', roster: [] }}
      node={{ id: 2, node_id: 'rack-1', acquisition_kind: 'mqtt' }} controller={controllerFor(gym)} />)
    expect(container.textContent).toContain('Rack 1')
    expect(container.textContent).toContain('Rack check-in')
  })
})

describe('opening the session link', () => {
  function answer(status, body) {
    globalThis.fetch = vi.fn((url) => Promise.resolve({
      status: url.endsWith('/join/') ? status : 200,
      json: () => Promise.resolve(url.endsWith('/join/') ? body : { athlete_name: 'Riley Brooks' }),
    }))
  }

  it('joined: their own rack, through the gym rack screen', async () => {
    answer(200, { rack_number: 10003, sensor: { id: 4, node_id: 'sim-riley-brooks' } })
    joined = controllerFor({ rack_number: 10003, phase: 'idle', owner_athlete: RILEY,
      selected_athlete: RILEY, state_version: 1, current_set: null, rep_count: 0 })
    await show(<SessionPage sessionId={7} />)
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/sessions/7/join/', expect.objectContaining({
      method: 'POST', headers: expect.objectContaining({ Authorization: 'Bearer t' }) }))
    expect(container.textContent).toContain('Riley Brooks')
    expect(container.textContent).not.toContain('Rack check-in')
  })

  it('not started: waits on the page and checks again by itself', async () => {
    vi.useFakeTimers()
    answer(409, { code: 'not_started', session: { id: 7, label: 'Thursday — Lower' } })
    await show(<SessionPage sessionId={7} />)
    expect(container.textContent).toContain("Your coach hasn't started this session yet")
    expect(container.textContent).toContain('Thursday — Lower')
    const joinsBefore = vi.mocked(globalThis.fetch).mock.calls.filter(([u]) => u.endsWith('/join/')).length
    await act(async () => { vi.advanceTimersByTime(5000) })
    await act(async () => {})
    const joinsAfter = vi.mocked(globalThis.fetch).mock.calls.filter(([u]) => u.endsWith('/join/')).length
    expect(joinsAfter).toBe(joinsBefore + 1)
  })

  it('not on this session: says so, and Back', async () => {
    answer(403, { code: 'not_in_session' })
    await show(<SessionPage sessionId={7} />)
    expect(container.textContent).toContain("You're not on this session")
    expect([...container.querySelectorAll('button')].some((b) => b.textContent === 'Back')).toBe(true)
  })

  it('ended: says everything is saved, and offers sign out', async () => {
    answer(409, { code: 'ended', session: { id: 7, label: 'Thursday' } })
    await show(<SessionPage sessionId={7} />)
    expect(container.textContent).toContain('Your coach ended the session. Everything is saved.')
    expect(container.textContent).toContain('Sign out')
  })

  it('signed out: off to sign in, then back to this session', async () => {
    vi.mocked(freshAthleteToken).mockResolvedValueOnce(null)
    answer(200, {})
    await show(<SessionPage sessionId={7} />)
    expect(sessionStorage.getItem(RETURN_KEY)).toBe('/session/7')
    expect(navigate).toHaveBeenCalledWith('/athlete', { replace: true })
  })
})
