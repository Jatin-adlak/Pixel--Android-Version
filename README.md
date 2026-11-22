# PIXEL

College photography and social networking Android app, managed by the college social media club.

## Current milestone

The app has college authentication, profiles, persistent social actions, administrator publishing, two-way Drive event galleries, Moments, Spotlight and private event face search. Metadata and typed face embeddings now use **live Neon PostgreSQL with pgvector**; originals remain in Google Drive. The API, sync worker and recognition worker still run locally. See [live database setup and migration verification](docs/live-database.md), [authentication setup](docs/authentication.md), and the [face-search pipeline](face_recognition/README.md). Password reset remains deferred by request.

**Preserve the existing UI.** Reuse its layout, typography, colours, imagery treatments, animations, and components. New screens must follow the existing theme.

## One-click Windows launcher

**New computer or collaborator:** see [clone-and-run setup](docs/friend-setup.md). Install Git, Node and uv once, provide private configuration outside Git, run **Setup PIXEL.bat**, then **Run PIXEL.bat**. To prepare all source files for a new private GitHub repository without copying the nested frontend Git checkout or secrets, run **Prepare GitHub.bat**.

Double-click **Run PIXEL.bat** in the main folder. It starts the backend, Drive sync, face worker and frontend in the background, waits for readiness, and opens `http://localhost:8081` in your default browser. Existing PIXEL services are reused. Another program occupying port 8000 or 8081 produces an error without being stopped.

The launcher uses the existing backend environment, installed frontend dependencies and configured Neon database; it does not install packages or run database migrations. Internet access is needed for Neon and Drive. Startup logs are in `backend/.local/`, including `frontend.out.log` and `frontend.err.log`. This launcher does not use Codex or screen capture.

For Expo Go, double-click **Run PIXEL Phone.bat**. Its CMD window stays open with the QR code. It detects the computer's LAN IPv4 address, starts a separate phone API on that address at port 8001, starts/reuses the workers, and runs Expo Go on port 8082. The phone and computer must use the same Wi-Fi; use Expo Go compatible with SDK 58. If needed, allow Node/Python on the Windows private network. Google OAuth can require a development build rather than Expo Go.

Phone mode sets the API and media URLs only for its own processes, leaving saved `.env` files and the web launcher unchanged. For multiple network adapters, an explicit address can be passed in CMD: `"Run PIXEL Phone.bat" 192.168.1.10`. The BAT files run in CMD; a local PowerShell helper handles network detection and background services. No PowerShell commands need to be typed manually. Phone API logs are `backend/.local/phone-backend.*.log`.

## Workspace

```text
Pixel-App/
  frontend/                 Existing Expo / React Native / TypeScript repository
  backend/
    config/                 Django settings, URLs and deployment entry point
    apps/                   Accounts, community content, administration and durable face search
    tests/                  Authentication, content, Drive, privacy and pgvector regressions
  face_recognition/
    app/                    Private CPU detection, alignment and embedding engine
    models/                 Model provenance and licensing boundary
    tests/                  Inference quality and evaluation boundary
  docs/
    requirements.md         Original uploaded development brief
    repository-review.md    What exists, what is missing, and integration risks
    architecture.md         Service boundaries, permissions, and data ownership
    development-plan.md     Ordered phases with verification gates
    validation.md           Checks performed and remaining verification
    authentication.md       Current auth implementation, setup and API reference
```

Read the [repository review](docs/repository-review.md), [architecture](docs/architecture.md), and [implementation phases](docs/development-plan.md) before implementing features.

## Frontend commands

From this directory, after dependency installation:

```powershell
cd frontend
npm ci
npm exec -- tsc --noEmit
npm run lint
npm run start
```

Use the committed lockfile. The repository currently declares Expo SDK 58. Follow `frontend/AGENTS.md`, including checking matching Expo documentation before touching native APIs. Do not run `reset-project`: it replaces the existing application with starter code.

Start Django, event-gallery sync and the face worker with `scripts/start-backend.ps1`. Feed, gallery, moments, Spotlight and social activity use the backend. The themed administrator workspace is at `/admin` in the app. See [content and Drive setup](docs/community-backend.md) and [event face search](face_recognition/README.md) for setup and verification status. Face search is implemented locally; college-photo accuracy calibration and device checks are still pending.

## Source provenance

- Upstream: https://github.com/kanishkk52/Pixel_Android
- Reviewed commit: `586e32daccf0619efdf16434087771d48b8c895b`
- The original development workspace preserves the upstream Git history in `frontend/`. The clean GitHub export keeps its license and source provenance while excluding that nested Git history.
- In the original workspace, only `frontend/` is a Git checkout. In the prepared whole-project export, `frontend/` is a normal source directory so the new root repository contains every service.
- The launchers and export helper do not commit, push, deploy or release code. The backend requires private configuration to access the Pixel Google Drive account.

## Product constraints

Exactly three roles: Administrator, Faculty, Student. Only Administrators manage published application content. Authenticated Faculty and Students can manage their own profiles, interact where permitted, and search authorized event photographs with consent.

Target approximately 4,000 accounts and 100 simultaneously active users. Start with a modular Django application, a separate inference service, and a worker. Add infrastructure in response to measurements. Free-tier deployment can experience cold starts and resource limits; availability and cost must be measured before release.
