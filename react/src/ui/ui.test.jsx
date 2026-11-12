// @vitest-environment jsdom
// ui.test.jsx — checks the shared pieces in react/src/ui/ (spec 06, Phase 1).
//
// Why this test exists: these pieces are what every later screen is built from, so each
// look (every Button kind, every Badge) must render the way the Final designs draw it,
// a wrong kind must be refused, everything pressable must be finger-sized, and every
// text colour must be readable on the background it sits on.
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import BarChart, { TONES } from './BarChart.jsx'
import Load from './Load.jsx'
import PillGroup from './PillGroup.jsx'
import RangePicker from './RangePicker.jsx'
import Tiles from './Tiles.jsx'
import TrendLine from './TrendLine.jsx'
import UnitToggle from './UnitToggle.jsx'
import { formatLoad, toKg } from '../units.js'
import Badge, { BADGE_KINDS } from './Badge.jsx'
import Button, { BUTTON_KINDS } from './Button.jsx'
import FocusCard from './FocusCard.jsx'
import Hero from './Hero.jsx'
import QuietRow from './QuietRow.jsx'
import RiskTag from './RiskTag.jsx'
import SectionLabel from './SectionLabel.jsx'
import Step, { StepLink } from './Step.jsx'
import { REACT_ROOT, appFiles, tokens } from '../styles/colorScan.js'

globalThis.IS_REACT_ACT_ENVIRONMENT = true
let host, root
beforeEach(() => { host = document.createElement('div'); document.body.appendChild(host); root = createRoot(host) })
afterEach(() => { act(() => root.unmount()); host.remove() })
const render = (node) => act(() => root.render(node))

describe('Button', () => {
  it.each(BUTTON_KINDS)('draws the %s kind', (kind) => {
    render(<Button kind={kind}>Go</Button>)
    const button = host.querySelector('button')
    expect(button.className).toBe(`ui-button ui-button--${kind}`)
    expect(button.type).toBe('button')
    expect(button.textContent).toContain('Go')
  })

  it('has all eight kinds from rule 2', () => {
    expect(BUTTON_KINDS).toEqual(['primary', 'next', 'solid', 'key', 'end', 'danger', 'quiet', 'quiet-lime'])
  })

  it('ends a "next" button with an arrow, and shows an icon before the words', () => {
    render(<Button kind="next" icon={<svg data-icon />}>Schedule</Button>)
    expect(host.textContent).toBe('Schedule→')
    expect(host.querySelector('.ui-button-icon [data-icon]')).not.toBeNull()
  })

  it('refuses an unknown or missing kind while the app is being built', () => {
    const quiet = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<Button kind="outline">Go</Button>)).toThrow(/unknown kind "outline"/)
    expect(() => render(<Button>Go</Button>)).toThrow(/unknown kind/)
    quiet.mockRestore()
  })

  it('passes clicks and other button settings through', () => {
    const onClick = vi.fn()
    render(<Button kind="end" onClick={onClick} disabled={false} aria-label="End training day">End</Button>)
    act(() => host.querySelector('button').click())
    expect(onClick).toHaveBeenCalledOnce()
    expect(host.querySelector('button').getAttribute('aria-label')).toBe('End training day')
  })
})

describe('Badge', () => {
  it.each(BADGE_KINDS)('draws the %s kind with its default words', (kind) => {
    render(<Badge kind={kind} />)
    const badge = host.querySelector('.ui-badge')
    expect(badge.className).toBe(`ui-badge ui-badge--${kind}`)
    expect(badge.textContent.length).toBeGreaterThan(0)
  })

  it('uses a warning mark, not a dot, for a sensor that stopped answering', () => {
    render(<Badge kind="sensor-off" />)
    expect(host.querySelector('svg')).not.toBeNull()
    expect(host.querySelector('.ui-badge-dot')).toBeNull()
    expect(host.textContent).toBe('Sensor not responding')
  })

  it('takes other words, and refuses an unknown kind', () => {
    render(<Badge kind="scheduled">Scheduled · week 3</Badge>)
    expect(host.textContent).toBe('Scheduled · week 3')
    const quiet = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<Badge kind="online" />)).toThrow(/unknown kind "online"/)
    quiet.mockRestore()
  })
})

