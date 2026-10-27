// @vitest-environment jsdom
// Why this test exists: when the countdown reached GO and the server was slow to
// answer (a remote server, a busy network), every redraw of the rack screen in the
// meantime queued another set start. A BLE rack redraws every second, so a reply
// slower than about a second sent two: the server refused the second, and the
// athlete's finished set then showed a scary "The rack changed underneath this
// screen". This pins that GO sends one start, however many redraws happen first.
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
  // A server that has not answered yet.
  createSet: vi.fn(() => new Promise(() => {})),
}))
vi.mock('../mqtt/client.js', () => ({ subscribeNodeReps: vi.fn(() => () => {}) }))
vi.mock('./nfc.js', () => ({ pollLocalNfcTap: vi.fn(() => Promise.resolve(null)),
  handleNfcPollResult: vi.fn() }))
vi.mock('../db/repBuffer.js', () => ({ addRep: vi.fn(), clearBuffer: vi.fn(() => Promise.resolve()),
  getBufferedReps: vi.fn(() => Promise.resolve([])) }))

const { default: RackScreen } = await import('./RackScreen.jsx')
const { createSet } = await import('../api/client.js')

const counting = { rack_number: 1, phase: 'countdown', state_version: 4, owner_athlete: null,
  selected_athlete: { id: 1, name: 'Riley Brooks' }, selected_exercise: { id: 1 },
  current_set: null, rep_count: 0 }
const controller = {
  mode: 'controller', canControl: true, snapshot: counting,
  runControlled: vi.fn(), updateState: vi.fn(() => Promise.resolve()),
  runMutation: vi.fn((send) => send('capability', counting.state_version)),
}

let container, root
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  vi.useFakeTimers()
  container = document.createElement('div')
  document.body.appendChild(container)
  root = createRoot(container)
})
afterEach(() => {
  act(() => root.unmount())
  container.remove()
  vi.useRealTimers()
})

// A redraw from above, like the sensor-health check that lands every second.
async function redraw() {
  await act(async () => {
    root.render(<RackScreen rackNumber={1} session={LIVE} node={{ id: 4 }} controller={controller} />)
  })
}

it('starts one set at GO while the server is still answering', async () => {
  await redraw()
  // 3, 2, 1, GO, and the start goes out.
  for (let i = 0; i < 4; i += 1) await act(async () => { vi.advanceTimersByTime(1000) })
  expect(createSet).toHaveBeenCalledTimes(1)

  // No reply yet, so the rack is still on GO. Five more seconds of redraws.
  for (let i = 0; i < 5; i += 1) {
    await redraw()
    await act(async () => { vi.advanceTimersByTime(1000) })
  }

  expect(createSet).toHaveBeenCalledTimes(1)
})
