# Validation record

Review date: 17 November 2026 (Asia/Calcutta).

## Callback raw-text rendering fix — 18 November 2026

Reproduced the exact `Unexpected text node: .` warning on a callback route in
its initial loading state. The period is part of React Native Web's log format:
the leaked child was an empty string from `{displayError && ...}`, forwarded
through AuthPage into ScrollView. Changed the conditional to an explicit
element-or-null ternary. No UI layout or styling changed.

Frontend lint and TypeScript pass. Added `react/jsx-no-leaked-render` for auth
routes and verified it rejects a string-valued conditional child. Restarted
Metro with a clean cache; a fresh callback page exercised loading followed by
recovery and captured zero matching text-node console errors. The earlier
source error was reproduced twice before the change; no warnings were hidden.

## Google callback recovery — 18 November 2026

A browser visit opened the bare backend callback URL without an authorization
code or state. The rejection was correct, but its raw DRF error screen was
unhelpful. Direct/expired HTML requests now redirect to the existing themed
frontend recovery screen, which explains how to restart from Continue with
Google. JSON callers continue to receive HTTP 400. No state/nonce/PKCE checks
were removed or bypassed.

All **20 backend tests**, frontend lint and TypeScript pass. New tests prove
direct and expired browser callbacks do not call Google or create sessions or
tickets. Browser verification confirmed the callback redirect and return to the
normal sign-in page. A successful live Google account roundtrip remains pending.

## Authentication milestone — 18 November 2026

- Django 5.2 backend and locked dependencies installed into `backend/.venv` using Python 3.12. Initial custom-user migrations and Moments migration apply; `manage.py check` and migration drift checks pass.
- All **18** authentication/authorization regression tests pass on the local SQLite development database, including college-only signup, verification/expiry/replay, policy versions, onboarding, unique/reserved usernames, password-change token invalidation, session rotation/logout, role separation, web CSRF/cookies, private search, published/read-only Moments, malformed JSON, throttling and mocked Google contracts.
- Backend Ruff checks pass. Frontend Expo lint configuration is now explicit; TypeScript and lint pass after resolving the prior web ref type and hydration/animation lint compatibility issues. Native animation handle compatibility suppressions are narrowly scoped and documented.
- Browser verification using a temporary local member exercised real sign-in, username creation, profile save, all five tour steps, Spotlight search and member-profile display. Profile's header now has Logout instead of the inbox icon. The temporary account is removed after verification; the main administrator's onboarding is left for the user.
- Follow-up UI checks at 320×640, 390×844 and desktop width verified the structural overlap fixes. Spotlight search remains 24 pixels above the first event card and scrolls together with it (gap preserved after scrolling). Profile uses a measured, flowing identity/stats header and a small pencil beside the name; there are no large editing/tour buttons. The tour is first-login-only. The editor opens with Save changes, and Find Yourself has a 46-pixel touch target separated from the photo grid by 20 pixels. Browser logout returned to sign-in; viewport overrides and the extra QA tab were cleaned up.
- The main administrator was provisioned as Pixel / pixel.club@sait.ac.in. Initial password is in the ignored local credential file, never printed or hardcoded.
- Both actual Google credential settings are detected from the private environment. A configured Google-start request passes CSRF, client-ID, PKCE and fixed-callback checks. No provider credentials were printed. The real Google-account consent/callback roundtrip is still pending user testing; mocked provider tests are not represented as live sign-in verification.
- Password reset remains disabled by explicit user request. Development verification messages use a local file backend; actual SMTP delivery is pending. Existing feed/gallery/event data and social interactions are still sample/local data pending later content APIs. Face recognition remains unavailable and captures no selfies.
- Not verified: Android/native OAuth deep links or playback, actual video content delivery, Neon/PostgreSQL concurrency, 20/50/100-user capacity, deployment, production policy approval, and release. The installed npm graph reports existing advisories; dependency security remediation is required before production. No forced package upgrades were applied.

The sections below record earlier milestone results and do not override this current implementation status.

## Follow-up: desktop preview startup fix

The running preview exposed a real SSR failure: `Cannot read properties of
undefined (reading 'RuntimeEffect')`. The native entry imported `PixelApp`,
which imported `GlassScene` and compiled its shader before browser CanvasKit
was initialized.

