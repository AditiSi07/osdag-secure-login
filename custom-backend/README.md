\# Custom Backend — FastAPI + PostgreSQL



\## Setup



1\. Create a virtual environment and activate it:



python -m venv .venv

.venv\\Scripts\\Activate.ps1 # Windows

source .venv/bin/activate # macOS/Linux



2\. Install dependencies:



pip install -r requirements.txt



3\. Create a PostgreSQL database named `login\_system` (see root README or install PostgreSQL locally / via Docker).

4\. Copy `.env.example` to `.env` and fill in your actual database password:



copy .env.example .env



5\. Create the tables:



python -c "from app.database import Base, engine; from app import models; Base.metadata.create\_all(bind=engine)"



6\. Seed the 3 required test users:



python seed.py



7\. Run the server:



uvicorn app.main:app --reload --port 3000





\## Test credentials



All seeded via `seed.py`, all use the same password for convenience:



| Email | Password |

|---|---|

| alice@example.com | Password123! |

| bob@example.com | Password123! |

| carol@example.com | Password123! |



`seed.py` is idempotent — safe to re-run, it skips users that already exist rather than duplicating them.



\## Testing against the provided client



Serve `../client/index.html` over HTTP (not `file://`, since it needs to fetch `seed-data.json` in mock mode and make cross-origin requests in custom-backend mode):



cd ../client

python -m http.server 8080



Then open `http://localhost:8080/index.html`, select "Custom REST backend" mode — the default Base URL (`http://localhost:3000`) already matches this server.



\## Design decisions



\*\*JWT vs. session-based auth:\*\* I chose opaque, randomly-generated session tokens stored server-side (hashed, in a `sessions` table) rather than stateless JWTs. The task requires that logout invalidate the session server-side, not just clear it client-side — a bare stateless JWT can't do that without maintaining a server-side revocation list anyway, which is functionally the same thing as this `sessions` table. So rather than implementing JWT and then bolting on a blocklist to satisfy the logout requirement, I went directly with the server-tracked-session approach, which supports real revocation natively and is simpler to reason about correctly.



\*\*How logout works:\*\* each login creates a row in `sessions` with a `token\_hash` (SHA-256 of the raw token — the raw token itself is never stored, same principle as password hashing) and an `expires\_at`. Logout sets `revoked\_at` on that row. Every protected route's shared dependency (`get\_current\_user` in `app/auth.py`) checks that the session exists, is not expired, and has `revoked\_at IS NULL` — so a revoked token is rejected immediately on its very next use, even though the client might still be holding onto it.



\*\*How user data isolation is enforced:\*\* every protected route derives the current user exclusively from the validated session token (via `get\_current\_user`) — no route ever accepts a client-supplied user ID or owner filter. `/files/:id` and `/files/:id/download` explicitly check `file.owner\_id == current\_user.id` as a distinct step from checking whether the file exists at all, returning `404` for "doesn't exist" and `403` for "exists but isn't yours" — these are two separate `if` branches in the code, not collapsed into one check, per the task's explicit requirement to distinguish the two cases.



\*\*Rate limiting / lockout:\*\* implemented per-account (tracked via `failed\_attempts` / `locked\_until` columns on the `users` table) rather than per-IP. After 5 consecutive failed login attempts, the account locks for 5 minutes. A successful login resets the counter. I chose per-account over per-IP because it's simpler to reason about and test, and doesn't risk locking out legitimate users sharing an IP (e.g. behind NAT/a corporate network) — the trade-off is it doesn't protect against a distributed attack trying many accounts from many IPs, which per-IP limiting also wouldn't fully solve on its own; a production system would likely want both.



\*\*Ambiguous decision — validation error codes:\*\* FastAPI/Pydantic returns `422` for malformed request bodies (missing/invalid fields) by convention, rather than `400`. I kept FastAPI's default rather than overriding it, since `422 Unprocessable Entity` is arguably the more semantically correct status for "well-formed JSON but invalid field values" versus `400 Bad Request` — but this is a minor, debatable convention difference worth flagging explicitly.



\## What I'd improve given more time

\- Refresh-token rotation instead of a single long-lived session token

\- Combine per-account lockout with per-IP rate limiting for defense in depth

\- Real file storage (e.g. S3-compatible object storage) instead of storing file content as text in the database

\- Automated test suite (pytest) covering the auth and isolation logic, run in CI

\- Alembic migrations instead of `Base.metadata.create\_all()` for schema changes

