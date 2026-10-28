// @vitest-environment jsdom
// Why these tests exist: a gym tablet is often switched on before practice, so the
// rack screen opens with no session running. When the coach then started one, the
// names appeared on the next poll but the session itself was never asked for again:
// the header kept saying "No active session" and Start Set sent no session, which the
// server refused (400) until someone reloaded the tablet. These pin that the session
// arrives with the names, and that a set started afterwards carries it.
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

const LIVE = { session_id: 9, label: 'Thursday — Lower + Push', roster: [{ athlete_id: 1, name: 'Riley Brooks' }] }

vi.mock('../api/client.js', () => ({
  getAthleteProgress: vi.fn(() => Promise.resolve({ movements: [{
    exercise_id: 1, name: 'Back Squat', planned_sets: 3, completed_sets: 0, next_set_number: 1,
    target_reps: 5, target_weight_lbs: 225, velocity_zone_min: 0.55, velocity_zone_max: 0.7,
  }] })),
  getActiveSession: vi.fn(() => Promise.resolve(LIVE)),
  getRackHotList: vi.fn(() => Promise.resolve({ athletes: [] })),
  getSessionStatus: vi.fn(() => Promise.resolve({ session_id: 9, athletes: [] })),
  checkInAthlete: vi.fn(), consumeNfcTap: vi.fn(), completeSet: vi.fn(),
  createSet: vi.fn(() => Promise.resolve({ id: 55 })),
}))
vi.mock('../mqtt/client.js', () => ({ subscribeNodeReps: vi.fn(() => () => {}) }))
vi.mock('./nfc.js', () => ({ pollLocalNfcTap: vi.fn(() => Promise.resolve(null)),
  handleNfcPollResult: vi.fn() }))
vi.mock('../db/repBuffer.js', () => ({ addRep: vi.fn(), clearBuffer: vi.fn(() => Promise.resolve()),
  getBufferedReps: vi.fn(() => Promise.resolve([])) }))

const { default: RackScreen } = await import('./RackScreen.jsx')
const { createSet } = await import('../api/client.js')

// What GET /api/sessions/active/ answers when nothing is running.
const NO_SESSION = { session_id: null, label: null, roster: [], session_exercises: [] }

function controllerAt(snapshot) {
  return {
    mode: 'controller', canControl: true, snapshot,
    runControlled: vi.fn(), updateState: vi.fn(() => Promise.resolve()),
    runMutation: vi.fn((send) => send('capability', snapshot.state_version)),
  }
}
const idle = { rack_number: 1, phase: 'idle', state_version: 3, owner_athlete: null,
  selected_athlete: null, selected_exercise: null, current_set: null, rep_count: 0 }

let container, root
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  vi.useRealTimers()
  vi.mocked(createSet).mockClear()
  container = document.createElement('div')
  document.body.appendChild(container)
  root = createRoot(container)
})
afterEach(() => {
  vi.useRealTimers()
  act(() => root.unmount())
  container.remove()
})

async function show(controller) {
  await act(async () => {
    root.render(<RackScreen rackNumber={1} session={NO_SESSION} node={{ id: 4 }} controller={controller} />)
  })
  await act(async () => {})
  await act(async () => {})
}

it('picks up a session started after the tablet opened', async () => {
  await show(controllerAt(idle))

  expect(container.textContent).toContain('Thursday — Lower + Push')
  expect(container.textContent).not.toContain('No active session')
  expect(container.textContent).toContain('Riley Brooks')
})

it('starts a set with that session, not none', async () => {
  await show(controllerAt(idle))
  vi.useFakeTimers()
  // The athlete checked in and pressed Start Set: the rack is counting down.
  await show(controllerAt({ ...idle, phase: 'countdown', state_version: 4,
    selected_athlete: { id: 1, name: 'Riley Brooks' }, selected_exercise: { id: 1 } }))
  // 3, 2, 1, GO: the first set start fires about 3.35 s in.
  for (let i = 0; i < 4; i += 1) await act(async () => { vi.advanceTimersByTime(1000) })

  expect(createSet).toHaveBeenCalled()
  expect(vi.mocked(createSet).mock.calls[0][0]).toMatchObject({ session: 9, athlete: 1, exercise: 1 })
})
