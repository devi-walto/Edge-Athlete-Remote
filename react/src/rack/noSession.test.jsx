// @vitest-environment jsdom
// noSession.test.jsx — the rack with no session running (spec 19, Phase 0).
//
// Why this test exists: a tablet switched on before practice must say it's ready and
// waiting (board F_Rack_NoSession), not show an empty list and a "scan your band" prompt
// nobody can use yet; it must keep asking, so the check-in list replaces the message by
// itself when a coach starts the session; and its sensor chip must tell the truth: live
// only while the sensor is pulsing.
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const NO_SESSION = { session_id: null, label: null, roster: [], session_exercises: [] }
const LIVE = { session_id: 9, label: 'Thursday — Lower + Push', roster: [{ athlete_id: 1, name: 'Riley Brooks' }] }
let active = NO_SESSION
let pulse = null

vi.mock('../api/client.js', () => ({
  getAthleteProgress: vi.fn(() => Promise.resolve({ movements: [] })),
  getActiveSession: vi.fn(() => Promise.resolve(active)),
  getRackHotList: vi.fn(() => Promise.resolve({ athletes: [] })),
  getSessionStatus: vi.fn(() => Promise.resolve({ athletes: [] })),
  checkInAthlete: vi.fn(), consumeNfcTap: vi.fn(), completeSet: vi.fn(), createSet: vi.fn(),
}))
vi.mock('../mqtt/client.js', () => ({
  subscribeNodeReps: vi.fn(() => () => {}),
  subscribeNodePulse: vi.fn((id, onPulse) => { pulse = onPulse; return () => { pulse = null } }),
}))
vi.mock('./nfc.js', () => ({ pollLocalNfcTap: vi.fn(() => Promise.resolve({ status: 'none' })),
  handleNfcPollResult: vi.fn() }))
vi.mock('../db/repBuffer.js', () => ({ addRep: vi.fn(), clearBuffer: vi.fn(() => Promise.resolve()),
  getBufferedReps: vi.fn(() => Promise.resolve([])) }))

const { default: RackScreen } = await import('./RackScreen.jsx')
const { default: NoSession, useSensorLive } = await import('./NoSession.jsx')

// The chip as the rack screen wires it: the rack listens, the waiting screen shows.
function Chip({ node }) { return <NoSession rackNumber={3} node={node} live={useSensorLive(node)} /> }
const { pollLocalNfcTap } = await import('./nfc.js')

const idle = { rack_number: 3, phase: 'idle', state_version: 3, owner_athlete: null,
  selected_athlete: null, selected_exercise: null, current_set: null, rep_count: 0 }
const controller = { mode: 'controller', canControl: true, snapshot: idle,
  runControlled: vi.fn(), updateState: vi.fn(() => Promise.resolve()), runMutation: vi.fn() }
const NODE = { id: 4, node_id: 'rack_3', last_seen: new Date().toISOString() }

let host, root
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  active = NO_SESSION
  pulse = null
  vi.mocked(pollLocalNfcTap).mockClear()
  host = document.createElement('div'); document.body.appendChild(host); root = createRoot(host)
})
afterEach(() => { act(() => root.unmount()); host.remove(); vi.useRealTimers() })

async function show(page) {
  await act(async () => { root.render(page) })
  await act(async () => {}); await act(async () => {})
}
const text = () => host.textContent

describe('no session running', () => {
  it('says the rack is ready and waiting, with no list and no band prompt', async () => {
    await show(<RackScreen rackNumber={3} session={NO_SESSION} node={NODE} controller={controller} />)
    expect(text()).toContain('No session yet')
    expect(text()).toContain('Rack 3 is ready')
    expect(text()).toContain("Waiting fortoday's session")
    expect(text()).toContain('A coach starts it from the coach app. This screen updates on its own')
    expect(text()).not.toContain('Rack check-in')
    expect(text()).not.toContain('No athletes in this session')
    expect(text()).not.toContain('scan your NFC band')
    expect(pollLocalNfcTap).not.toHaveBeenCalled()       // nobody can check in yet
    expect(text()).toContain('phase: idle')               // the footer is unchanged
  })

  it('the check-in list replaces it by itself when a coach starts the session', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    await show(<RackScreen rackNumber={3} session={NO_SESSION} node={NODE} controller={controller} />)
    expect(text()).toContain('Waiting for')
    active = LIVE
    await act(async () => { await vi.advanceTimersByTimeAsync(5000) })
    expect(text()).not.toContain('Waiting for')
    expect(text()).toContain('Thursday — Lower + Push')
    expect(text()).toContain('Riley Brooks')
    expect(text()).toContain('scan your NFC band')
  })

  it('back to waiting after a session, a pulsing sensor still reads live', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    active = LIVE
    await show(<RackScreen rackNumber={3} session={LIVE} node={{ ...NODE, last_seen: '2026-11-01T10:00:00Z' }} controller={controller} />)
    await act(async () => { pulse() })                    // the sensor pulsed during the session
    active = NO_SESSION
    await act(async () => { await vi.advanceTimersByTimeAsync(5000) })
    expect(text()).toContain('Waiting for')
    expect(text()).toContain('Sensor rack_3 is live')
  })

  it('with a session from the start, the list shows as before', async () => {
    active = LIVE
    await show(<RackScreen rackNumber={3} session={LIVE} node={NODE} controller={controller} />)
    expect(text()).not.toContain('Waiting for')
    expect(text()).toContain('Rack check-in')
  })
})

describe('the sensor chip', () => {
  it('reads live while the sensor pulses, and not responding once it stops', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    await show(<Chip node={NODE} />)
    expect(text()).toContain('Sensor rack_3 is live')
    await act(async () => { await vi.advanceTimersByTimeAsync(16_000) })
    expect(text()).toContain('Sensor rack_3 not responding')
    await act(async () => { pulse() })
    expect(text()).toContain('Sensor rack_3 is live')
  })

  it('a sensor not seen lately starts as not responding', async () => {
    await show(<Chip node={{ ...NODE, last_seen: '2026-11-01T10:00:00Z' }} />)
    expect(text()).toContain('Sensor rack_3 not responding')
  })

  it('says so when no sensor is linked', async () => {
    await show(<Chip node={null} />)
    expect(text()).toContain('No sensor linked to this rack')
  })
})
