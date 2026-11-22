# UI and workflow verification — 21 November 2026

The existing blue/ivory offset buttons, charcoal cards, Nohemi brand text, colours and liquid-glass dock are retained. No phone, browser window or desktop UI was controlled during this work.

## Implemented in this change

| Area | Behaviour |
| --- | --- |
| Overlays | Shared full-screen modal window and safe-area boundary for Admin Studio, inbox, comments, photo viewer, profile editor and other content overlays. Headers use the same top origin as the main activity. Physical Android confirmation of the duplicate-header fix remains required. |
| Back | Visible back buttons were removed at the user’s request. Android system Back returns from subpages and routes within modals; Escape dismisses the topmost desktop overlay. |
| Side navigation | Desktop/tablet web views (768 px and wider) retain the side menu. Phones and narrow web views use the existing glass dock, with no hamburger or side-swipe trigger. |
| Profile settings | Profile header settings replaces logout. Appearance and liquid-glass controls moved out of the inbox; sign-out has confirmation, failure feedback and retry. Preferences persist when local device storage is available; a broken Expo Go keystore leaves them session-only. |
| Posts | Select 1–10 images, preview, remove or move a selected image earlier, and publish or save a draft. Editing can replace the complete image set. Caption-only edits preserve the existing set. Originals stay in the configured Posts Drive folder. |
| Carousel | Ordered feed paging, compact arrows and image count; opening a photo retains its position. Full-screen swipe/arrow navigation and download select the active image. Likes/comments/saves/sharing belong to the parent post. Legacy single-image posts remain supported. |
| Publish failures | Server enforces post-only multi-image uploads, ten-image limit and total 100 MB limit. Failed batches/replacements do not save partial metadata; cleanup of new Drive files is attempted. A separate cover does not count as an eleventh image. Existing saves remain attached when images are replaced. |
| Face search | Availability is checked before selecting/uploading. Separate consent remains mandatory. Progress, cancellation, filtered results and Show all remain connected to the normal photo viewer and actions. An active owned search can be resumed after a lost upload response. Timeouts are distinguished from network failures. |
| Phone sharing | The phone launcher supplies a LAN web URL instead of sharing localhost links. These development links work only on the same network. Public sharing requires the hosted web URL. |

## Automated checks

- Final full backend regression run: 74 tests, 73 passed and one PostgreSQL-only skip in the offline run. All eight carousel cases also passed on a separate PostgreSQL test database; the owned face-search recovery case passed on PostgreSQL separately.
- Additional tests cover ordered ten-image multipart publishing, one parent save, download bounds, draft revocation, authorization, injected Drive-ID rejection, caption edits, failed batches, replacement rollback and separate covers.
- PostgreSQL test runs use a separate `test_neondb`, with mocked Drive transport. They do not upload test images to the real Drive folders or modify live members/posts.
- The additive `community.0009_publication_post_media` migration is applied to live Neon. Existing single-image posts need no data conversion.
- Existing regression coverage checks follow request → recipient inbox → acceptance/decline → access/revocation; persistent social counts; reply ownership and moderation; private saved pictures; mandatory Pixel follow; event/Spotlight separation; and Drive reconciliation failures.
- Ten authentication storage tests, TypeScript, Expo lint, Ruff, migration consistency and final Android/web exports passed. Build success does not verify touch gestures or native modal geometry.

## Phone acceptance pass

Close the Expo CMD window. Run **Stop PIXEL Backend.bat**, then **Run PIXEL Phone.bat**, and scan the new QR code. The API uses `--noreload`, so merely reloading Expo leaves old backend code running.

1. Open Admin Studio and the inbox: confirm one top header, no stacking, no content covering it. Check both light and dark appearances.
2. Open settings from Profile; switch appearance and glass; close and reopen. Open/dismiss the side menu using buttons, edge swipe and Android Back.
3. Publish a draft with ten photos, reorder/remove/reselect, then publish. Swipe horizontally through all ten; open an intermediate photo and use both arrows/swipes. Download that photo and verify the original is the correct file. Save/like/comment once and refresh to confirm persistence.
4. Send a follow request between two accounts. Accept or decline in the recipient inbox. Confirm saved-picture access appears only after acceptance and disappears after unfollow/removal. Other profiles must not expose follower/following lists.
5. Open an event and use Find yourself with your own clear, consented selfie. Exercise cancel, retry, progress, no-match, matched results, save, download, previous/next and Show all. Test loss/recovery of Wi-Fi while processing.
6. Check Spotlight details and its optional form link; gallery results must still be completed-event photos. Check header/back behaviour from a searched profile.

