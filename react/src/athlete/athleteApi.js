// athleteApi.js — reading the signed-in athlete's own data from the server.
//
// Why this file exists: every athlete page (Home, Account, Manage sensors) asks the
// server for the same few things with the athlete's sign-in attached. One helper keeps
// that in one place, and answers with a plain { status, body } so a page can tell
// "not signed in any more" (401) from "the server didn't answer" (status 0).
import { signInHeaders } from '../api/client.js'

export const HOME = '/api/athlete/home/'
export const SENSORS = '/api/athlete/sensors/'
export const SESSIONS = '/api/athlete/sessions/'

export async function getJson(url, { fetchImpl = fetch } = {}) {
  try {
    const response = await fetchImpl(url, { headers: { Accept: 'application/json', ...(await signInHeaders()) } })
    return { status: response.status, body: await response.json().catch(() => ({})) }
  } catch {
    return { status: 0, body: {} }
  }
}

/** "Wed, Nov 11" from "2026-11-11", read as a calendar day (no time, no time zone shift). */
export function dayLabel(isoDate) {
  const [y, m, d] = String(isoDate).split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
}

/** "November 2026" from "2026-11-11": the month heading on All sessions. */
export function monthLabel(isoDate) {
  const [y, m] = String(isoDate).split('-').map(Number)
  return new Date(y, m - 1, 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
}

/** "6:02 PM" from a full timestamp. */
export function timeLabel(isoDateTime) {
  return new Date(isoDateTime).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
}