Added a web-only route and `PixelWeb` loader. The loader waits until browser
mount, initializes Skia using `WithSkiaWeb`, then dynamically imports the existing
screen. Matching WASM is copied from the locked installed package into the
public folder by `postinstall`, `preweb`, or `npm run setup:web`. No existing
layouts, styles, shaders, or Android entry were changed.

Verified by reloading `http://localhost:8081/` in the browser: the server error
was replaced by the existing intro, followed by rendered feed content and the
five navigation tabs. Metro successfully bundled the web route and dynamic
PIXEL module. Android/native behavior was not retested.

Follow-up `tsc --noEmit` reports only the existing `app-tabs.web.tsx:38` ref
type incompatibility. Expo-generated web types are now available after running
the preview; the four-diagnostic result below records the earlier baseline.
No new type errors were reported for the loader. Lint was attempted again but
entered automatic missing-tooling installation, which was stopped; its
unrequested package edits were removed. A successful source-lint run is still
pending. Earlier claims of an unchanged frontend apply to the review milestone,
before this targeted startup fix.

## Completed checks

- Cloned `https://github.com/kanishkk52/Pixel_Android` into `frontend/` and recorded commit `586e32daccf0619efdf16434087771d48b8c895b`.
- Read `frontend/AGENTS.md`, tracked source/configuration, active entry points, data/notification state, renderer and shader, dependency declarations, EAS configuration and license.
- Installed the original locked dependency set with `npm ci --ignore-scripts --no-audit --no-fund`. The first completed install added 567 packages. Lifecycle scripts were intentionally not run; this is not proof of a native build.
- Ran `npm exec -- tsc --noEmit` against that original dependency set. It exited with status 1 and the four existing diagnostics below.
- Ran `npm run lint` in CI mode. The sandbox initially prevented Expo from creating its user configuration directory. A permitted retry reached Expo's lint setup, which found no lint config, automatically installed ESLint/config dependencies and generated `eslint.config.js`, then exited with status 1. Its reported error was: `npx expo lint requires ESLint version 8.57.0 or greater. Upgrade eslint or use npx eslint directly.` This does not establish a source-lint result or a definitive root cause.
- Removed only that newly generated lint config and restored `package.json` / `package-lock.json` from the reviewed Git commit. Reinstalled the original lockfile to keep local dependencies consistent. No source/UI or dependency upgrades were retained.
- Checked that the final frontend tracked files match upstream and that the requested service/documentation directories exist.

The automatic temporary lint install also emitted dependency advisory warnings. Those warnings included the temporary tooling graph; a reproducible security audit of the original dependency graph remains pending. No automatic audit fix or forced upgrade was applied.

## Existing TypeScript failures

| Location | Diagnostic |
| --- | --- |
| `frontend/src/components/animated-icon.web.tsx:5` | TS2307: missing type declarations for `./animated-icon.module.css` |
| `frontend/src/components/app-tabs.web.tsx:38` | TS2322: incompatible React Native element/ref type in the web tab button |
| `frontend/src/constants/theme.ts:6` | TS2882: no module/type declaration for side-effect import `@/global.css` |
| `frontend/src/pixel/Notifications.tsx:613` | TS2353: `touchAction` is not accepted by the typed native animated style |

These existed before project implementation changes. Phase 0 must resolve them with appropriate platform/type declarations and typed component props, preserving appearance and behavior. Do not suppress all errors or disable strict checking to obtain a passing baseline.

## Not yet verified

- Android launch, native rendering, gesture behavior, animation smoothness, screenshot parity and signed builds.
- Expo dependency compatibility diagnostics, a successful source lint run, or a clean production dependency security audit.
- Any Django/FastAPI behavior or tests: the new service folders contain design documentation only.
- Neon, pgvector queries, Drive/R2 access, real notifications, model licensing/accuracy, consent/deletion processing and hosting.
- Capacity at 20/50/100 active users, AI concurrency, costs, legal/store compliance or Play submission.

The local `python --version` command resolved to a Windows Apps launcher that could not execute in the current environment. No Python service setup was attempted in this milestone; verify/install an actual interpreter when Phase 1 begins.

## Recheck commands

From `frontend/`, once Phase 0 tooling fixes are intentionally implemented:

```powershell
npm ci
npm exec -- tsc --noEmit
npm run lint
npm exec -- expo-doctor
```

`expo-doctor` is an additional dependency diagnostic to run in Phase 0, not a check already passed here. Missing ESLint configuration currently causes Expo to attempt automatic setup; review resulting package/config changes deliberately. Keep the original source baseline available for comparison.