describe('RiskTag', () => {
  it('says Behind with its count', () => {
    render(<RiskTag detail="4/5" />)
    expect(host.querySelector('.ui-risk').textContent).toBe('Behind 4/5')
  })

  it('has a compact triangle that still says Behind to a screen reader', () => {
    render(<RiskTag compact detail="4/5" />)
    const mark = host.querySelector('svg.ui-risk-mark')
    expect(mark.getAttribute('role')).toBe('img')
    expect(mark.getAttribute('aria-label')).toBe('Behind 4/5')
    expect(host.textContent).toBe('')
  })
})

describe('FocusCard, QuietRow, SectionLabel, Hero', () => {
  it('draws a focus card with its label, title and actions', () => {
    render(<FocusCard label="Step 2" title="Create a Training Program"><Button kind="primary">Create</Button></FocusCard>)
    expect(host.querySelector('section.ui-focus .ui-focus-label').textContent).toBe('Step 2')
    expect(host.querySelector('h2.ui-focus-title').textContent).toBe('Create a Training Program')
    expect(host.querySelector('.ui-focus-actions button')).not.toBeNull()
  })

  it('shows a detail line under the title, and a mark before the name of a row', () => {
    render(<><FocusCard title="Day 2" detail="Varsity · Deadlift" /><QuietRow lead={<i data-dot />} name="ea-3f9c" /></>)
    expect(host.querySelector('.ui-focus-detail').textContent).toBe('Varsity · Deadlift')
    expect(host.querySelector('.ui-row-lead [data-dot]')).not.toBeNull()
  })

  it('leaves out the parts a focus card or row is not given', () => {
    render(<><FocusCard title="Roster" /><QuietRow name="Jordan" /></>)
    expect(host.querySelector('.ui-focus-label, .ui-focus-detail, .ui-focus-actions, .ui-row-lead, .ui-row-meta, .ui-row-badge, .ui-row-actions')).toBeNull()
  })

  it('draws a row with its name, detail, badge and actions', () => {
    render(<QuietRow name="Jordan Lee" meta="Varsity" badge={<RiskTag detail="2/3" />}
      actions={<Button kind="quiet">Archive</Button>} />)
    expect(host.querySelector('.ui-row-name').textContent).toBe('Jordan Lee')
    expect(host.querySelector('.ui-row-meta').textContent).toBe('Varsity')
    expect(host.querySelector('.ui-row-badge .ui-risk')).not.toBeNull()
    expect(host.querySelector('.ui-row-actions .ui-button--quiet')).not.toBeNull()
  })

  it('draws a section label, as a heading by default', () => {
    render(<SectionLabel>Other Training Blocks</SectionLabel>)
    expect(host.querySelector('h3.ui-section-label').textContent).toBe('Other Training Blocks')
  })

  it('draws the header card with the same markup the tabs use today', () => {
    render(<Hero eyebrow="Build and deploy" title="Design" aside="4 blocks">Design a block.</Hero>)
    const card = host.querySelector('header.workout-catalog-heading')
    expect(card.querySelector('div > span').textContent).toBe('Build and deploy')
    expect(card.querySelector('div > h2').textContent).toBe('Design')
    expect(card.querySelector('div > p').textContent).toBe('Design a block.')
    expect(card.querySelector(':scope > b').textContent).toBe('4 blocks')
  })
})

