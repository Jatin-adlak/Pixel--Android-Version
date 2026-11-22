# PIXEL Django backend

Authentication, profiles, content, interactions, Drive galleries, administration and local face recognition are implemented. The active metadata and vector database is now Neon PostgreSQL. See [live database setup](../docs/live-database.md) for migration evidence, private connection configuration, checks and backups, and [authentication setup](../docs/authentication.md) for Google/email configuration.

```text
backend/
  config/       Django settings, URLs, WSGI and redacted logging
  apps/         Account services, permissions, onboarding and initial video records
  tests/        Authentication, permissions, privacy and provider contract tests
```

Django owns the database schema and migrations, authentication, exactly three roles, Django Admin, content publication, event access, interactions, consent, and retention. Django also owns durable Drive sync/indexing/search job records and authorized pgvector queries.

Background sync and indexing run in a separate worker process using this backend's domain services. FastAPI inference remains under `../face_recognition/`; it must not become a second public API or migration authority.

## Run locally

```powershell
cd C:\Users\yasha\Desktop\Pixel-App\backend
uv sync --locked
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

The API runs at `http://localhost:8000/api/v1/`; Django Admin is at `http://localhost:8000/admin/`. This workspace already has a generated secret in the ignored `.env`. On a new installation, copy `.env.example` and replace its example secret with a randomly generated value. Never overwrite an existing `.env` when following setup instructions.

The local main administrator is **Pixel / pixel.club@sait.ac.in**. Its generated initial password is in `.local/admin-initial-password.txt`, ignored by Git. After your first login, choose a username, fill profile details and change the password through Django Admin. Store it securely, then remove the initial credential file when no longer needed.

On a fresh database, `manage.py bootstrap_admin` prompts for a password. Alternatively, `manage.py bootstrap_admin --password-file .local/admin-initial-password.txt` generates it into a new local file. The command never overwrites an existing account or file. Use `manage.py changepassword pixel.club@sait.ac.in` to change existing credentials.

## Checks

```powershell
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.venv\Scripts\python.exe manage.py test tests
.venv\Scripts\python.exe -m ruff check apps config tests
```

Local SQLite is allowed only with `DJANGO_DEBUG=true`. Production requires PostgreSQL/Neon and configured SMTP. Development verification emails are written to `.local/emails/`; they are not delivered to the actual college inbox. Password reset remains disabled per request. Run `manage.py cleanup_auth` daily to remove expired authentication artifacts and audit logs older than 90 days.

The small initial Moments video record is in `apps/accounts` for this milestone; move it into the content application using a data-preserving migration when that application is introduced. Do not reset existing databases or migrations.
