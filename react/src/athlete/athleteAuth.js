// athleteAuth.js — how an athlete gets signed in, and stays signed in.
//
// Why this file exists: on a remote school an athlete signs in on their own phone
// (spec 03). The first time, they use the login link their coach sent; after that,
// their username and password. They stay signed in for 30 days: the server gives
// an athlete a 30-day renewal token, and freshAthleteToken() quietly swaps it for a
// new short sign-in token whenever the old one has run out.
//
// Every function here answers with a plain { status, … } so the pages can say
// exactly what happened, the same way archiveAthlete.js does for coaches.

import {
  getCoachToken, getRefreshToken, getSignedInRole, setCoachToken, setRefreshToken,
  setSignedInRole,
} from '../coach/api.js'

const LOOKUP = '/api/auth/login-link/lookup/'
const REDEEM = '/api/auth/login-link/redeem/'
const SIGN_IN = '/api/auth/login/'
const RENEW = '/api/auth/refresh/'

async function post(url, body, fetchImpl) {
  try {
    const response = await fetchImpl(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await response.json().catch(() => ({}))
    return { response, data }
  } catch {
    return { response: null, data: {} }
  }
}

function saveSignIn(data) {
  setCoachToken(data.access)
  setSignedInRole(data.role)
  setRefreshToken(data.refresh)
}

/** "Who is this link for?" → found (with the name), dead, too-many, or offline. */
export async function lookupLoginLink(link, { fetchImpl = fetch } = {}) {
  if (!link) return { status: 'dead' }
  const { response, data } = await post(LOOKUP, { link }, fetchImpl)
  if (!response) return { status: 'offline' }
  if (response.status === 429) return { status: 'too-many' }
  if (response.ok && data.athlete_name) return { status: 'found', name: data.athlete_name }
  return { status: 'dead' }
}

/** Use the link. Signed in → saved; a field problem → its messages; or dead/too-many/offline. */
export async function redeemLoginLink(link, username, password, { fetchImpl = fetch } = {}) {
  const { response, data } = await post(REDEEM, { link, username, password }, fetchImpl)
  if (!response) return { status: 'offline' }
  if (response.status === 429) return { status: 'too-many' }
  if (response.status === 404) return { status: 'dead' }
  if (response.status === 400) {
    return { status: 'fields', fields: data.fields || {}, message: data.detail || 'Please check the form.' }
  }
  if (response.ok && data.access) { saveSignIn(data); return { status: 'signed-in' } }
  return { status: 'offline' }
}

/** Sign in with a username and password. Only athlete logins are kept here. */
export async function athleteSignIn(username, password, { fetchImpl = fetch } = {}) {
  const { response, data } = await post(SIGN_IN, { username, password }, fetchImpl)
  if (!response) return { status: 'refused', message: 'The server could not be reached. Try again.' }
  if (response.status === 429) return { status: 'refused', message: 'Too many tries. Wait a minute, then try again.' }
  if (response.status === 401) {
    return { status: 'refused', message: data.code === 'no_role' && data.detail
      ? data.detail : 'The username or password was not accepted.' }
  }
  if (!response.ok || !data.access) return { status: 'refused', message: 'Unable to sign in. Try again.' }
  if (data.role !== 'athlete') return { status: 'coach' }
  saveSignIn(data)
  return { status: 'signed-in' }
}

/** When a sign-in token runs out, as a time in milliseconds (0 if it can't be read). */
export function expiresAt(token) {
  try {
    const part = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(part)).exp * 1000
  } catch {
    return 0
  }
}

/**
 * A working sign-in token for the signed-in athlete, renewing it if it has run out
 * (or is about to). null means "not signed in as an athlete any more": the 30 days
 * are up, the login was replaced by a new link, or the coach removed it.
 */
export async function freshAthleteToken({ fetchImpl = fetch, now = Date.now() } = {}) {
  if (getSignedInRole() !== 'athlete') return null
  const token = getCoachToken()
  if (token && expiresAt(token) > now + 60_000) return token
  const refresh = getRefreshToken()
  if (!refresh) { setCoachToken(null); return null }
  const { response, data } = await post(RENEW, { refresh }, fetchImpl)
  if (!response) return token   // offline: keep what we have, try again later
  if (!response.ok || !data.access) { setCoachToken(null); return null }
  setCoachToken(data.access)
  if (data.refresh) setRefreshToken(data.refresh)
  return data.access
}

export function athleteSignOut() {
  setCoachToken(null)
}
