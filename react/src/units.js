// units.js — pounds or kilograms: one remembered choice on this phone or tablet.
//
// Why this file exists: loads are stored in pounds everywhere (weight_lbs), but a person
// may think in kilograms. Every screen that shows a load asks this file how to write it,
// so the choice made in one place (My Recent Progress' LB | KG, later the rack screen's
// plate loader, spec 16) changes it everywhere on that device (spec 10; Devin,
// 2026-11-11). Pounds by default. Speeds are always m/s and never come through here.
import { useSyncExternalStore } from 'react'

export const UNIT_KEY = 'ea_load_unit'
export const UNITS = ['lb', 'kg']
const CHANGED = 'ea-unit-change'
// Without storage (a private window, a blocked site) the choice still works until the page
// closes: kept here too.
let current = null

export function getUnit() {
  try {
    const saved = localStorage.getItem(UNIT_KEY)
    if (saved) return saved === 'kg' ? 'kg' : 'lb'
  } catch { /* no storage: use the page's own copy */ }
  return current || 'lb'
}

export function setUnit(unit) {
  current = unit === 'kg' ? 'kg' : 'lb'
  try { localStorage.setItem(UNIT_KEY, current) } catch { /* this page only */ }
  window.dispatchEvent(new Event(CHANGED))
}

/** Pounds to kilograms, to the nearest half kilogram. */
export function toKg(lbs) {
  return Math.round(lbs * 0.45359237 * 2) / 2
}

/** "225 lb" or "102 kg" (or "102.5 kg"); null when there's no load. */
export function formatLoad(lbs, unit = getUnit()) {
  if (lbs == null) return null
  return unit === 'kg' ? `${toKg(lbs)} kg` : `${Math.round(lbs * 10) / 10} lb`
}

function subscribe(onChange) {
  window.addEventListener(CHANGED, onChange)
  window.addEventListener('storage', onChange)            // another tab changed it
  return () => { window.removeEventListener(CHANGED, onChange); window.removeEventListener('storage', onChange) }
}

/** The current unit, redrawing the component when it changes anywhere. */
export function useUnit() {
  return useSyncExternalStore(subscribe, getUnit, () => 'lb')
}