describe('Step', () => {
  it('draws the open step with its rail and contents, marked as the current step', () => {
    render(<Step number={2} title="Create a Training Program" active summary="hidden when open"><p>form</p></Step>)
    expect(host.querySelector('.ui-step').className).toBe('ui-step is-active')
    expect(host.querySelector('[aria-current="step"]')).not.toBeNull()
    expect(host.querySelector('.ui-step-body p').textContent).toBe('form')
    expect(host.querySelector('.ui-step-summary')).toBeNull()
  })

  it('shrinks a step the coach is not in to one row, a button when it can open', () => {
    const onOpen = vi.fn()
    render(<Step number={1} title="Build a Training Block" summary="4 blocks" onOpen={onOpen}><p>form</p></Step>)
    expect(host.querySelector('.ui-step-body')).toBeNull()
    expect(host.querySelector('.ui-step-summary').textContent).toBe('4 blocks')
    act(() => host.querySelector('button.ui-step-row').click())
    expect(onOpen).toHaveBeenCalledOnce()
  })

  it('draws a step without a way to open as a plain row', () => {
    render(<Step number={3} title="Schedule" />)
    expect(host.querySelector('button')).toBeNull()
  })

  it('draws a step that goes to another page with an arrow', () => {
    const onClick = vi.fn()
    render(<StepLink number={3} title="Open Calendar" onClick={onClick} />)
    expect(host.querySelector('.ui-step-arrow')).not.toBeNull()
    act(() => host.querySelector('button').click())
    expect(onClick).toHaveBeenCalledOnce()
  })
})

