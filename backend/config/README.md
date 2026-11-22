# Django configuration

`settings.py` loads environment-based development/production configuration, with URL routing, WSGI and an OAuth-query redaction filter. `.env.example` documents supported variables; actual credentials stay in the ignored `.env`.

Load secrets from environment/hosting secret storage. Production must fail on missing required secrets, disable debug, restrict hosts and origins, and configure HTTPS/proxy behavior explicitly. Configure database connection limits for the chosen Neon deployment; choose transaction-compatible pooling and a migration connection deliberately.

SQLite is development-only. Production requires PostgreSQL/Neon and configured SMTP, strong secrets and HTTPS. Authentication starts locally using the backend README; production static assets, reverse-proxy headers, shared throttle cache and deployment validation still need the hosting phase.