## Outstanding external verification

The screenshot alone does not establish the cause of the phone's face-upload network failure. The new preflight, recovery and timeout handling improve diagnosis; an actual phone upload remains required. The indexed matching engine is not a guarantee of identification accuracy: a consented real-selfie check and a labelled accuracy evaluation are still outstanding.

Google sign-in needs a development/application build and a public HTTPS callback configuration; Expo Go cannot complete this app's custom callback scheme. The application API and workers still require hosting for use independently of the computer, even though Neon and originals in Drive are online. Public share links need that hosted web address. Push alerts and direct messaging are not implied by the existing follow-request inbox and are not implemented here.

## Follow-up: header, outside dismissal and local cookie authentication

The wordmark was lowered slightly to align with the logo. Outside-image letterboxing, popup backdrops and available margins around bounded subpages dismiss the opened view; taps on content and controls remain active. Full-screen phone subpages retain system Back navigation.

Browser previews now use the page’s local hostname for local development APIs, while Expo Go retains the LAN hostname. The phone API listens on both loopback and Wi-Fi so localhost previews can send same-site CSRF/refresh cookies. CSRF rejection has an explicit error code; the client obtains a fresh token and retries once. Persistent rejection and ordinary authorization failures are not bypassed. Both APIs were restarted.

Verification: 21 backend authentication tests and four client origin/retry tests passed; TypeScript, Expo lint and Ruff passed. Fresh local browser sessions on ports 8000 and 8001 received CSRF cookies and reached the expected unauthenticated 401 refresh response; a foreign Origin remained rejected with 403. Physical touch/gesture and wordmark alignment confirmation still requires a device check.

## Follow-up: saved grids, photo frames and Google entry

Saved posts and moments now use square, three-column thumbnail grids with uniform 8-point gaps and the existing blue offset/charcoal card frames. Opening a post shows its author, uncropped carousel, full caption and social controls. Opening a moment uses the full-screen video player. Unsave updates the owner’s grid and count immediately. Public profile visibility rules are unchanged.

Post frames use the widest original width and tallest original height, with a shared proportional scale to fit the available screen width. Every image is centered without cropping or distortion; unused areas are black in dark appearance and white in light appearance. Small originals are not enlarged. `image_dimensions` stores display-oriented dimensions only; originals remain unmodified in Drive. Migration `community.0010_publication_image_dimensions` is applied to Neon, and metadata was filled for both existing posts. Legacy/missing metadata can fall back to preview dimensions.

One audio preference now covers the Moments feed and saved-moment player throughout the current signed-in app session. New clips start with that same mute setting instead of resetting on every scroll.

The login page’s Google button is no longer disabled by the manual form or its checkboxes. Its own consent dialog clearly labels the Google flow, preserves explicit policy acceptance, allows reading the policies and reports errors. The existing Expo Go/custom-callback limitation remains; this UI change does not claim to implement native Google OAuth in Expo Go.

Eleven carousel/dimension cases passed on isolated PostgreSQL, and eighteen client storage/origin/frame tests passed. Final Android and web exports, TypeScript, Expo lint and Ruff passed. Visual and audio acceptance on a physical phone remains a separate check.

## 22 November: profile editor and header Home action

The embedded profile editor now follows the selected appearance for its page, inputs, labels and supporting text. It uses the existing permanent header rather than repeating the Pixel brand inside the form. The existing or newly selected profile photo appears in an 84-point circular preview beside a compact change control, above the fields. The scroll content reserves an additional 112 points plus safe-area padding below Cancel, keeping the final controls clear of the glass dock.

The logo and wordmark are one accessible Home target. A Home request resets the main feed and dismisses open overlays, including the global inbox, editor and nested content viewers. Shared authentication form defaults remain unchanged for other screens that do not opt into the selected appearance.
