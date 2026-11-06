# React

*Both installs*

**Why I picked it.** I learned it at my internship at the Cyber Innovation Center in Bossier, where they also taught me to use IndexedDB in a PWA to keep app state.

**What it is.** The app every screen runs, as a PWA: one app on any phone, tablet or laptop. One codebase, several faces chosen by the address. Vite is the build tool.

**How we use it.** The role comes from the path, and decides the PWA identity:

```
/rack/{n}          the athlete's screen at a rack
/dashboard         the wall display
/coach/planning    the coach's workspace (also /session, /analytics)
/coach/setup       the room layout
/rack/setup        a tablet waiting to be assigned
/athlete           an online athlete's sign-in and overview   (remote)
/session/{id}      the session link: the athlete's own rack    (remote)
/login-link        setting a login from a coach's link         (remote)
```

The bundle is built at image build time and served by nginx as static files. There
is no Node process in production.

**Where it lives.** `react/src/`. Built into `react/dist/`, which is gitignored —
the container builds its own.

**Worth knowing.** `react/src/rack/`, `react/src/db/repBuffer.js` and `react/src/device.js` were a **frozen contract** for most of the project. The freeze was lifted on Aug 10; they're ordinary files now ({doc}`../core/rack-screen`).

A screen that exists on both installs is **one screen**, with the online-only parts behind `useDeployment()`, never a second copy.

**More:** {doc}`../core/rack-screen` · {doc}`../core/coach-screens` ·
{doc}`../core/room-display`
