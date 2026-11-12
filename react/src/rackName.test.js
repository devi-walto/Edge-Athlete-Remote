// rackName.test.js — how a rack is printed (spec 18, Phase 2).
//
// Why this test exists: racks now have names, and two may share one, so the server says
// what to print. Every screen must go through rackLabel(); this guard fails if a screen
// prints "Rack 3" from a bare number again. The old setup screens that spec 18 Phases 4
// and 5 replace are listed by name, and leave this list when they go.
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { rackLabel } from './rackName.js'
import { REACT_ROOT, appFiles } from './styles/colorScan.js'

describe('rackLabel', () => {
  it('prints the label the server sends', () => {
    expect(rackLabel('Platform (4)', 4)).toBe('Platform (4)')
  })
  it('an older server with no label still reads Rack and the number', () => {
    expect(rackLabel(null, 3)).toBe('Rack 3')
    expect(rackLabel(undefined, undefined)).toBe('Rack')
  })
})

// Replaced by spec 18: today's Room Layout (Phase 4/5), the slot-waiting sensor step
// (Phase 5), the coach's quick note (prints a number it is handed, no rack object yet).
const OLD_SCREENS = ['src/coach/CoachTablet.jsx', 'src/rack/RackNodeSetup.jsx', 'src/coach/QuickNote.jsx']

it('no screen prints "Rack N" from a bare number', () => {
  const handPrinted = /Rack \{[^}]*(rack_number|rackNumber|\.rack\b)[^}]*\}|`Rack \$\{[^}]*(rack_number|rackNumber)[^}]*\}`/
  const offenders = appFiles()
    .filter((file) => !file.endsWith('.test.js') && !file.endsWith('.test.jsx') && file !== 'src/rackName.js')
    .filter((file) => !OLD_SCREENS.includes(file))
    .filter((file) => handPrinted.test(readFileSync(join(REACT_ROOT, file), 'utf8')))
  expect(offenders).toEqual([])
})
