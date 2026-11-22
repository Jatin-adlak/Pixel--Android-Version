# Authentication storage and phone testing

- Web refresh credentials remain in the backend's HttpOnly cookie. The short-lived OAuth verifier uses tab-scoped sessionStorage.
- Native refresh tokens and OAuth verifiers use `expo-secure-store` with the PIXEL-specific `com.pixel.credentials.v2` service for both reads and writes. Old default-service values are migrated after a verified encrypted write.
- An unreadable legacy token returns to sign-in instead of blocking app initialization. Keystore write errors get one bounded retry, clearing only the affected PIXEL item. The app never resets the shared Android keystore.
- Normal app and development builds require encrypted storage. A failed write prevents the new session from being published.
- Only `__DEV__` inside actual Expo Go permits a memory-only session when encrypted writes fail. A visible notice explains that the login may need to be repeated after restarting. No credential is written to plaintext preferences, AsyncStorage, files or logs by this fallback.

Google OAuth uses the `pixelmobile://auth/callback` scheme. Expo Go does not own that scheme and cannot run this OAuth flow. The app explains this before creating a verifier or launching Google. Use email/password for Expo Go testing. Google login requires an app/development build plus a reachable HTTPS backend callback registered on the Google OAuth client; the LAN-only phone launcher does not supply that hosted callback.

Run `npm run test:auth` to exercise scoped storage, legacy migration, corrupt reads, bounded recovery, fail-closed behavior, read-back verification, explicit memory fallback, restart behavior, and logout clearing with a fake adapter. These tests do not access real device credentials. Android keystore behavior must still be confirmed on the affected phone.
