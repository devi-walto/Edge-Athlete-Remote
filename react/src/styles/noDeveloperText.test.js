// noDeveloperText.test.js — fails when developer text shows up where a coach reads.
//
// Why this test exists: spec 06 rule 3, no developer text in the interface. Server
// addresses ("PATCH /api/racks/…"), "server-local" and the like crept onto screens
// before, because they're natural to type while building. This reads every screen's
// source, ignoring comments and the addresses the code itself calls, and fails if a
// server address or "server-local" is in words a person would see.
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { expect, it } from 'vitest'
import { REACT_ROOT, appFiles } from './colorScan.js'

// Comments out: /* … */ (including JSX's {/* … */}) and // to the end of a line, but not
// the // inside an address like https://.
const withoutComments = (text) => text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:\w"'`])\/\/.*$/gm, '$1')

export function developerText(source) {
  const text = withoutComments(source)
  const found = []
  // Words after a tag (JSX text). Apostrophes are allowed (they're in sentences); the
  // marks of code (quotes, backticks, ; ( ) =) and an arrow's => aren't, so code isn't
  // mistaken for it.
  for (const [, words] of text.matchAll(/(?<![=\->])>([^<>{}"`;()=]+)[<{]/g)) {
    if (/\/api\/|server-local/i.test(words)) found.push(words.trim())
  }
  // Strings. An address the code calls starts with /api/ (or a ${base} before it), and a
  // file the code imports starts with ./ or ../; anything else holding /api/ is a
  // sentence about the server.
  for (const match of text.matchAll(/(['"`])((?:\\.|(?!\1)[^\\\n])*)\1/g)) {
    const value = match[2]
    if (/server-local/i.test(value)) found.push(value)
    else if (/\/api\//.test(value) && !/^(\$\{[^}]+\})?\/api\//.test(value) && !/^(https?:|\.{1,2}\/)/.test(value)) found.push(value)
  }
  return found
}

it('finds the kinds of developer text it is meant to catch', () => {
  expect(developerText(`<p>Screens: <code>{'PATCH /api/racks/{device_id}/'}</code></p>`)).toHaveLength(1)
  expect(developerText(`<p>one athlete's server-local training days.</p>`)).toHaveLength(1)
  expect(developerText(`coachFetch('/api/racks/', { token }) // calls /api/racks/`)).toEqual([])
  expect(developerText("fetch(`${base}/api/nodes/`)")).toEqual([])
  expect(developerText("import { getRackState } from '../api/client.js'")).toEqual([])
})

it('no screen shows a server address or "server-local"', () => {
  const found = appFiles().filter((file) => file.endsWith('.jsx'))
    .flatMap((file) => developerText(readFileSync(join(REACT_ROOT, file), 'utf8')).map((words) => `${file}: ${words}`))
  expect(found).toEqual([])
})
