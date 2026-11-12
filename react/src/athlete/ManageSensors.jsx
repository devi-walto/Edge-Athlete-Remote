// ManageSensors.jsx — /athlete/sensors: the athlete's sensors, opened from My sensor's Manage.
//
// Why this file exists: Home's and Account's sensor row needs somewhere to go once the
// athlete has a sensor. For now this is the sensor list that already existed (MySensor.jsx:
// remove with a confirm); spec 14 Phase 10 rebuilds it to board F_Ath_M1 (live / standby,
// Swap, Add new sensor). It's a drill-down page, so its only way out is back to where it was
// opened from (Home or Account). Adding a sensor opens the Add my sensor page, whose back
// link and Done come back here.
import { navigate } from '../router.js'
import AthletePage, { SENSORS_PATH, SENSOR_ADD_PATH, backFor } from './AthletePage.jsx'
import { MySensorSection } from './MySensor.jsx'

export default function ManageSensors() {
  const search = window.location.search
  const up = new URLSearchParams(search).get('from')
  const addPath = `${SENSOR_ADD_PATH}?from=sensors${up ? `&up=${encodeURIComponent(up)}` : ''}`
  return <AthletePage here={SENSORS_PATH + search} back={backFor(search)}>
    <h1 className="athlete-page-title">My sensors</h1>
    <MySensorSection onAdd={() => navigate(addPath)} />
  </AthletePage>
}
