// @vitest-environment jsdom
// Why these tests exist: the rack's two timers (the 3-2-1 countdown and the rest
// timer) each do one thing when they run out: start the set, or send the rack back to
// idle. Both used to do it again on every redraw of the screen while the server was
// still answering. A second set start was refused by the server and left the
// athlete's finished set showing a scary "The rack changed underneath this screen";
// the extra "back to idle" messages were just noise. These pin that each timer acts
// once, however many redraws happen before the server answers.
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

const riley = { rack_number: 1, state_version: 4, owner_athlete: null,
  selected_athlete: { id: 1, name: 'Riley Brooks' }, selected_exercise: { id: 1 },
  current_set: null, rep_count: 0 }

// The rack as the server last described it. updateState never answers, like a slow server.
function controllerAt(phase) {
  const snapshot = { ...riley, phase }
  return {
    mode: 'controller', canControl: true, snapshot,
    runControlled: vi.fn(), updateState: vi.fn(() => new Promise(() => {})),
    runMutation: vi.fn((send) => send('capability', snapshot.state_version)),
  }
}

let container, root
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  vi.useFakeTimers()
  vi.mocked(createSet).mockClear()
  container = document.createElement('div')
  document.body.appendChild(container)
  root = createRoot(container)
})
afterEach(() => {
  act(() => root.unmount())
  container.remove()
  vi.useRealTimers()
})

// A redraw from above, the way the screen redraws on its own polls.
async function redraw(controller) {
  await act(async () => {
    root.render(<RackScreen rackNumber={1} session={LIVE} node={{ id: 4 }} controller={controller} />)
  })
}
const tick = (ms) => act(async () => { vi.advanceTimersByTime(ms) })

it('starts one set at GO while the server is still answering', async () => {
  const controller = controllerAt('countdown')
  await redraw(controller)
  // 3, 2, 1, GO, and the start goes out.
  for (let i = 0; i < 4; i += 1) await tick(1000)
  expect(createSet).toHaveBeenCalledTimes(1)

  // No reply yet, so the rack is still on GO. Five more seconds of redraws.
  for (let i = 0; i < 5; i += 1) {
    await redraw(controller)
    await tick(1000)
  }

  expect(createSet).toHaveBeenCalledTimes(1)
})

it('sends the rack back to idle once when rest runs out', async () => {
  const controller = controllerAt('rest')
  await redraw(controller)
  // The two-minute rest runs out.
  for (let i = 0; i < 121; i += 1) await tick(1000)
  const backToIdle = () => controller.updateState.mock.calls
    .filter(([change]) => change?.phase === 'idle').length
  expect(backToIdle()).toBe(1)

  // No reply yet, so the rack is still resting at 0:00. Keep redrawing.
  for (let i = 0; i < 5; i += 1) {
    await redraw(controller)
    await tick(1000)
  }

  expect(backToIdle()).toBe(1)
})
