// LoginLinkDialog.jsx — the one time a coach sees an athlete's login link.
//
// Why this file exists: a login link is as good as a password for that athlete,
// so the coach sees it exactly once, right after making it, with what it does and
// how not to share it. Built to the Final designs board F_Remote_LoginLink (spec
// 03, Phase 3). Remote only: a local install never offers login links.
//
// The link lives only in the props of this dialog. The parent drops it when the
// dialog closes, so it is not kept anywhere on the page afterwards.

import { useEffect, useRef, useState } from 'react'
import { formatExpiry } from './loginLinks.js'
import './LoginLinkDialog.css'

export default function LoginLinkDialog({ athlete, link, expiresAt, busy, error, onCancelLink, onDone }) {
  const [copied, setCopied] = useState(false)
  const copyButton = useRef(null)
  const done = useRef(onDone)
  done.current = onDone
  const first = athlete.name.split(' ')[0]

  // Start on Copy link, the one thing the coach came here to do; Escape closes.
  // Runs once when the dialog opens, so later updates never move the focus.
  useEffect(() => {
    copyButton.current?.focus()
    const onKey = (event) => { if (event.key === 'Escape') done.current() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  async function copy() {
    try {
      await navigator.clipboard.writeText(link)
      setCopied(true)
    } catch {
      // No clipboard (an older browser): select the text so the coach can copy it.
      document.getElementById('login-link-text')?.select()
    }
  }

  return (
    <div className="login-link-backdrop" onClick={onDone}>
      <section className="login-link-dialog" role="dialog" aria-modal="true"
        aria-labelledby="login-link-title" onClick={(event) => event.stopPropagation()}>
        <span className="login-link-eyebrow">Login link</span>
        <h2 id="login-link-title">For {athlete.name}</h2>
        <p className="login-link-lead">
          Send this to {first} directly. Opening it lets {first} choose a username and
          password, and connects that login to this athlete.
        </p>

        <div className="login-link-copy">
          <input id="login-link-text" readOnly value={link} aria-label={`Login link for ${athlete.name}`}
            onFocus={(event) => event.target.select()} />
          <button type="button" ref={copyButton} className="login-link-primary" onClick={copy}>
            {copied ? 'Copied' : 'Copy link'}
          </button>
        </div>

        <dl className="login-link-facts">
          <div><dt>Works</dt><dd>Once</dd></div>
          <div><dt>Expires</dt><dd>{formatExpiry(expiresAt)}</dd></div>
          <div><dt>Earlier links</dt><dd>Cancelled</dd></div>
        </dl>

        <div className="login-link-warning" role="note">
          <span aria-hidden="true">⚠</span>
          <p><b>Don't post this in a group chat</b>
            Whoever opens it becomes {first}. The session link is the one that is safe to share
            with everyone.</p>
        </div>

        <p className="login-link-note">
          Forgotten password later? Send a new link from the roster. It replaces the login, never
          the training history.
        </p>

        {error && <p className="coach-login-error" role="alert">{error}</p>}

        <div className="login-link-actions">
          <button type="button" className="login-link-secondary" disabled={busy} onClick={onCancelLink}>
            {busy ? 'Cancelling…' : 'Cancel this link'}
          </button>
          <button type="button" className="login-link-done" onClick={onDone}>Done</button>
        </div>
      </section>
    </div>
  )
}
