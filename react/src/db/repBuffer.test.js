// Tests for spotting a rep that arrives twice (spec 14, Phase 4).
//
// Why these exist: sensors send each rep "at least once" (MQTT QoS 1), so a rep can
// now and then arrive twice, and the rack screen used to count every one it got. A
// repeat must count once; two real reps, even with the same number, must both count.
import { describe, expect, it, vi } from 'vitest'

vi.mock('dexie', () => ({ default: class { version() { return { stores() {} } } } }))
const { isRepeat } = await import('./repBuffer.js')

const rep = (n, at, node = 'ea-3f9c') => ({ node_id: node, rep_number: n, timestamp: at })

describe('a repeated rep', () => {
  it('the same rep arriving twice is a repeat', () => {
    expect(isRepeat(rep(3, '12:00:03'), [rep(1, '12:00:01'), rep(2, '12:00:02'), rep(3, '12:00:03')])).toBe(true)
  })

  it('two different reps are both counted', () => {
    expect(isRepeat(rep(4, '12:00:04'), [rep(3, '12:00:03')])).toBe(false)
  })

  it('the same number at another moment is another rep', () => {
    // A sensor restarts its numbering, or a set restarts: a new rep, not a repeat.
    expect(isRepeat(rep(1, '12:05:00'), [rep(1, '12:00:01')])).toBe(false)
  })

  it("another sensor's rep with the same number and time is not a repeat", () => {
    expect(isRepeat(rep(1, '12:00:01', 'ea-other'), [rep(1, '12:00:01')])).toBe(false)
  })

  it('a new set starts counting again (the buffer is empty)', () => {
    expect(isRepeat(rep(1, '12:00:01'), [])).toBe(false)
  })
})
