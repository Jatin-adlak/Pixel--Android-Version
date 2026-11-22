# PIXEL — Complete Project Context & Development Prompt

## 1. Project Overview

I am developing **PIXEL**, a college photography and social networking Android application using Expo React Native, Django REST Framework, FastAPI, and PostgreSQL.

The application will support approximately **4,000 registered users**, but the current requirement is to handle **up to 100 simultaneously active users smoothly**.

The application will provide college event galleries, student and faculty profiles, social interactions, photography spotlights, newsletters, notifications, and AI-powered face recognition to help users find their photographs.

**Important:** All content published on PIXEL will be created, uploaded, edited, approved, published, and deleted exclusively by the Administrator. Faculty and Students will primarily consume and interact with administrator-managed content.

My goal is to complete development using free-tier services wherever possible and eventually publish the application on Google Play.

## 2. Technology Stack

**Android Frontend**
- Expo + React Native + TypeScript
- Expo Router
- Expo SecureStore
- Expo Notifications
- Expo EAS Build

**Main Backend**
- Python Django
- Django REST Framework
- JWT authentication
- Role-based permissions

**AI Backend**
- Python FastAPI
- ONNX Runtime
- Face detection and alignment
- ArcFace/InsightFace-compatible face embeddings, subject to model licensing
- Vector similarity search

**Database**
- Neon PostgreSQL
- pgvector for face embeddings

**Storage and Delivery**
- Google Drive for original event photographs
- Google Drive API for automatic synchronization
- Cloudflare R2 for thumbnails and previews
- Cloudflare CDN for image delivery

**Additional Services**
- Firebase Cloud Messaging for push notifications
- Redis for caching and background processing where necessary
- GitHub and GitHub Actions
- Docker
- Free-tier or low-cost hosting during development

## 3. Existing Project

I already have an Expo React Native project called PIXEL.

GitHub repository:
https://github.com/kanishkk52/Pixel_Android

Inspect the existing repository before making changes.

Identify existing screens, components, navigation, dependencies, mock data, and API integrations.

Reuse completed code wherever possible instead of rebuilding the application unnecessarily.

## 4. User Roles and Permissions

PIXEL has **exactly three roles**:

### Administrator

The Administrator has complete control over the application's content and management.

Responsibilities:
- Create, update, publish, and delete college events.
- Upload, organize, and remove event photographs.
- Connect and manage Google Drive event folders.
- Create and manage posts and feed content.
- Publish photography spotlights.
- Upload and manage newsletters.
- Create and publish college announcements.
- Manage users, accounts, and permissions.
- Manage application notifications and announcements.
- Moderate comments and user interactions.
- Control event visibility and photograph access.
- Monitor AI indexing, failed jobs, and application activity.
- Manage content displayed throughout the application.

### Faculty

Faculty can:
- Register and log in.
- View and edit their own profile information.
- Browse published events and photographs.
- View administrator-published posts, spotlights, and newsletters.
- Like, comment, and interact where permitted.
- Connect with other users where supported.
- Use Find My Photos with appropriate consent.
- Download photographs where authorized.
- Receive notifications.

Faculty **cannot create, upload, edit, publish, or delete application content**.

### Student

Students can:
- Register and log in.
- View and edit their own profile information.
- Browse published events and photographs.
- View administrator-published posts, spotlights, and newsletters.
- Like, comment, and interact where permitted.
- Connect with other users where supported.
- Use Find My Photos with appropriate consent.
- Download photographs where authorized.
- Receive notifications.

Students **cannot create, upload, edit, publish, or delete application content**.

**Access-control rule:** Only Administrators may manage published application content. Student and Faculty profile updates, comments, likes, connections, and selfie-search requests are permitted user actions, not administrator content-publishing privileges.

Enforce these restrictions in Django permissions and APIs, not merely by hiding buttons in the frontend.

## 5. Core Application Features

Implement:

1. Student and Faculty registration and authentication.
2. Administrator-controlled account and role management.
3. Student and Faculty profiles.
4. Administrator-created college events.
5. Event photo galleries.
6. Authorized photograph viewing and downloads.
7. Administrator-published social feed posts.
8. Likes, comments, and user connections.
9. Administrator-managed photography spotlights.
10. Administrator-managed newsletters and announcements.
11. In-app and push notifications.
12. AI-powered Find My Photos.
13. Administrator dashboard.
14. Privacy, consent, and account deletion.

