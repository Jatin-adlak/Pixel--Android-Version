# Content, social features and Drive

Implemented locally on 18 November 2026. This supersedes the sample-data descriptions in the earlier repository review. Production deployment and device verification are separate work.

## Code map

| Location | Responsibility |
| --- | --- |
| `backend/apps/community/models.py` | Events, publications, reactions, comments/replies, follows, profile images, Drive folders |
| `backend/apps/community/queries.py`, `content_views.py`, `profile_views.py` | Member APIs, publication visibility, social actions, saved-content privacy |
| `backend/apps/community/management_api.py`, `spotlight_api.py` | Administrator CRUD, moderation, gallery uploads and separate announcements |
| `backend/apps/community/synchronization.py` | Event-folder polling, leases, retry and backoff |
| `backend/apps/community/media.py` | Expiring media links, private Drive previews, range delivery, original downloads |
| `backend/apps/community/drive.py` | Drive uploads and event-folder discovery/reconciliation |
| `backend/apps/community/drive_oauth.py` | Administrator-initiated Google authorization and server-only refresh credentials |
| `backend/apps/community/forms.py`, `admin.py` | Administrator publishing, file/cover uploads, Drive selection and gallery sync |
| `backend/apps/community/signals.py` | Required accepted follow to the main Pixel administrator |
| `frontend/src/pixel/PixelShell.tsx` | Existing palette, logo, typography, glass dock, navigation and account entry points |
| `frontend/src/community/ContentScreen.tsx` | API-driven feed, events, saved sections, profiles, inline search, discussions and inbox |
| `frontend/src/community/PrivatePictures.tsx` | Animated glass restriction without retrieving private pictures |
| `frontend/src/community/PhotoViewer.tsx` | Medium previews, original download, save, arrow and swipe navigation |
| `frontend/src/admin/` | Themed administrator dashboard, editors, members and moderation |
| `frontend/src/pixel/MomentsScreen.tsx` | Paged video playback, cover loading and video actions |
| `backend/tests/test_community.py`, `test_drive.py` | Persistence, privacy, moderation, provider and login regressions |

## Administration

1. Open `http://localhost:8081/admin` for the themed administrator workspace. The legacy Django administrator remains at `http://localhost:8000/admin/`. The administrator email is `pixel.club@sait.ac.in`; use the existing private initial-password file if the password has not been changed.
2. Visit `/admin/connect-drive/` while signed in. Choose the Pixel Google account and authorize Drive access. This reuses the backend's existing Google client and registered `/api/v1/auth/google/callback/` URI. Refresh credentials stay in ignored `backend/.local/drive-oauth.json`.
3. The supplied service account can already read the configured Posts and Moments folders. Direct uploads into My Drive use the Pixel account's OAuth credentials. No API key or service-account secret belongs in the frontend.
4. Gallery contains completed-event folders. Title, category, description, venue, dates, cover and an existing Drive folder are collected in the gallery editor. Connecting that folder is mandatory. Spotlight has its own model and editor for upcoming announcements, dates, venue, cover and optional form URL; it does not create a gallery folder. Single-day and multi-day dates are supported.
5. In Publications, select Post, Moment or Gallery photograph, the event, title/caption/tag and media. Upload an original, select an existing Drive file, or supply delivery URLs. Optional cover uploads override the generated Drive thumbnail. New content remains unpublished until its Published checkbox is selected. Supported original uploads: JPEG, PNG, WebP and MP4, up to 100 MB.
6. Start the backend and event worker with `scripts/start-backend.ps1`. Linked event folders reconcile automatically, normally every 60 seconds, with database leases and retry/backoff. Only a complete successful listing reconciles missing files. Direct Drive additions, replacements, renames and removals update gallery media. PIXEL gallery uploads, renames, moves, replacements and removals update Drive; removed originals go to Drive Trash. This two-way reconciliation applies to event media only, preserving social records across temporary removals. Manual sync is also available in Admin.

