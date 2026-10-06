// Why this file exists: athletes leave. Deleting one would tear their sets out of every
// past report, so an athlete is never deleted; they are ARCHIVED. An archived athlete
// disappears from the roster, the groups and every picker, and their NFC tag is freed
// for someone else, but everything they lifted stays readable in Analytics.
//
// The server refuses while the athlete is in a session that is running, because pulling
// someone out from under a live set would lose it. That refusal comes back as a message
// to show, not as an error to swallow.
//
// The route and its rules are Braydon's, from the coach-accounts work. The question the
// coach is asked lives here, in one place, so every screen that offers Archive words it
// the same way.

export function archiveQuestion(athlete) {
  return `Archive ${athlete.name}? They leave the roster, their groups and every picker, `
    + 'and their tag is freed. Everything they have lifted is kept and stays in Analytics.'
}

/**
 * Ask, then archive. Resolves to one of:
 *   { status: 'cancelled' }            the coach said no
 *   { status: 'archived' }             done
 *   { status: 'signed-out' }           the login is no longer good
 *   { status: 'refused', message }     the server said no, and why
 */
export async function archiveAthlete(athlete, accessToken, { confirm = (text) => window.confirm(text), fetchImpl = fetch } = {}) {
  if (!confirm(archiveQuestion(athlete))) return { status: 'cancelled' }
  let response
  try {
    response = await fetchImpl(`/api/athletes/${athlete.id}/`, {
      method: 'DELETE',
      headers: { Accept: 'application/json', Authorization: `Bearer ${accessToken}` },
    })
  } catch {
    return { status: 'refused', message: 'The server could not be reached. Nothing was changed.' }
  }
  if (response.status === 204) return { status: 'archived' }
  if (response.status === 401) return { status: 'signed-out' }
  const body = await response.json().catch(() => ({}))
  return { status: 'refused', message: body.detail || body.error || `${athlete.name} could not be archived.` }
}
