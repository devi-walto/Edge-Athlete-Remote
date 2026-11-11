// colorGuard.test.js — fails when a colour is typed into the app instead of using a token.
//
// Why this test exists: every colour lives in styles/tokens.css, so changing it there
// changes it everywhere (spec 06, Phase 0). Without a guard, someone types "#a9f04d"
// into a stylesheet once, then again, and the copies drift apart. This test reads every
// stylesheet and component and fails on any colour code outside the token file.
//
// colorLeftovers.json lists the codes not moved to tokens yet (spec 06 Phase 0, Stop B
// maps them). The list may only shrink: a new code fails, and so does a list entry that
// is no longer in the code, so the list always says exactly what is left.
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { REACT_ROOT, appFiles, tokens, typedColours } from './colorScan.js'
import leftovers from './colorLeftovers.json'

describe('colours come only from tokens.css', () => {
  it('no colour code is typed outside tokens.css, apart from the listed leftovers', () => {
    const typed = typedColours()
    const extra = []
    for (const [file, counts] of Object.entries(typed)) {
      for (const [value, count] of Object.entries(counts)) {
        const allowed = leftovers.app[file]?.[value] || 0
        if (count > allowed) extra.push(`${file}: ${value} (${count - allowed} new)`)
      }
    }
    expect(extra, 'Use a token from src/styles/tokens.css instead (var(--name), or T.name in inline styles)').toEqual([])
  })

  it('the leftovers list only lists codes that are still there', () => {
    const typed = typedColours()
    const stale = []
    for (const [file, counts] of Object.entries(leftovers.app)) {
      for (const [value, allowed] of Object.entries(counts)) {
        const count = typed[file]?.[value] || 0
        if (count < allowed) stale.push(`${file}: ${value} (list says ${allowed}, code has ${count})`)
      }
    }
    expect(stale, 'Shrink src/styles/colorLeftovers.json to match').toEqual([])
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
    // A missing variable silently falls back (or vanishes). The list holds the ones found
    // on 2026-11-11, mapped in Stop B; it may only shrink.
    expect(missing).toEqual(leftovers.undefinedVariables)
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
