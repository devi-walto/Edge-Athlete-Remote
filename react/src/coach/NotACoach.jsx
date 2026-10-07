// Why this file exists: athletes have logins too now, and an athlete can end up on the
// coach workspace's address with a perfectly good sign-in. The server refuses every
// coach action for them, so without this page they would see a workspace where every
// panel fails. This says plainly where they are and where to go, and loads nothing else.
import { Mark } from './SignIn.jsx'
import './account.css'

export default function NotACoach({ onSignOut }) {
  return <main className="acct-screen">
    <section className="acct-card" role="alert">
      <div className="acct-mark-row"><Mark /><div className="acct-mark-name"><b>Edge Athlete</b><span>Coach workspace</span></div></div>
      <h1>This is the coach workspace</h1>
      <p className="acct-note">You are signed in as an athlete. Use the session link your coach sent you.</p>
      <button type="button" className="acct-solid" onClick={onSignOut}>Sign out</button>
    </section>
  </main>
}
