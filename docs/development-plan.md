# Phased implementation plan

Status update, 18 November 2026: the authentication portion of Phase 1 and its themed frontend/onboarding integration are implemented locally; see `authentication.md`. Typecheck and lint now pass, and authentication/role tests run on the local development database. PostgreSQL deployment, real SMTP, live Google-account verification and Android device testing remain pending. Content/social APIs, storage and recognition phases remain pending. Preserve existing frontend design and verify each runtime capability before claiming it works.

## Phase 0 — Reproducible frontend baseline

Existing review and three-directory layout are in place. Next, resolve the pre-existing frontend tooling/typecheck failures recorded in `validation.md` without changing visuals. Establish lint configuration, a repeatable dependency install, SDK compatibility diagnostics, and a source-controlled whole-project Git layout deliberately preserving upstream history.

Record Android screenshots/video for Gallery, Feed, Discover, Profile, Moments, modals, intro and notification drawer in both themes, including reduced motion. Check native back, keyboard, swipe, safe areas, scrolling and image load failures. Keep this reference for later visual comparison.

**Gate:** typecheck and lint pass, compatibility diagnostics are reviewed, and the existing UI runs on Android with a recorded baseline. No backend integration until failures are understood. Current source-level audit findings are not device-test results.

## Phase 1 — Django foundation, authentication and authorization

Implement `backend/config/`, `manage.py`, locked runtime/dev dependencies, environment example, and a local PostgreSQL + pgvector development setup (container or native). Add production settings checks and initial CI for actual checks.

Create `apps/accounts` with a custom User and the three fixed role choices before any migration. Add Profile, login/refresh/logout, refresh invalidation, Student/Faculty registration, college membership verification and an administrator-managed Faculty verification path. Bootstrap administrators securely. Add Django Admin, audit events, health/readiness endpoints, throttling and paginated API conventions.

Keep account role/status/privileged flags server-managed. Account deletion must be designed at creation time even if cleanup of later domains is introduced with those domains.

**Gate:** migrations apply on fresh PostgreSQL; authentication/refresh/revocation tests pass; role escalation fails; Student/Faculty cannot enter admin/manage users; another user's profile/private data is inaccessible; secrets are absent from source. Backend services run locally before adding content features.

## Phase 2 — Administrator content and social APIs

Implement `apps/events`, `content`, `social`, and `audit`: events/permissions/photos, posts, spotlights, newsletters, announcements, publication/archive lifecycle, likes, comments, connections and saved collections. Use Django Admin first for administration. Add ownership constraints, pagination, filters, indexes and efficient queryset loading. Provide a versioned OpenAPI contract for the mobile app.

Proposed route families (design only): `/api/v1/auth/*`, `/me/*`, `/events/*`, `/posts/*`, `/spotlights/*`, `/newsletters/*`, `/announcements/*`, `/notifications/*`; management writes require Administrator independently of route naming. Use dedicated interaction actions so member permissions cannot become general content-write permissions.

**Gate:** role matrix tests cover all CRUD actions, draft/private content stays invisible, guessed/nested IDs cannot bypass event access, interactions persist with uniqueness/ownership, and admin actions are audited. Verify pagination and bounded query counts with realistic fixtures.

## Phase 3 — Connect existing frontend to real APIs

Introduce frontend configuration, typed domain/API contracts, a transport layer, session provider and feature hooks outside route files. Use SDK-compatible SecureStore for credentials; keep server secrets out of Expo public environment variables. Implement refresh coordination, expiry/logout, offline/error/loading behavior and cancelable paginated requests.

Integrate one existing surface at a time: session/profile, events/gallery, feed/interactions, Discover, saved collections, notifications. Replace array-index identifiers with stable IDs. Add only missing auth/profile/newsletter/consent interfaces, using existing palette, font, cards and motion. Route with Expo Router, following repository guidance.

Resolve the six-image canvas/shader coupling with a measured bounded rendering approach. Preserve the glass dock and visible card geometry; do not simply map thousands of photographs into a single ScrollView. Use event-specific photo lists and actual server counts.

**Gate:** same UI against seeded APIs; state survives restart where appropriate; session refresh/logout and permission errors work; loading/offline states are usable; Android gallery scrolling/memory are measured; visual comparison passes. Do not retain demo notifications/data as an implicit fallback after real integration.

## Phase 4 — Google Drive synchronization and R2 delivery

Implement `apps/integrations`, durable job records and a separately runnable worker. Add secure authorized folder linking, paginated discovery, revision/hash comparison, derivative generation, R2 upload, resumable/idempotent sync, retries and administrator monitoring. Originals remain in Drive. Add authorized download endpoints with current access checks and bounded streams/short-lived delivery as appropriate.