The database stores metadata, file identifiers and social activity; media bytes are streamed from Drive. An interrupted upload or database save may leave an unreferenced Drive file; automatic orphan cleanup/resumable job recovery is not implemented. Thumbnails use Drive's generated derivatives (800 px feed covers and 1600 px photo previews), while downloads stream original bytes. Video requests forward a single byte range. This is progressive delivery, not adaptive HLS transcoding or a guaranteed ten-second buffer on every device/network.

## API families

- `GET /api/v1/feed/?kind=post|photo|moment&event_id=...&tag=...`
- `GET /api/v1/events/?q=...` and `/events/<uuid>/` for completed-event galleries
- `GET /api/v1/spotlights/` and `/spotlights/<uuid>/` for announcements
- Administrator CRUD at `/api/v1/management/events|publications|spotlights|members|comments/`, plus `/management/dashboard/`, `/management/storage/`, event `/sync/` and `/photos/`
- `GET /api/v1/publications/<uuid>/` and `/download/`
- `PUT` / `DELETE /api/v1/publications/<uuid>/like|save/` (idempotent)
- `GET` / `POST /api/v1/publications/<uuid>/comments/`, with optional `parent_id`
- `DELETE /api/v1/comments/<id>/`; `PUT` the same URL to like; `DELETE /comments/<id>/like/` to unlike
- `GET /api/v1/members/<username>/` and `/saved/?kind=post|moment|photo`
- `PUT` / `DELETE /api/v1/members/<username>/follow/`
- `GET /api/v1/connections/?kind=requests|followers|following` (current user only)
- `PUT /api/v1/connections/<id>/` to accept an incoming request; `DELETE` to decline/remove
- `PUT /api/v1/me/avatar/` supports profile image upload (the app uses the image picker); username changes use the existing unique-username endpoint

Published content requires an authenticated, onboarded college member. Draft/archived/unavailable records are excluded. Comment deletion is restricted to its author or an Administrator; deleting a parent also removes its replies. Saves and likes are database records with uniqueness constraints and survive refresh. Saved posts and moments are visible to other signed-in members. Saved photographs require an accepted follow; removing that follow immediately removes access. Nobody can enumerate another member's follower/following list. Email and administrative flags remain private.

## Validation and remaining live checks

The two supplied Drive folders returned HTTP 200 using the service account. Automated tests cover reactions, nested comments, moderation, follow requests/privacy, mandatory Pixel follows, username uniqueness, revoked media visibility, partial sync failures, OAuth state/session/replay checks and CSRF-protected Admin login.

Pixel OAuth is connected locally. The live event folder synchronized 518 photographs. Original-byte checksum and size matched Drive, and HTTP 206 byte-range delivery was verified with `manage.py check_media_delivery`. The existing published post now appears on Home after repairing its internal availability flag; multipart publication regression tests prevent that flag from being incorrectly cleared. All 49 backend tests, migration checks, Ruff, frontend TypeScript and lint passed. Browser checks verified the Home feed, borderless stable search, profile restrictions, equal-width saved tabs, photo arrows and horizontal swipes. Live destructive Drive mutations were not performed for testing.

Android/native downloads, keyboard, scrolling, video playback/buffering and accessibility still need device checks. Push notifications, adaptive streaming and PostgreSQL deployment remain outside this implementation. Event-scoped local face search is now implemented; see [pipeline setup and verification](../face_recognition/README.md). Its held-out accuracy and real-selfie/device checks remain pending. Google Drive progressive byte-range delivery is implemented; it cannot guarantee a fixed buffer duration on every connection.

Admin login uses `Referrer-Policy: same-origin`; `no-referrer` can cause ordinary form POSTs to send `Origin: null`. CSRF remains enabled. Reload an old login form after a backend policy change. Stop stale copies of Django before restarting: multiple local instances were found serving the same port during verification.
