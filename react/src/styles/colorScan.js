// colorScan.js — finds colour codes typed into the app's code, for the colour guard tests.
//
// Why this file exists: every colour is meant to live in styles/tokens.css and nowhere
// else (spec 06, Phase 0). The guard tests use these helpers to look through every
// stylesheet and component for a colour written out by hand (#a9f04d, rgba(...)), and to
// read the token file itself. Only the tests use it; the app never imports it.
import { readFileSync, readdirSync } from 'node:fs'
import { dirname, join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

// The react/ folder, worked out from where this file sits (react/src/styles/). Done with
// plain path steps: the browser-like test setup (jsdom) replaces the URL class, which
// Node's file helpers then refuse.
export const REACT_ROOT = join(dirname(fileURLToPath(import.meta.url)), '../../')
export const TOKENS_FILE = 'src/styles/tokens.css'

// A colour code: #rgb, #rgba, #rrggbb, #rrggbbaa, or rgb()/rgba()/hsl()/hsla().
const COLOUR = /#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3,4}\b|\b(?:rgba?|hsla?)\([^)]*\)/g

/** Every stylesheet and component in src/, as paths relative to react/. Tests, the token
 *  file and this scanner are left out. */
export function appFiles(dir = join(REACT_ROOT, 'src')) {
  const found = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name)
    if (entry.isDirectory()) found.push(...appFiles(path))
    else if (/\.(css|jsx?)$/.test(entry.name) && !/\.test\./.test(entry.name)) found.push(relative(REACT_ROOT, path))
  }
  return found.filter((file) => file !== TOKENS_FILE && file !== 'src/styles/colorScan.js').sort()
}

/** The colour codes typed in one piece of text, counted: { '#0b1114': 3, 'rgba(0,0,0,.5)': 1 }. */
export function coloursIn(text) {
  const counts = {}
  for (const match of text.match(COLOUR) || []) {
    const value = match.replace(/\s+/g, '').toLowerCase()
    counts[value] = (counts[value] || 0) + 1
  }
  return counts
}

/** Every colour code typed anywhere in the app: { 'src/athlete/athlete.css': { '#123456': 1 } }. */
export function typedColours() {
  const all = {}
  for (const file of appFiles()) {
    const counts = coloursIn(readFileSync(join(REACT_ROOT, file), 'utf8'))
    if (Object.keys(counts).length) all[file] = counts
  }
  return all
}

/** The tokens, from tokens.css: { lime: '#a9f04d', 'radius-button': '6px', ... }. */
export function tokens() {
  const text = readFileSync(join(REACT_ROOT, TOKENS_FILE), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '')
  const found = {}
  for (const [, name, value] of text.matchAll(/--([a-z0-9-]+)\s*:\s*([^;]+);/g)) found[name] = value.trim().toLowerCase()
  return found
}
