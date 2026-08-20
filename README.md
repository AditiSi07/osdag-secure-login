\# Secure Login System — Custom Backend + Appwrite



Two implementations of the same auth/user-details/file-access contract

(see `docs/api-contract.md`), both testable through the single provided

client in `client/`.



\## Repo layout

\- `client/` — the provided test client (`index.html`, `mock-api.js`,

&#x20; `seed-data.json`), plus `appwrite-adapter.js` (written for this task)

&#x20; which lets the same unmodified `index.html` talk to Appwrite mode

\- `custom-backend/` — FastAPI + PostgreSQL implementation

\- `appwrite-backend/` — Appwrite-based implementation

\- `docs/api-contract.md` — the exact endpoint contract both backends

&#x20; satisfy



\## Setup



\### Custom backend

See `custom-backend/README.md` for full setup. Quick version:



cd custom-backend

python -m venv .venv \&\& .venv\\Scripts\\Activate.ps1

pip install -r requirements.txt

copy .env.example .env # fill in your Postgres password

python -c "from app.database import Base, engine; from app import models; Base.metadata.create\_all(bind=engine)"

python seed.py

uvicorn app.main:app --reload --port 3000





\### Appwrite backend

See `appwrite-backend/README.md` for full setup (Appwrite project

configuration is required first — collection, permissions, platform,

API key). Quick version once configured:



cd appwrite-backend

python -m venv .venv \&\& .venv\\Scripts\\Activate.ps1

pip install -r requirements.txt

copy .env.example .env # fill in your real Appwrite values

python seed.py





\### Test client



cd client

python -m http.server 8080



Open `http://localhost:8080/index.html` — switch between Mock / Custom

REST backend / Appwrite modes via the radio buttons at the top.



\## Test credentials (both backends, seeded via each backend's `seed.py`)



| Email | Password |

|---|---|

| alice@example.com | Password123! |

| bob@example.com | Password123! |

| carol@example.com | Password123! |



\## Design notes



\*\*JWT vs. session-based auth (custom backend):\*\* I used opaque,

randomly-generated session tokens stored server-side (hashed, in a

`sessions` table) rather than stateless JWTs. The task requires logout

to invalidate the session server-side, not just client-side — a bare

JWT can't do that without maintaining a revocation list anyway, which

is functionally the same mechanism as this `sessions` table. Going

directly with server-tracked sessions avoided implementing JWT and then

bolting on a blocklist just to satisfy the logout requirement.



\*\*How logout works:\*\* \*Custom backend\* — each login creates a

`sessions` row with a SHA-256 hash of the token (never the raw token

itself) and an expiry; logout sets `revoked\_at` on that row, and the

shared `get\_current\_user` dependency rejects any token whose session is

revoked or expired, on every protected route. \*Appwrite backend\* —

`account.deleteSession('current')` is a native platform call; Appwrite

invalidates the session server-side immediately, no custom code

required.



\*\*How user data isolation is enforced:\*\* \*Custom backend\* — every

protected route derives the current user exclusively from the validated

session token; no route accepts a client-supplied user ID. `/files/:id`

explicitly checks file ownership as a separate step from checking

existence, returning 404 for "doesn't exist" and 403 for "exists but

isn't yours." \*Appwrite backend\* — enforced natively by Appwrite via

per-document read permissions (`Permission.read(Role.user(ownerId))`,

set at creation time) with Document Security enabled on the collection;

Appwrite's query/list engine only ever returns documents the current

session is permitted to read, so isolation holds even without any

explicit ownership check in my adapter code. One platform-level

difference worth flagging: Appwrite's `getDocument()` returns the same

404 whether a document doesn't exist or exists but isn't readable by

the caller (a deliberate anti-enumeration security choice on Appwrite's

part) — so the custom backend's explicit 404-vs-403 distinction isn't

literally reproducible against a single-document fetch in the Appwrite

implementation without adding a server-side Appwrite Function; see

`appwrite-backend/README.md` for the full reasoning.



\*\*Rate limiting / lockout (custom backend):\*\* per-account, via

`failed\_attempts`/`locked\_until` on the `users` table — 5 consecutive

failures locks the account for 5 minutes, reset on successful login.

Chosen over per-IP limiting for simplicity and to avoid locking out

legitimate users sharing an IP; a production system would likely

combine both. \*Appwrite backend\* — Appwrite Cloud applies its own

platform-level rate limiting on the auth endpoints automatically.



\*\*What Appwrite handled automatically vs. what I configured myself:\*\*

see `appwrite-backend/README.md` for the detailed breakdown — in short,

Appwrite handles password hashing, session issuance/validation, and

logout invalidation natively; I configured the database schema,

per-document permissions, and the Document Security setting that makes

those permissions apply to queries.



\## What I'd improve given more time

\- Refresh-token rotation for the custom backend instead of a single

&#x20; long-lived session token

\- Combine per-account and per-IP rate limiting

\- Real file storage (S3-compatible / Appwrite Storage bucket) instead

&#x20; of text content in the database, for both implementations

\- Automated test suite (pytest for custom backend, SDK-based for

&#x20; Appwrite) run in CI

\- A server-side Appwrite Function to restore explicit 403-vs-404 on

&#x20; Appwrite's single-file fetch, if exact parity with the custom

&#x20; backend's contract is required

