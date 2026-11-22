# Existing repository review

Reviewed 17 November 2026 at upstream commit `586e32daccf0619efdf16434087771d48b8c895b`. This is a source review; Android runtime behavior has not been validated on a device.

## Entry points and navigation

| File | Existing responsibility | Integration notes |
| --- | --- | --- |
| `frontend/src/app/_layout.tsx` | Router Stack, font loading, splash handling, gesture and safe-area providers, brand intro | Preserve the brand intro and providers. Introduce session gating around the existing app later. |
| `frontend/src/app/index.tsx` | Re-exports `src/pixel/PixelApp.tsx` | This is the active PIXEL entry point. |
| `frontend/src/pixel/PixelApp.tsx` | Feed, Gallery, Moments, Discover, Profile; collection/photo, event, and comments modals | Active tabs are local React state, not individual Expo Router routes. Preserve visuals when adding routes and deep links. |
| `frontend/src/pixel/data.ts` | Six albums, palette, tab definitions, photo sizes | Static demo data and Unsplash images; numeric array indexes currently serve as identifiers. |
| `frontend/src/pixel/GlassScene.tsx` | Skia image composition and glass dock rendering | Explicitly loads six images and imports demo albums directly. |
| `frontend/src/pixel/glassShader.ts` | Glass refraction shader | Six shader image inputs and a six-card uniform array. Large-gallery support requires a bounded rendering window or decoupled dock composition. |
| `frontend/src/pixel/Notifications.tsx` | Drawer, animated notification island, unread state, swipe dismissal, appearance switches | In-memory notifications; `DEMO_NOTIFICATIONS = true` generates a timed demo event and a preview reply. |
| `frontend/src/pixel/BrandIntro.tsx` | Existing animated introduction | Reuse. |
| `frontend/src/components/PixelApp.tsx` | Re-export of active implementation | Compatibility wrapper, not a second full implementation. |
| `frontend/src/components/GalleryScreen.tsx`, `GlassPreview.tsx` | Alternative gallery and glass examples | No importing references found in the reviewed source; do not build new features in these by mistake. Keep pending explicit cleanup. |
| `frontend/src/app/explore.tsx` | Expo starter Explore route | Remains routable but is not the active PIXEL Discover tab. |
| `frontend/src/app/layout backupt.txt` | Layout backup text file | Preserve during audit; determine intended removal later. |

## Existing functionality and gaps

| Area | Existing work to reuse | Missing behavior |
| --- | --- | --- |
| Gallery | Search/category UI, collection modal, photo viewer, previous/next navigation | Published events API, real per-event photo membership, pagination, access checks, download authorization |
| Feed | Cards, like/save buttons, comments modal, native Share call | Server persistence, administrator publication workflow, moderation, reliable counts, post IDs |
| Profile | Avatar placeholder, saved collections, follower/following counters | Authentication, actual profile, editing, connections, account deletion |
| Discover / spotlight | Event cards and event information modal | Admin-managed event/spotlight records and visibility |
| Moments | Designed empty state | Videos are not implemented; clarify video scope before expanding beyond the brief |
| Notifications | Rich presentation and local read/dismiss interactions | Database records, push registration, delivery, permission handling, durable read state, real routing |
| Theme | Charcoal/ivory appearance, blue accents, typography, glass effect | Preferences are local component state; persistence can be added without redesign |
| Authentication / roles | None found | Registration, verification, login, refresh/logout, SecureStore, exactly three roles, backend permission tests |
| API layer | None found; no `fetch` or Axios integration in app source | Configured API base URL, typed DTOs, errors, timeouts, cancellation, refresh handling, pagination |
| Backend / infrastructure | None in upstream repository | Django, DRF, database, admin, workers, private inference, storage and provider integration, CI |
| Find My Photos | None found | Consent UI, capture/upload, indexing, model validation, event-scoped vector search and deletion |
| Newsletters / announcements | None found | Models, admin publishing, read/download interfaces consistent with the theme |

## Important implementation risks

1. **Collection data is demonstrative.** `CollectionModal` rearranges all six album covers into each collection and labels the result as six photos. Backend integration must introduce distinct Event and Photograph objects, with durable IDs; replacing one array URL is insufficient.
2. **Renderer is bounded to six demo images.** Both Skia loading and shader inputs assume six images. The active screen uses an `Animated.ScrollView` and maps all slots. An alternative `GalleryScreen` has a `FlatList`, but it is not connected to the active entry. Profile on a representative Android device before choosing a visually equivalent rendering strategy.
3. **Interactions reset with the app.** Likes, bookmarks, comments, notification state, and appearance are component state. Retain visual behavior, replacing data ownership through hooks/adapters after API contracts are tested.
4. **Navigation needs integration work.** Modal and tab targets are array indexes. Push routing and photo-search results must use validated IDs and route parameters. The horizontal swipe detector is attached to an empty sibling View in the current JSX; this needs device verification before claiming it works.
5. **Admin authority is absent.** Hiding mobile controls is insufficient. Django must filter querysets and enforce object/action permissions. DRF staff status alone must not create an extra content-publishing role.
6. **Prototype and real notifications must be separated.** Disable demo generation when real notifications are connected; retain the existing drawer/island presentation.
7. **Native capabilities are missing.** SecureStore and Expo Notifications are not declared dependencies. Camera/image selection and authorized downloads also need SDK-compatible modules and native permission configuration in later phases.
8. **Release configuration is partial.** EAS preview APK and production app-bundle profiles exist. Android package is `com.jatinadlak.pixel`; Expo owner is `kanishk_kukreja`, with a committed EAS project ID. These identifiers are not secrets, but ownership/signing access must be verified before release. There is no development-build profile or Firebase integration in the reviewed config.

## Dependency and tooling inventory

Declared versions include Expo `~58.0.25`, React Native `0.88.1`, React `19.3.0`, Expo Router `~58.0.31`, Skia `2.14.0`, Reanimated `4.7.1`, Gesture Handler `~3.3.0`, and TypeScript `~6.0.3`. A package lock exists. These are repository declarations, not a claim that every version is registry-available or SDK-compatible.

Scripts: `start`, `android`, `ios`, `web`, `lint`, and a destructive-for-this-project starter reset utility. No project-owned automated test suite, ESLint config, backend, Docker setup, or CI workflow was found among tracked files. Strict TypeScript is enabled. See [validation](validation.md) for actual command results.

The current source and asset files have been preserved. No UI component was added or redesigned during this milestone.
