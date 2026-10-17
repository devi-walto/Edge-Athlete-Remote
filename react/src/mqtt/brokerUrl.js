// brokerUrl.js — the address a screen uses to reach the live-update broker.
//
// Why this file exists: a local install and a remote server reach the broker
// differently, and every screen that listens must agree on how.
//   local  (plain http://) → ws://<host>:9001, straight to the broker's browser door.
//   remote (https://)      → wss://<host>/mqtt, the site's own address. The reverse
//                            proxy passes /mqtt on to the broker (k8s/app/base/ingress.yaml).
//
// The page's own address decides: a local install is always plain http and a remote
// server is always https. An https page isn't allowed to open a plain ws:// connection
// anyway, so this can't pick the wrong one. Nothing to wait for, so screens can
// connect on their first render.
export function brokerUrl(location = window.location) {
  if (location.protocol === 'https:') return `wss://${location.host}/mqtt`
  return `ws://${location.hostname}:9001`
}
