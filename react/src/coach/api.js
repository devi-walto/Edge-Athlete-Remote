/*
 * Coach REST helpers — JWT Bearer calls against the base-station /api.
 * Token lives in localStorage so a refresh does not kick the coach out mid-demo.
 */

const TOKEN_KEY = 'coach_access_token'
const ROLE_KEY = 'coach_signed_in_role'
// The renewal token, kept for athletes only (spec 03): an athlete stays signed in on
// their own phone for 30 days by renewing the short sign-in token with this. Coaches
// don't keep one yet, so their sign-in works exactly as before.
const REFRESH_KEY = 'signed_in_refresh_token'

function responseError(data, status) {
  if (typeof data === 'string') return `HTTP ${status}`
  if (data?.error || data?.detail) return data.error || data.detail
  if (!data) return `HTTP ${status}`
  return Object.entries(data).map(([key, value]) => {
    const label = key === 'non_field_errors' ? '' : `${key}: `
    return label + (Array.isArray(value) ? value.join(' ') : String(value))
  }).join(' ') || `HTTP ${status}`
}

export function getCoachToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setCoachToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(ROLE_KEY)
    localStorage.removeItem(REFRESH_KEY)
  }
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY)
}

export function setRefreshToken(token) {
  if (token) localStorage.setItem(REFRESH_KEY, token)
  else localStorage.removeItem(REFRESH_KEY)
}

/** The role the server reported at sign-in: 'administrator', 'coach' or 'athlete'.
 *  Kept beside the token so a screen knows who it is talking to before it asks the
 *  server anything. It only decides what to SHOW; the server decides what is allowed.
 *  A login stored before roles existed has none, and those were all coaches. */
export function getSignedInRole() {
  return localStorage.getItem(ROLE_KEY)
}

export function setSignedInRole(role) {
  if (role) localStorage.setItem(ROLE_KEY, role)
  else localStorage.removeItem(ROLE_KEY)
}

export async function coachLogin(username, password, { persist = true, coachOnly = false } = {}) {
  const res = await fetch('/api/auth/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  // Rate limiting answers before any JSON exists, and "HTTP 429" tells a coach
  // standing at a tablet nothing. Say what to do instead.
  if (res.status === 429) throw new Error('Too many login attempts. Wait a minute, then try again.')
  const data = await res.json().catch(() => ({}))
  // The password was right, but the login is attached to neither a coach nor an
  // athlete. Calling that a wrong password would send someone off to reset a
  // password that works; pass on the server's own sentence.
  if (res.status === 401 && data.code === 'no_role' && typeof data.detail === 'string') throw new Error(data.detail)
  if (res.status === 401) throw new Error('The username or password was not accepted.')
  if (!res.ok || !data.access) {
    const detail = data.detail || data.error || `HTTP ${res.status}`
    throw new Error(typeof detail === 'string' ? detail : 'login failed')
  }
  if (coachOnly && data.role === 'athlete') throw new Error('Only a coach can do this. Ask your coach to sign in here.')
  if (persist) {
    setCoachToken(data.access)
    setSignedInRole(data.role)
  }
  return data.access
}

export async function coachFetch(path, { token, method = 'GET', body } = {}) {
  const headers = {}
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const res = await fetch(path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (res.status === 429) {
    const error = new Error('Too many attempts. Wait a minute, then try again.')
    error.status = 429
    throw error
  }
  const text = await res.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!res.ok) {
    const detail = responseError(data, res.status)
    const error = new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    error.status = res.status
    error.code = data && data.code
    error.data = data
    throw error
  }
  return data
}

/** Who is signed in, whether they administer the box, and whether they must
 *  change their temporary password before the rest of the app opens. */
export function fetchCurrentCoach(token) {
  return coachFetch('/api/auth/me/', { token })
}

export function changePassword(token, currentPassword, newPassword) {
  return coachFetch('/api/auth/password/', {
    token,
    method: 'POST',
    body: { current_password: currentPassword, new_password: newPassword },
  })
}

export function listCoaches(token) {
  return coachFetch('/api/coaches/', { token })
}

export function createCoach(token, username, password) {
  return coachFetch('/api/coaches/', {
    token,
    method: 'POST',
    body: password ? { username, password } : { username },
  })
}

export function updateCoach(token, id, changes) {
  return coachFetch(`/api/coaches/${id}/`, { token, method: 'PATCH', body: changes })
}

export function resetCoachPassword(token, id) {
  return coachFetch(`/api/coaches/${id}/reset/`, { token, method: 'POST' })
}

/** Short slice shown on waiting tablets / coach dropdowns (not a full UUID wall). */
export function shortId(id) {
  if (!id) return '—'
  const s = String(id)
  return s.length <= 8 ? s : s.slice(-8)
}