All publicly displayed application content must originate from or be approved and controlled by the Administrator.

## 6. Administrator Dashboard

Build a secure administrative dashboard, preferably as a web interface using Django Admin initially.

The Administrator must be able to:

1. Manage Student and Faculty accounts.
2. Create and manage college events.
3. Link Google Drive folders to events.
4. Upload, remove, and organize photographs.
5. Publish posts, spotlights, and newsletters.
6. Manage announcements and notifications.
7. Review and moderate comments.
8. Configure content visibility and permissions.
9. Monitor photograph synchronization.
10. Monitor face-indexing progress and failures.
11. Review application usage and system health.
12. Delete or archive content.

Students and Faculty must never have access to administrator-only endpoints.

## 7. Google Drive Integration

Google Drive stores original college event photographs.

Required workflow:

1. Administrator creates an event.
2. Administrator links an authorized Google Drive folder.
3. Backend automatically discovers photographs in that folder.
4. New and modified photographs are synchronized.
5. Photograph metadata is saved in PostgreSQL.
6. Optimized thumbnails and previews are generated.
7. Thumbnails and previews are stored in Cloudflare R2.
8. Original photographs remain in Google Drive.
9. Deleted photographs are removed or marked unavailable in PIXEL.
10. AI indexing runs automatically for new or changed photographs.

Avoid downloading unchanged images repeatedly.

Use background jobs, retries, synchronization logs, and secure Drive credentials.

Google Drive API access has no fixed free-trial expiration, but quotas, storage allowances, and applicable provider policies must be monitored.

## 8. AI-Powered Find My Photos

This is a major feature of PIXEL.

**Required workflow:**

1. Administrator publishes an event with photographs.
2. Backend automatically indexes detected faces in the event photographs.
3. Student or Faculty opens the PIXEL application.
4. User selects a published event.
5. User captures or uploads a selfie with appropriate consent.
6. Django verifies authentication and event access.
7. FastAPI detects and aligns the selfie face.
8. The AI model generates a face embedding.
9. Neon pgvector searches embeddings belonging to the selected event.
10. Similarity results are filtered using validated thresholds.
11. Duplicate photograph results are removed.
12. Matching photographs are displayed in the Android application.
13. User can view or download authorized photographs.

**Technical requirements:**

- Precompute embeddings for event photographs.
- Never rescan the entire event for every selfie search.
- Support multiple faces per photograph.
- Store face embeddings linked to event and photograph IDs.
- Use the same embedding model for event photographs and selfies.
- Use 512-dimensional embeddings if supported by the selected model.
- Keep original photographs in Google Drive.
- Avoid permanent storage of uploaded selfies.
- Separate background indexing from interactive searches.
- Implement consent, deletion, authorization, and retention controls.
- Measure recognition accuracy and false-positive rates.
- Do not automatically build named identities across events.

## 9. Database Design

Use Neon PostgreSQL with pgvector.

Create models for:

- Users
- Roles (Administrator, Faculty, Student)
- Profiles
- Events
- Event permissions
- Photographs
- Google Drive synchronization records
- Posts
- Likes
- Comments
- User connections
- Spotlights
- Newsletters
- Announcements
- Notifications
- Push device tokens
- Face embeddings
- Indexing jobs
- Face-search jobs
- Consent records
- Audit logs

Optimize database queries, indexes, pagination, and connection pooling.

Use Django migrations to manage schema changes.

## 10. Current Performance Requirements

**Current scale:**
- Approximately 4,000 registered users.
- Up to 100 simultaneously active users.
- Around 200 consenting participants for initial face-recognition testing.

**Performance goals:**
- Smooth gallery scrolling.
- Fast navigation.
- Responsive authentication and profile APIs.
- Efficient event and feed loading.
- Optimized image delivery.
- Reliable face-search results.
- Minimal unnecessary database requests.

Implement:

- Paginated APIs.
- CDN image caching.
- Optimized thumbnails.
- React Native virtualized lists.
- Efficient database indexes.
- Lightweight API responses.
- Background AI processing.
- AI search rate limits.
- Redis caching only when justified.

