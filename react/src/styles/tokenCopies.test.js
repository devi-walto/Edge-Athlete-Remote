// tokenCopies.test.js — fails when a colour written outside the app stops matching tokens.css.
//
// Why this test exists: a few places can't use the token file, because they are not part
// of the app's code. The sensor's own setup page (the page a phone opens on the sensor's
// Wi-Fi) runs on the sensor, so it carries its own copy of the colours. The browser's theme
// colour (index.html) and the install manifests (public/) must write the colour out too.
// They should still look like the same product, so every colour they use must be one of
// the tokens, and this test checks it.
import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { REACT_ROOT, coloursIn, tokens } from './colorScan.js'
import leftovers from './colorLeftovers.json'

const SETUP_PAGE = join(REACT_ROOT, '../esp32/edge_athlete_node/src/setup_page.h')
// "#c8b" on the setup page is the id of an element (the code boxes), not a colour.
const NOT_COLOURS = new Set(['#c8b'])

describe('colours outside the app match tokens.css', () => {
  it("the sensor's setup page uses only token colours, apart from the listed leftovers", () => {
    const values = new Set(Object.values(tokens()))
    const counts = coloursIn(readFileSync(SETUP_PAGE, 'utf8'))
    const off = Object.keys(counts).filter((value) => !values.has(value) && !NOT_COLOURS.has(value))
    expect(off.sort()).toEqual(Object.keys(leftovers.sensorSetupPage).sort())
  })

  it("the browser's theme colour and every install manifest use the page background", () => {
    const bg = tokens().bg
    const html = readFileSync(join(REACT_ROOT, 'index.html'), 'utf8')
    expect(html.match(/name="theme-color" content="([^"]+)"/)[1].toLowerCase()).toBe(bg)
    const manifests = readdirSync(join(REACT_ROOT, 'public')).filter((name) => /^manifest.*\.json$/.test(name))
    expect(manifests.length).toBeGreaterThan(0)
    for (const name of manifests) {
      const manifest = JSON.parse(readFileSync(join(REACT_ROOT, 'public', name), 'utf8'))
      expect(manifest.theme_color.toLowerCase(), name).toBe(bg)
      expect(manifest.background_color.toLowerCase(), name).toBe(bg)
    }
  })
})
