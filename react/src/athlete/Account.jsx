// Account.jsx — /athlete/account: who this login is, read-only.
//
// Why this file exists: the athlete's menu has Account (spec 10). For now it shows their
// name, their teams and their sensor; Phase 5 finishes it to board F_Ath_A1 (the username,
// and the "Changing your password?" help). Everything here is the coach's to change.
import { useEffect, useState } from 'react'
import QuietRow from '../ui/QuietRow.jsx'
import SectionLabel from '../ui/SectionLabel.jsx'
import AthletePage, { ACCOUNT_PATH, HOME_PATH, toSignIn } from './AthletePage.jsx'
import { HOME, getJson } from './athleteApi.js'
import SensorRow from './SensorRow.jsx'

export default function Account() {
  const [me, setMe] = useState(null)
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
    <h1 className="athlete-page-title">Account</h1>
    {me && <>
      <SectionLabel as="h2">You</SectionLabel>
      <QuietRow name={me.name} meta={me.groups.join(' · ') || 'Not on a team yet'} />
      <SensorRow />
    </>}
  </AthletePage>
}