Test at 20, 50, and 100 simultaneous users.

Design the architecture so it can scale further later, but **do not overengineer or pay for infrastructure intended for 1,000 concurrent users at this stage**.

## 11. Hosting and Cost Requirements

Prioritize free-tier hosting during development and testing.

Preferred services:
- Neon PostgreSQL Free.
- Google Drive API.
- Cloudflare R2 Free.
- Firebase Cloud Messaging.
- Free-tier backend hosting where feasible.

Host the following components:

1. Django REST API.
2. FastAPI face-recognition service.
3. Background photo-indexing worker.
4. Database.
5. Image storage and delivery.
6. Scheduled Google Drive synchronization.

Account for cold starts, memory limitations, and free-tier usage quotas.

Do not promise uninterrupted or delay-free service from free-tier hosting.

Recommend paid or institution-provided infrastructure only when testing demonstrates that it is necessary.

## 12. Security and Privacy

Implement:

- HTTPS.
- Secure authentication and token handling.
- Role-based API authorization.
- Administrator-only content management.
- Secure Google Drive credentials.
- Secure database access.
- File upload validation.
- API rate limiting.
- Face-processing consent.
- Minimal selfie retention.
- Biometric embedding deletion.
- Account deletion.
- Audit logs.
- Privacy policy.
- Applicable Indian privacy and Google Play compliance requirements.

## 13. Notifications

Use Firebase Cloud Messaging and Expo Notifications.

Notifications may include:

- New administrator-published events.
- New event photographs.
- Administrator announcements.
- New newsletters.
- Likes and comments.
- Connection activity.
- Completed face-search results.

Administrators control application-wide announcements and published content notifications.

User-interaction notifications can be generated automatically by the backend.

## 14. Testing Plan

Test the application in stages:

1. Verify authentication and role permissions.
2. Test administrator-only content creation.
3. Test Student and Faculty restrictions.
4. Test Google Drive synchronization.
5. Test thumbnail generation and delivery.
6. Test AI indexing using event photographs.
7. Test face matching with 200 consenting participants.
8. Test API responses and database queries.
9. Test Android application navigation and galleries.
10. Test notifications.
11. Load-test 20 simultaneous users.
12. Load-test 50 simultaneous users.
13. Load-test 100 simultaneous users.
14. Separately test concurrent AI face searches.
15. Fix bottlenecks before production deployment.

## 15. Google Play Deployment

Complete:

1. Production Android configuration.
2. EAS Build configuration.
3. Android application signing.
4. Production API endpoints.
5. Signed AAB generation.
6. App icons and screenshots.
7. Privacy policy and Data Safety declarations.
8. Account-deletion instructions.
9. Required Google Play testing.
10. Play Console submission.
11. Production release.
12. Monitoring and updates.

## 16. Instructions for the AI Development Assistant

Act as a senior full-stack developer, React Native engineer, Django developer, AI/ML engineer, PostgreSQL architect, and DevOps engineer.

Follow these instructions:

1. Inspect the existing PIXEL repository before generating code.
2. Identify completed, incomplete, and missing functionality.
3. Preserve the existing frontend design where practical.
4. Implement exactly three roles: Administrator, Faculty, and Student.
5. Restrict all application content management to Administrators.
6. Allow Students and Faculty to interact with published content without granting publishing privileges.
7. Build secure Django REST APIs.
8. Implement Google Drive event-folder synchronization.
9. Implement automated face indexing and event-specific selfie matching.
10. Use Neon PostgreSQL and pgvector.
11. Optimize image delivery with Cloudflare R2.
12. Integrate Firebase notifications.
13. Target 100 simultaneous users for the current release.
14. Prefer free-tier and low-cost infrastructure.
15. Keep the system modular and scalable without unnecessary complexity.
16. Provide file-by-file changes, code, commands, and tests.
17. Never hardcode secrets or credentials.
18. Verify each phase before starting the next.
19. Guide development through hosting and Google Play deployment.
20. Clearly identify any functionality that cannot be verified without the actual project files.

**Start by reviewing my existing PIXEL repository, identifying the development gaps, and creating a phased implementation plan. Do not rewrite completed functionality unnecessarily.**