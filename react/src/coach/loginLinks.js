// loginLinks.js — the coach's side of athlete login links, as plain functions.
//
// Why this file exists: on a remote school an athlete signs in on their own phone,
// and the coach gets them there by sending a one-time login link (spec 03). The
// roster shows each athlete's login status and offers the buttons; this file holds
// the three server calls and the words the roster shows, so they can be tested on
// their own and worded the same way wherever they appear.
//
// The rules (works once, 3 days, a newer link cancels the older, only a fingerprint
// is stored) are the server's. Nothing here keeps a link: the dialog shows it once,
// and it is gone when the dialog closes.

const linkUrl = (athleteId) => `/api/athletes/${athleteId}/login-link/`
const loginUrl = (athleteId) => `/api/athletes/${athleteId}/login/`

async function call(url, method, accessToken, fetchImpl) {
  try {
    return await fetchImpl(url, {
      method,
      headers: { Accept: 'application/json', Authorization: `Bearer ${accessToken}` },
    })
  } catch {
    return null
  }
}

async function refusal(response, fallback) {
  if (!response) return { status: 'refused', message: 'The server could not be reached. Nothing was changed.' }
  if (response.status === 401) return { status: 'signed-out' }
  const body = await response.json().catch(() => ({}))
  return { status: 'refused', message: body.detail || fallback }
}

/**
 * Make a new link. Resolves to one of:
 *   { status: 'sent', link, expiresAt }   the only time the full link exists
 *   { status: 'signed-out' }
 *   { status: 'refused', message }
 */
export async function sendLoginLink(athlete, accessToken, { fetchImpl = fetch } = {}) {
  const response = await call(linkUrl(athlete.id), 'POST', accessToken, fetchImpl)
  if (response?.status === 201) {
    const body = await response.json()
    return { status: 'sent', link: body.link, expiresAt: body.expires_at }
  }
  return refusal(response, `A login link for ${athlete.name} could not be made.`)
}

/** Cancel the athlete's unused link. Their login, if they have one, keeps working. */
export async function cancelLoginLink(athlete, accessToken, { fetchImpl = fetch } = {}) {
  const response = await call(linkUrl(athlete.id), 'DELETE', accessToken, fetchImpl)
  if (response?.status === 204) return { status: 'cancelled' }
  return refusal(response, 'That link could not be cancelled.')
}

export function unlinkQuestion(athlete) {
  return `Remove ${athlete.name}'s login? They are signed out everywhere and can't join a `
    + 'session until you send a new login link. Everything they have lifted is kept.'
}

/** Ask, then remove the athlete's login. Their sets and reports stay. */
export async function unlinkLogin(athlete, accessToken,
  { confirm = (text) => window.confirm(text), fetchImpl = fetch } = {}) {
  if (!confirm(unlinkQuestion(athlete))) return { status: 'cancelled' }
  const response = await call(loginUrl(athlete.id), 'DELETE', accessToken, fetchImpl)
  if (response?.status === 204) return { status: 'unlinked' }
  return refusal(response, `${athlete.name}'s login could not be removed.`)
}

/** "Oct 8, 6:10 PM", in the coach's own time. */
export function formatExpiry(value) {
  const when = new Date(value)
  if (Number.isNaN(when.getTime())) return ''
  return when.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

/**
 * What the roster's Login column shows, from the athlete list's login fields:
 *   { label: 'Linked', detail: 'riley', tone: 'linked' }
 *   { label: 'Link sent', detail: 'expires Oct 9', tone: 'sent' }
 *   { label: 'No login yet', detail: 'cannot join', tone: 'none' }
 */
export function loginStatus(athlete) {
  if (athlete.login_status === 'link_sent') {
    const expiry = formatExpiry(athlete.link_expires_at)
    return { label: 'Link sent', detail: expiry ? `expires ${expiry.split(',')[0]}` : '', tone: 'sent' }
  }
  if (athlete.login_status === 'linked') {
    return { label: 'Linked', detail: athlete.login_username || '', tone: 'linked' }
  }
  return { label: 'No login yet', detail: 'cannot join', tone: 'none' }
}

/** A login exists, or a link is waiting: the row's button reads "Send new link". */
export function hasLoginOrLink(athlete) {
  return athlete.login_status === 'linked' || athlete.login_status === 'link_sent'
}