**Gate:** new/modified/deleted/unchanged photos behave correctly; unchanged originals are not repeatedly downloaded; partial-list failures do not mass-delete; retries do not duplicate records; EXIF orientation and unsafe-image handling work; private derivatives/downloads cannot be accessed by unauthorized users. Verify an actual authorized test folder and R2 bucket; provider mocks alone do not complete this phase.

## Phase 5 — Consent, private inference and automatic indexing

Implement `apps/recognition`, consent/retention data and the separately deployed `face_recognition/app` service. Select licensed detector/embedder weights; record checksums, dimensions, preprocessing and versions. Implement private service authentication, bounded uploads and model readiness failures. Implement worker indexing for every face per photo, tied to source revision and model version, with stale-job protection and administrator failure visibility.

**Gate:** deterministic compatible embeddings, correct multiple-face indexing, PostgreSQL vector migrations, authenticated private calls, retry/reindex behavior, deletion/suppression persistence, and no sensitive payloads in logs. No random/stub vectors or unconditional sample matches. Use only authorized test photographs.

## Phase 6 — Event-specific Find My Photos

Add a themed event-specific consent and selfie flow. Django checks membership, event access, current consent and rate limits; FastAPI validates/detects/aligns/embeds; Django runs event/model-filtered pgvector search, thresholding and photo deduplication. Dispose of selfies/query embeddings and return authorized results through existing photo UI. Expose requester-scoped job status if processing must be asynchronous.

Calibrate and separately evaluate with approximately 200 consenting participants, including group photos, varied lighting/pose, and no-match samples. Report precision, recall, false positives/negatives, abstentions and latency; set acceptance thresholds using college risk requirements and held-out results.

**Gate:** no cross-event/private-photo leaks; no-match/multiple-face/low-quality cases work; withdrawals/deletion racing with searches are enforced; temporary-file and log retention checks pass; evaluation meets agreed criteria. Do not represent face similarity as verified identity.

## Phase 7 — Durable notifications and privacy completion

Implement recipient-scoped in-app notifications, device registration, delivery retries, invalid-token removal and preferences. Select one push path (Expo-to-FCM or direct FCM). Generate administrator-controlled publication notices and scoped interaction notices. Connect the existing drawer/island and validate deep links against current authorization.

Complete account deletion, embedding/result deletion, photo/event suppression, retention schedules and cleanup jobs across all domains. Draft privacy notice, face-processing notice, account-deletion instructions and an accurate data inventory for current platform/legal review.

**Gate:** delivery works on Android development/release builds, read state persists, invalid devices are cleaned, unrelated recipients cannot read notices, deleted/private targets stay protected, and end-to-end deletion/withdrawal jobs are verified. Legal/store declarations require review against the actual deployed behavior.

## Phase 8 — Load, reliability and deployment

Create repeatable load fixtures and scenarios for 20, 50, then 100 simultaneous active users: event/feed pagination, preview requests, profiles and interactions. Separately measure queued/concurrent AI searches and indexing contention. Collect p50/p95/p99 latency, errors, database query/pool behavior, memory, CPU, network/egress and cold starts; define acceptance budgets before running.

Optimize demonstrated bottlenecks with queries/indexes, derivatives/CDN policy, bounded workloads and rendering changes. Add Redis or paid/institution-provided capacity only when evidence supports it. Add Docker deployment definitions, scheduled sync/cleanup, health checks, backups/restoration drills, alerts and rollback procedures. Recheck current provider free-tier quotas and actual accounts before choosing hosts.

**Gate:** agreed latency/error/scrolling targets hold at 100 active users under a stated workload; AI has a separately measured concurrency limit; permissions/privacy regressions pass; provider costs/cold starts are documented; staging restoration and rollback work. No capacity claim from design estimates alone.

## Phase 9 — Google Play release

Verify Expo/EAS and Play account ownership, final package name, signing custody and production API endpoints. Add development-build configuration, production Firebase/native permissions and tested AAB configuration. Build and test a signed release artifact; prepare screenshots, icon, privacy URL, Data Safety/account-deletion declarations and required Play testing based on current official requirements.

**Gate:** signed release passes device/internal testing, production configuration/security checks, privacy/store review, monitoring and rollback readiness. Submission/public release requires the actual authorized accounts and deliberate release authorization; it is not performed by this planning milestone.

## External inputs needed at the relevant phase

- College domain/membership verification rules, Faculty approval process, and initial Administrator identities.
- Representative Android device/emulator and existing-screen baseline approval; ownership of committed Expo identifiers.
- Neon connection/extension access, authorized Drive folders/credentials, R2 configuration, and a chosen hosting account.
- Licensed model weights and a consented evaluation dataset; event-photo processing/withdrawal policy, retention periods and accuracy acceptance criteria.
- Firebase/Expo credentials and devices for real push; Play Console and signing access for final release.

Use local fixtures and explicit mock provider adapters for independent development, clearly labelled in development. Do not hardcode credentials or claim a provider/model/release integration verified without actual runs.
