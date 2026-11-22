# Planned Django application boundaries

`accounts` is implemented for authentication, roles, onboarding, policy records, user search and the initial small Moments video model. The other boundaries below remain planned; create them when their phase begins. Move the initial Moments model into `content` using a data-preserving migration when that application is introduced.

| Application | Owned data / behavior |
| --- | --- |
| `accounts` | Custom User, three role choices, Profile, registration/authentication, account deletion |
| `events` | Event, EventPermission, Photograph, visibility, authorized download orchestration |
| `content` | Post, Spotlight, Newsletter, Announcement, administrator publication lifecycle |
| `social` | Like, Comment, Connection, SavedCollection, moderation |
| `notifications` | Notification, PushDeviceToken, delivery records and retries |
| `integrations` | Google Drive and R2 adapters, sync runs/cursors, retries and media derivatives |
| `recognition` | FaceEmbedding, IndexingJob, FaceSearchJob, ConsentRecord, inference client, vector search |
| `audit` | Actor/action/target AuditLog with redacted metadata |

Keep validation in serializers, authorization in permissions and scoped querysets, multi-step operations in domain services, and external calls in adapters. Jobs call the same domain services as APIs/admin where appropriate. Django Admin must use the same publication/access invariants as APIs.
