// Account.jsx — /athlete/account: who this login is, read-only.
//
// Why this file exists: the athlete's name menu has Account (spec 10, Phase 5; boards
// F_Ath_A1, A2). It shows their name, username and teams, all the coach's to change
// ("Your coach manages your name and teams"), and their sensor with Manage, the one thing
// they can act on. There's no password change here on purpose (a smaller door to attack,
// spec 03): "Changing your password?" opens, in place, how to get a new login link from
// the coach. Sign out of this phone is at the bottom. No route of its own: the details come
// from Home's.
import { useEffect, useState } from 'react'
import Button from '../ui/Button.jsx'
import QuietRow from '../ui/QuietRow.jsx'
import AthletePage, { ACCOUNT_PATH, HOME_PATH, signOut, toSignIn } from './AthletePage.jsx'
import { HOME, getJson } from './athleteApi.js'
import SensorRow from './SensorRow.jsx'

export default function Account() {
  const [me, setMe] = useState(null)
  const [helping, setHelping] = useState(false)
  useEffect(() => {
    let cancelled = false
    getJson(HOME).then(({ status, body }) => {
      if (cancelled) return
      if (status === 401 || status === 403) toSignIn(ACCOUNT_PATH)
      else if (status === 200) setMe(body.athlete)
    })
    return () => { cancelled = true }
  }, [])
  return <AthletePage name={me?.name} here={ACCOUNT_PATH} back={{ label: 'Home', to: HOME_PATH }}>
    <section className="athlete-greeting">
      <span className="athlete-greeting-label">Account</span>
      <h1>Your account</h1>
      <span className="athlete-greeting-groups">Your coach manages your name and teams.</span>
    </section>
    {me && <>
      <div className="athlete-account-rows">
        <QuietRow name={me.name} meta="Name" />
        <QuietRow name={me.username || '--'} meta="Username" />
        <QuietRow name={me.groups.join(' · ') || 'Not on a team yet'} meta="Teams" />
      </div>
      <SensorRow from="account" />
      <div className="athlete-account-help">
        <Button kind="quiet-lime" aria-expanded={helping} aria-controls="password-help"
          onClick={() => setHelping(!helping)}>Changing your password? {helping ? '▴' : '▾'}</Button>
        {helping && <p id="password-help" className="athlete-account-help-text">
          You can't change it here. Ask your coach in person for a new login link. Open it on
          your phone and it lets you choose a new password. The old one stops working.
        </p>}
      </div>
      <Button kind="solid" className="athlete-wide" onClick={signOut}>Sign out of this phone</Button>
    </>}
  </AthletePage>
}
