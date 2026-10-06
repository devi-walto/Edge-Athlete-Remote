// Why this file exists: every coach has their own login, and somebody has to hand them
// out. That somebody is an administrator, and this is their page: see who can sign in,
// add a coach, reset a forgotten password, switch a login off when a coach leaves, and
// make another coach an administrator.
//
// Three things here are deliberate:
//   - A new or reset password is TEMPORARY and is shown exactly once, on this page,
//     right after it is made. It cannot be read back later, by anyone. The coach must
//     replace it the first time they sign in.
//   - An administrator's own row offers only "Change password". Deactivating or demoting
//     yourself is how an installation ends up with nobody able to manage it.
//   - The word is "Administrator". "Head coach" is a label on a training group and has
//     nothing to do with who may manage logins.
//
// The calls to the server and the guards are Braydon's, from the coach-accounts work;
// the layout follows the Final design board `F_Coaches`.
import { useEffect, useState } from 'react'
import { createCoach, listCoaches, resetCoachPassword, updateCoach } from './api.js'
import './account.css'

export default function Coaches({ accessToken, me, onLogout, onChangePassword }) {
  const [coaches, setCoaches] = useState([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [handoff, setHandoff] = useState(null)   // { username, password } — shown once
  const [adding, setAdding] = useState(false)
  const [username, setUsername] = useState('')
  const [copied, setCopied] = useState(false)

  function failed(err) {
    // 401: the login has expired. 403: this login may not be here. Either way the page
    // has nothing to show, so hand back to sign in rather than display an empty table.
    if (err.status === 401 || err.status === 403) onLogout()
    else setError(err.message || 'The server could not be reached.')
  }
  async function load() {
    setLoading(true)
    setError('')
    try { setCoaches(await listCoaches(accessToken)) } catch (err) { failed(err) } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [accessToken])

  async function run(work) {
    setBusy(true)
    setError('')
    try { await work() } catch (err) { failed(err) } finally { setBusy(false) }
  }
  function add(event) {
    event.preventDefault()
    if (busy || !username.trim()) return
    setHandoff(null)
    run(async () => {
      const created = await createCoach(accessToken, username.trim())
      setUsername('')
      setAdding(false)
      setCopied(false)
      setHandoff({ username: created.username, password: created.temporary_password })
      await load()
    })
  }
  function reset(coach) {
    if (!window.confirm(`Reset the password for ${coach.username}? Their current password stops working, and they will choose a new one when they next sign in.`)) return
    setHandoff(null)
    run(async () => {
      const updated = await resetCoachPassword(accessToken, coach.id)
      setCopied(false)
      setHandoff({ username: updated.username, password: updated.temporary_password })
      await load()
    })
  }
  function change(coach, changes, question) {
    if (question && !window.confirm(question)) return
    run(async () => { await updateCoach(accessToken, coach.id, changes); await load() })
  }
  async function copy() {
    try { await navigator.clipboard.writeText(handoff.password); setCopied(true) } catch { setCopied(false) }
  }

  const admins = coaches.filter((c) => c.is_staff && c.is_active).length
  return <section className="acct-body">
    <header className="acct-hero">
      <div>
        <span className="acct-label">Account · administrators only</span>
        <h2>Coaches</h2>
        <p>Every coach can use the whole workspace. Administrators can also add coaches, reset passwords and deactivate logins.</p>
      </div>
      {!loading && <span>{coaches.length} {coaches.length === 1 ? 'coach' : 'coaches'} · {admins} {admins === 1 ? 'administrator' : 'administrators'}</span>}
    </header>

    {error && <p className="acct-error" role="alert">{error} <button type="button" className="acct-quiet is-strong" onClick={load} disabled={busy || loading}>Retry</button></p>}

    {handoff && <div className="acct-handoff" role="status">
      <div>
        <b>Temporary password for {handoff.username}</b>
        <span>Pass it on now. It cannot be shown again, and they will choose their own when they first sign in.</span>
      </div>
      <code>{handoff.password}</code>
      <button type="button" className="acct-solid" onClick={copy}>{copied ? 'Copied' : 'Copy'}</button>
      <button type="button" className="acct-quiet" onClick={() => setHandoff(null)}>Done</button>
    </div>}

    <div className="acct-list-head">
      <span className="acct-label">Coach logins</span>
      {!adding && <button type="button" className="acct-primary" disabled={busy} onClick={() => setAdding(true)}>Add coach</button>}
    </div>

    {adding && <form className="acct-add" onSubmit={add}>
      <label className="acct-field">Username for the new coach
        <input type="text" autoFocus maxLength={150} required value={username} disabled={busy} onChange={(e) => setUsername(e.target.value)} />
      </label>
      <button className="acct-primary" style={{ minHeight: 48 }} disabled={busy || !username.trim()}>{busy ? 'Saving…' : 'Create login'}</button>
      <button type="button" className="acct-quiet" disabled={busy} onClick={() => { setAdding(false); setUsername('') }}>Cancel</button>
    </form>}

    {loading ? <p className="acct-note" role="status">Loading coaches…</p> : <div className="acct-table">
      <div className="acct-row is-head"><span>Coach</span><span>Role</span><span>Status</span><span>Actions</span></div>
      {coaches.map((coach) => {
        const self = coach.username === me?.username
        return <div className={`acct-row${coach.is_active ? '' : ' is-off'}`} key={coach.id}>
          <span className="acct-who"><b>{coach.username}</b>{self && <small>you</small>}</span>
          <span className="acct-role">{coach.is_staff ? <em className="acct-badge" style={{ fontStyle: 'normal', fontSize: 11, padding: '5px 10px' }}>Administrator</em> : 'Coach'}</span>
          <span className="acct-status">
            <i className={`acct-dot ${!coach.is_active ? 'is-off' : coach.must_change_password ? 'is-due' : 'is-on'}`} />
            {coach.is_active ? 'Active' : 'Deactivated'}
            {coach.is_active && coach.must_change_password && <small>must change password</small>}
          </span>
          <span className="acct-actions">
            {self
              ? <button type="button" className="acct-quiet" disabled={busy} onClick={onChangePassword}>Change password</button>
              : !coach.is_active
                ? <button type="button" className="acct-quiet is-strong" disabled={busy} onClick={() => change(coach, { is_active: true })}>Reactivate</button>
                : <>
                  <button type="button" className="acct-quiet" disabled={busy} onClick={() => reset(coach)}>Reset password</button>
                  <button type="button" className="acct-quiet" disabled={busy} onClick={() => change(coach, { is_staff: !coach.is_staff })}>{coach.is_staff ? 'Remove administrator' : 'Make administrator'}</button>
                  <button type="button" className="acct-quiet is-danger" disabled={busy}
                    onClick={() => change(coach, { is_active: false }, `Deactivate ${coach.username}? They will not be able to sign in. Nothing they recorded is removed, and you can reactivate them later.`)}>Deactivate</button>
                </>}
          </span>
        </div>
      })}
    </div>}

    <p className="acct-note">There must always be at least one active administrator. You cannot deactivate yourself or remove your own administrator access.</p>
  </section>
}