describe('BarChart', () => {
  const bars = [
    { value: 0.8, above: '0.80', inside: '225 lb', below: 'Nov 4', tone: 'green', label: 'Nov 4: 0.80 m/s' },
    { value: 0.4, above: '0.40', inside: '235 lb', below: 'Nov 7', tone: 'yellow', faded: true },
    { value: 0.01, above: '0.01', below: 'Nov 9', tone: 'red' },
  ]
  const fills = () => [...host.querySelectorAll('.ui-bar-fill')]

  it('draws one bar per item, tallest = the top, a slow one still visible', () => {
    render(<BarChart bars={bars} label="Speed" />)
    expect(host.querySelector('[role="list"]').getAttribute('aria-label')).toBe('Speed')
    expect(fills().map((f) => f.style.height)).toEqual(['100%', '50%', '12%'])
    expect(fills().map((f) => f.dataset.tone)).toEqual(['green', 'yellow', 'red'])
    expect(fills()[1].classList.contains('is-faded')).toBe(true)
  })

  it('shows the number above, the text inside and the label below, only when given', () => {
    render(<BarChart bars={bars} />)
    expect([...host.querySelectorAll('.ui-bar-above')].map((e) => e.textContent)).toEqual(['0.80', '0.40', '0.01'])
    expect([...host.querySelectorAll('.ui-bar-inside')].map((e) => e.textContent)).toEqual(['225 lb', '235 lb'])
    expect([...host.querySelectorAll('.ui-bar-below')].map((e) => e.textContent)).toEqual(['Nov 4', 'Nov 7', 'Nov 9'])
    expect(host.querySelectorAll('[role="listitem"]')[0].getAttribute('aria-label')).toBe('Nov 4: 0.80 m/s')
  })

  it('legend lines go on top', () => {
    render(<BarChart bars={bars} legend={['Each bar = 1 week', 'Speed above · load inside · when, below']} />)
    expect([...host.querySelectorAll('.ui-bars-legend span')].map((e) => e.textContent))
      .toEqual(['Each bar = 1 week', 'Speed above · load inside · when, below'])
  })

  it('a spark has no words at all, whatever it is given', () => {
    render(<BarChart size="spark" bars={bars} legend={['x']} />)
    expect(host.querySelector('.ui-bars--spark')).not.toBeNull()
    expect(host.querySelectorAll('.ui-bar-above, .ui-bar-inside, .ui-bar-below, .ui-bars-legend')).toHaveLength(0)
    expect(fills()).toHaveLength(3)
  })

  it('a fixed top: the coach chart never reads less than 1 m/s as full height', () => {
    render(<BarChart size="large" max={1} bars={[{ value: 0.5 }, { value: 0.25 }]} />)
    expect(fills().map((f) => f.style.height)).toEqual(['50%', '25%'])
    expect(host.querySelector('.ui-bars-row').classList.contains('is-scroll')).toBe(true)   // large scrolls
  })

  it('normal fits the width; scrolling can be asked for', () => {
    render(<BarChart bars={bars} />)
    expect(host.querySelector('.ui-bars-row').classList.contains('is-scroll')).toBe(false)
    render(<BarChart bars={bars} scroll />)
    expect(host.querySelector('.ui-bars-row').classList.contains('is-scroll')).toBe(true)
  })

  it('every tone has a colour in ui.css, and an unknown size is refused', () => {
    const css = readFileSync(join(REACT_ROOT, 'src/ui/ui.css'), 'utf8')
    for (const tone of TONES) expect(css).toContain(`.ui-bar-fill.is-${tone}`)
    const quiet = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<BarChart size="huge" bars={bars} />)).toThrow(/unknown size/)
    quiet.mockRestore()
  })

  it('no hand-drawn bar charts are left anywhere in the app', () => {
    // A bar chart drawn by hand sets each bar's height from a number: style={{ height: `${...}%` }}.
    const offenders = appFiles().filter((file) => !file.startsWith('src/ui/'))
      .filter((file) => /height:\s*`\$\{[^`]*%`/.test(readFileSync(join(REACT_ROOT, file), 'utf8')))
    expect(offenders).toEqual([])
  })
})

describe('PillGroup, RangePicker, TrendLine, Tiles, units', () => {
  it('PillGroup: one lime pill, pressing another reports it', () => {
    const chosen = vi.fn()
    render(<PillGroup label="Scope" value="a" onChange={chosen} choices={[{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }]} />)
    const pills = [...host.querySelectorAll('.ui-pills button')]
    expect(pills.map((p) => p.getAttribute('aria-pressed'))).toEqual(['true', 'false'])
    act(() => pills[1].click())
    expect(chosen).toHaveBeenCalledWith('b')
  })

  it('RangePicker: a preset reports both dates; dates the wrong way round are swapped', () => {
    const changed = vi.fn()
    render(<RangePicker value={{ from: '2026-11-01', to: '2026-11-10' }} onChange={changed} />)
    expect(host.querySelectorAll('.ui-pills button.is-on')).toHaveLength(0)
    act(() => host.querySelectorAll('.ui-pills button')[0].click())
    expect(changed.mock.calls[0][0].to).toBe(changed.mock.calls[0][0].to)
    const [from] = host.querySelectorAll('input[type="date"]')
    const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
    act(() => { set.call(from, '2026-11-20'); from.dispatchEvent(new Event('input', { bubbles: true })) })
    expect(changed).toHaveBeenLastCalledWith({ from: '2026-11-10', to: '2026-11-20' })
  })

  it('TrendLine: a line through the numbers, nulls skipped, one number a dot, none nothing', () => {
    render(<TrendLine values={[0.5, null, 0.7]} label="t" />)
    expect(host.querySelector('polyline').getAttribute('points').split(' ')).toHaveLength(2)
    render(<TrendLine values={[0.5]} label="t" />)
    expect(host.querySelector('circle')).not.toBeNull()
    render(<TrendLine values={[null]} label="t" />)
    expect(host.querySelector('svg')).toBeNull()
  })

  it('Tiles: label over number, "/ planned" quieter, amber when short', () => {
    render(<Tiles items={[{ label: 'Sets', value: 7, of: 9, short: true }, { label: 'Avg m/s', value: 'not measured', quiet: true }]} />)
    expect([...host.querySelectorAll('.ui-tiles b')].map((b) => b.textContent)).toEqual(['7 / 9', 'not measured'])
    expect(host.querySelector('b.is-short')).not.toBeNull()
    expect(host.querySelector('b.is-quiet')).not.toBeNull()
  })

  it('units: kilograms to the nearest half; every Load follows the toggle (even with no storage)', () => {
    expect(toKg(225)).toBe(102)
    expect(toKg(235)).toBe(106.5)
    expect(formatLoad(null)).toBeNull()
    render(<><UnitToggle /><span id="a"><Load lbs={225} /></span><span id="b"><Load lbs={null} /></span></>)
    expect(host.querySelector('#a').textContent).toBe('225 lb')
    expect(host.querySelector('#b').textContent).toBe('--')
    act(() => [...host.querySelectorAll('.ui-pills button')].find((b) => b.textContent === 'KG').click())
    expect(host.querySelector('#a').textContent).toBe('102 kg')
    act(() => [...host.querySelectorAll('.ui-pills button')].find((b) => b.textContent === 'LB').click())
    expect(host.querySelector('#a').textContent).toBe('225 lb')
  })
})

describe('the look in ui.css', () => {
  const css = readFileSync(join(REACT_ROOT, 'src/ui/ui.css'), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '')
  const rule = (selector) => {
    const found = [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].find(([, sel]) => sel.split(',').map((s) => s.trim()).includes(selector))
    return found ? found[2] : ''
  }
  const px = (body, prop) => Number((body.match(new RegExp(`(?:^|;|\\s)${prop}:\\s*(\\d+)px`)) || [])[1] || 0)

  it('makes every button, step row, top bar part and back link at least 44px tall', () => {
    expect(px(rule('.ui-button'), 'min-height')).toBeGreaterThanOrEqual(44)
    expect(px(rule('.ui-button--danger'), 'min-height')).toBeGreaterThanOrEqual(44)
    expect(px(rule('.ui-step-row'), 'min-height')).toBeGreaterThanOrEqual(44)
    expect(px(rule('.ui-topbar-home'), 'height')).toBeGreaterThanOrEqual(44)
    expect(px(rule('.ui-topbar-home'), 'width')).toBeGreaterThanOrEqual(44)
    expect(px(rule('.ui-topbar-name'), 'min-height')).toBeGreaterThanOrEqual(44)
    expect(px(rule('.ui-backlink'), 'min-height')).toBeGreaterThanOrEqual(44)
    // Row actions are quiet Buttons, so they inherit the 44px; nothing shrinks a button.
    expect(css).not.toMatch(/\.ui-button[^{]*\{[^}]*(?:^|;|\s)(?:min-)?height:\s*(?:[0-3]?\d|4[0-3])px/)
  })

  it('gives the Danger button the 19px words rule 5 needs', () => {
    expect(px(rule('.ui-button--danger'), 'font-size')).toBe(19)
  })
})

describe('every text colour is readable on what it sits on', () => {
  const t = tokens()
  const luminance = (hex) => {
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
      .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b
  }
  const contrast = (a, b) => { const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x); return (hi + 0.05) / (lo + 0.05) }

  // [text, background, where]: the pairs the pieces use. Normal text needs 4.5:1.
  const pairs = [
    ['muted', 'focus-bg', 'the focus card label'], ['ink', 'focus-bg', 'the focus card title'],
    ['faint', 'bg', 'a section label on the page'], ['faint', 'panel', 'a section label in a card'],
    ['faint', 'panel2', 'a section label in a lighter card'], ['faint', 'focus-bg', 'a section label on the focus card'],
    ['soft-ink', 'panel', 'a row name'], ['muted', 'panel', 'a row detail, a quiet button'],
    ['muted', 'risk-bg', 'grey text on the risk background'], ['coral-text', 'risk-bg', 'an error message'],
    ['coral-text', 'panel', 'an End button label, a Behind tag'], ['ink', 'panel2', 'a solid button label'],
    ['on-lime', 'lime', 'a primary button label'], ['lime', 'panel', 'a quiet lime button'],
    ['amber', 'warn-bg', 'a sensor that stopped answering'], ['ink', 'bg', 'a Not scheduled badge'],
  ]
  it.each(pairs)('%s on %s (%s) is at least 4.5:1', (text, background) => {
    expect(contrast(t[text], t[background])).toBeGreaterThanOrEqual(4.5)
  })

  it('the Danger button meets the large-text bar (3:1, its words are 19px bold)', () => {
    expect(contrast(t.ink, t['danger-fill'])).toBeGreaterThanOrEqual(3)
  })
})
