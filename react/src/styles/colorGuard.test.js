// colorGuard.test.js — fails when a colour is typed into the app instead of using a token.
//
// Why this test exists: every colour lives in styles/tokens.css, so changing it there
// changes it everywhere (spec 06, Phase 0). Without a guard, someone types "#a9f04d"
// into a stylesheet once, then again, and the copies drift apart. This test reads every
// stylesheet and component and fails on any colour code outside the token file.
//
// It started with a list of leftovers (spec 06 Phase 0, Stop A) and runs with none since
// Stop B: a colour code anywhere outside tokens.css fails, full stop.
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { REACT_ROOT, appFiles, tokens, typedColours } from './colorScan.js'

describe('colours come only from tokens.css', () => {
  it('no colour code is typed anywhere outside tokens.css', () => {
    const typed = Object.entries(typedColours()).flatMap(([file, counts]) => Object.keys(counts).map((value) => `${file}: ${value}`))
    expect(typed, 'Use a token from src/styles/tokens.css instead (var(--name), or T.name in inline styles)').toEqual([])
  })

  it('every var(--name) the app uses is defined somewhere', () => {
    const defined = new Set(Object.keys(tokens()))
    const texts = appFiles().map((file) => [file, readFileSync(join(REACT_ROOT, file), 'utf8')])
    // A few stylesheets set their own local variables; those count as defined too.
    for (const [, text] of texts) for (const [, name] of text.matchAll(/--([a-z0-9-]+)\s*:/g)) defined.add(name)
    for (const [, text] of texts) for (const [, name] of text.matchAll(/['"]--([a-z0-9-]+)['"]\s*:/g)) defined.add(name)
    const missing = []
    for (const [file, text] of texts) {
      for (const [, name] of text.matchAll(/var\(--([a-z0-9-]+)/g)) if (!defined.has(name)) missing.push(`${file}: --${name}`)
    }
    // A missing variable silently falls back, or the colour vanishes.
    expect(missing).toEqual([])
  })

  it('every token has a value and the file explains every section', () => {
    const text = readFileSync(join(REACT_ROOT, 'src/styles/tokens.css'), 'utf8')
    const values = tokens()
    expect(Object.keys(values).length).toBeGreaterThan(15)
    for (const [name, value] of Object.entries(values)) expect(value, name).not.toBe('')
    // Each colour section opens with a comment saying what it's used on.
    for (const section of ['SURFACES', 'BANNER SURFACES', 'TEXT', 'LIME', 'MINT', 'AMBER', 'RED', 'EDGES AND SHAPES', 'TYPE']) {
      expect(text, section).toMatch(new RegExp(`\\* ${section}:`))
    }
  })
})
