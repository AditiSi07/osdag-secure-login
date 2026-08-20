# Secure Login System — Custom Backend + Appwrite

Two implementations of the same auth / user-details / file-access contract (see [`docs/api-contract.md`](docs/api-contract.md)), both testable through the single provided client in [`client/`](client).

---

## Repo layout

| Path | What's there |
|---|---|
| `client/` | The provided test client (`index.html`, `mock-api.js`, `seed-data.json`), plus `appwrite-adapter.js` — written for this task so the same unmodified `index.html` can talk to Appwrite mode |
| `custom-backend/` | FastAPI + PostgreSQL implementation |
| `appwrite-backend/` | Appwrite-based implementation |
| `docs/api-contract.md` | The exact endpoint contract both backends satisfy |

---

## Setup

### Custom backend

Full instructions: [`custom-backend/README.md`](custom-backend/README.md)

```bash
cd custom-backend
python -m venv .venv && .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # fill in your Postgres password
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)"
python seed.py
uvicorn app.main:app --reload --port 3000
```

### Appwrite backend

Full instructions (Appwrite console setup required first): [`appwrite-backend/README.md`](appwrite-backend/README.md)

```bash
cd appwrite-backend
python -m venv .venv && .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # fill in your real Appwrite values
python seed.py
```

### Test client

```bash
cd client
python -m http.server 8080
```

Open `http://localhost:8080/index.html` — switch between **Mock** / **Custom REST backend** / **Appwrite** modes via the radio buttons at the top.

---

## Test credentials

Seeded via each backend's own `seed.py`:

| Email | Password |
|---|---|
| alice@example.com | Password123! |
| bob@example.com | Password123! |
| carol@example.com | Password123! |

---

## Design notes

### JWT vs. session-based auth (custom backend)

I used opaque, randomly-generated session tokens stored server-side (hashed, in a `sessions` table) rather than stateless JWTs. The task requires logout to invalidate the session server-side, not just client-side — a bare JWT can't do that without maintaining a revocation list anyway, which is functionally the same mechanism as this `sessions` table. Going directly with server-tracked sessions avoided implementing JWT and then bolting on a blocklist just to satisfy the logout requirement.

### How logout works

- **Custom backend** — each login creates a `sessions` row with a SHA-256 hash of the token (the raw token itself is never stored) and an expiry. Logout sets `revoked_at` on that row. The shared `get_current_user` dependency (`app/auth.py`) checks that the session exists, is not expired, and has `revoked_at IS NULL` on every protected route — a revoked token is rejected on its very next use.
- **Appwrite backend** — `account.deleteSession('current')` is a native platform call; Appwrite invalidates the session server-side immediately, no custom code required.

### How user data isolation is enforced

- **Custom backend** — every protected route derives the current user exclusively from the validated session token; no route accepts a client-supplied user ID. `/files/:id` explicitly checks file ownership as a step separate from checking existence, returning `404` for "doesn't exist" and `403` for "exists but isn't yours."
- **Appwrite backend** — enforced natively via per-document read permissions (`Permission.read(Role.user(ownerId))`, set at creation time) with Document Security enabled on the collection. Appwrite's query/list engine only ever returns documents the current session is permitted to read.

> **Platform-level difference worth flagging:** Appwrite's `getDocument()` returns the same `404` whether a document doesn't exist or exists but isn't readable by the caller — a deliberate anti-enumeration security choice on Appwrite's part. So the custom backend's explicit 404-vs-403 distinction isn't literally reproducible against a single-document fetch in the Appwrite implementation without adding a server-side Appwrite Function. Full reasoning in [`appwrite-backend/README.md`](appwrite-backend/README.md).

### Rate limiting / lockout

- **Custom backend** — per-account, via `failed_attempts` / `locked_until` on the `users` table. 5 consecutive failures locks the account for 5 minutes; a successful login resets the counter. Chosen over per-IP for simplicity and to avoid locking out legitimate users sharing an IP (e.g. behind NAT); a production system would likely combine both.
- **Appwrite backend** — Appwrite Cloud applies its own platform-level rate limiting on auth endpoints automatically.

### What Appwrite handled automatically vs. what I configured myself

Appwrite handles password hashing, session issuance/validation, and logout invalidation natively. I configured the database schema, per-document permissions, and the Document Security setting that makes those permissions apply to queries. Full breakdown in [`appwrite-backend/README.md`](appwrite-backend/README.md).

---

## What I'd improve given more time

- Refresh-token rotation for the custom backend instead of a single long-lived session token
- Combine per-account and per-IP rate limiting
- Real file storage (S3-compatible / Appwrite Storage bucket) instead of text content in the database, for both implementations
- Automated test suite (pytest for custom backend, SDK-based for Appwrite) run in CI
- A server-side Appwrite Function to restore explicit 403-vs-404 on Appwrite's single-file fetch, if exact parity with the custom backend's contract is required
