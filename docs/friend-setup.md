# Clone and run PIXEL on Windows

The shared Neon database already contains the accounts, posts, saves, galleries and embeddings. Google Drive holds the originals. **The API and workers are local services, so an admin email/password alone is not enough to run another backend.**

## Prepare the GitHub repository once

Run **Prepare GitHub.bat** on the original computer. It creates a new folder under `.local/github-export/`, containing the frontend, backend, workers, source assets, lockfiles, launchers and documentation. It excludes Git histories, credentials, `.env`, local databases, temporary selfies, installed dependencies, generated builds and downloaded model weights. Its credential-pattern check is a safeguard; review the exported folder before publishing.

The current workspace has a Git repository inside `frontend/` only. Do not upload that folder alone, and do not add it to a new root repository as a gitlink/submodule. The clean export avoids that problem and preserves the upstream license and provenance without changing the working checkout.

Create an **empty private repository** in GitHub. From the **exported folder**, use GitHub Desktop to publish it, or CMD:

```cmd
git init -b main
git add .
git diff --cached --stat
git commit -m "Import complete PIXEL project"
git remote add origin https://github.com/YOUR-ACCOUNT/PIXEL.git
git push -u origin main
```

Replace the repository URL. Invite your friend as a collaborator. The preparation script does not create a repository, commit, or push.

Use this export for the **initial import only**. After publishing, both developers should work from clones of the new whole-project repository. You can clone it into a new `PIXEL-Team` folder and use the same private-file/setup steps below. Stop the original workspace's services and Expo processes before running the new clone on the same computer. Keep the original folder as a backup; do not overwrite your friend's later commits by repeatedly importing exports. Use normal `git pull`, commits and pushes in the team clone thereafter.

## Private files to give your trusted collaborator separately

Use a password manager's secure sharing or another private channel, never the repository, GitHub issues or chat logs:

| File from your computer | Where your friend places it, before setup |
| --- | --- |
| A private `backend.env` containing `DATABASE_URL`, `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from your `backend/.env` | `backend/.local/setup/backend.env` |
| `backend/.local/drive-oauth.json` | `backend/.local/setup/drive-oauth.json` |

The second file is the Pixel Google account's Drive authorization, not a normal app login. It grants Drive access; only share it with a trusted developer authorized to use that account's media. Alternatively, your friend can authorize the Pixel account themselves through `http://localhost:8000/admin/connect-drive/` after starting the backend. That requires access to the Pixel Google account. The OAuth client ID/secret in the private environment must be configured for the existing localhost callback.

Copy any intentionally shared feature settings, such as a calibrated `FACE_MATCH_THRESHOLD`, into that private file too. Do not share unrelated SMTP credentials, your Django signing secret, or your machine's worker ID. Setup also accepts a private environment-file copy for compatibility, but a minimal file is preferred.

A service-account key for independent media reads goes in `backend/.local/setup/service-account.json`. When configured, PIXEL uses it for previews, original downloads, video playback, gallery sync and face indexing, even when the admin's OAuth grant expires. Share the Posts, Moments, Spotlight, avatar storage and gallery folders with the service account as Viewer, including new folders that do not inherit access. Admin uploads and changes to My Drive still use the writable Google account authorization. Existing folder IDs remain in Neon.

Do not include your `.venv`, `node_modules`, SQLite snapshot, face-query files, model binaries or other `.local` files. Setup generates a new Django signing secret and a **distinct face-worker ID** on the friend's first installation. Existing account passwords still work. Never manually copy a machine's worker ID to another computer.

## Your friend's first installation



1. Install Git for Windows, **Node 24.3+** (Node 24.20 is the reference version used here), and **uv** from their official sites. Open a new CMD window after installation. Python 3.12 is installed/selected by uv during setup.
2. Clone the **whole** repository, then place the private files above:

```cmd
git clone https://github.com/YOUR-ACCOUNT/PIXEL.git
cd PIXEL
"Setup PIXEL.bat"
```

3. Double-click **Run PIXEL.bat**. Open `http://localhost:8081` and sign in with the existing admin account.

Setup installs dependencies from `backend/uv.lock` and `frontend/package-lock.json`, prepares machine-local settings, downloads/checks the pinned face models, and checks the backend/database schema. It preserves an existing local configuration and **does not run migrations or recreate/reset live data**. If Neon is missing migrations, the database owner must update it before others run the new code. No new admin account is needed.

If private configuration wasn't provided first, setup creates `backend/.env` with a fresh secret and tells your friend to add the Neon `DATABASE_URL` and Google configuration there before rerunning. They should never paste database passwords into source files.

Later updates: stop the local backend/Expo, `git pull`, rerun **Setup PIXEL.bat** if dependencies changed, and restart. Each clone keeps its own ignored configuration.

## Phone testing

Use **Run PIXEL Phone.bat** for the QR code on port 8082. Your friend must use **their computer's** Wi-Fi address, not the original computer's address. Keep phone and PC on the same Wi-Fi. If the phone cannot open the API health link printed by the launcher, use **Enable PIXEL Phone Access.bat** and approve the Windows administrator prompt. That rule allows only this Python API on TCP 8001 from the local subnet. A normal home Wi-Fi connection must allow devices to reach each other.

Google sign-in in Expo Go still requires a proper development/app build; the admin email/password can be used for local Expo Go testing.

## Shared data and worker ownership

Both local backends use the **same live data**. Editing, publishing, deleting and moderation actions are real changes visible to the other developer; use drafts or a separate Neon development branch for experiments.

Selfie uploads are intentionally local temporary files. Each machine has its own worker lease, readiness and job queue namespace, so a worker on one PC does not consume another PC's upload. Gallery embeddings stay shared in pgvector. A user can still have only one active face search across the shared database; finish or cancel it on the machine where it was started before starting another under the same account.

For genuinely "clone and run frontend only", deploy the API, Drive authorization and workers once to a shared host, then give developers its public API URL. Neon being online does not itself host Django or the recognition worker. That shared backend deployment is not performed by these scripts.

Official installers: https://git-scm.com/downloads/win · https://nodejs.org/en/download · https://docs.astral.sh/uv/getting-started/installation/

## Verification boundary

Configuration and clean-source export were exercised in temporary new-clone workspaces, including credential exclusion and preservation of existing settings. Backend regression and isolated PostgreSQL face-worker tests cover host ownership. The full dependency installer was not run on a second physical Windows computer; its final provider/device checks still need to happen on your friend's machine after private access is supplied.
