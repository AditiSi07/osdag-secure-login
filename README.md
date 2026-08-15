# Secure Login System — Custom Backend + Appwrite

Two implementations of the same auth/user-details/file-access contract (see
`docs/api-contract.md`), both testable through the single provided client in `client/`.

## Repo layout
- `client/` — the provided test client (`index.html`, `mock-api.js`, `seed-data.json`),
  used unmodified against both backends
- `custom-backend/` — FastAPI + PostgreSQL implementation
- `appwrite-backend/` — Appwrite-based implementation
- `docs/api-contract.md` — the exact endpoint contract both backends satisfy

## Setup

### Custom backend
_(instructions added once the implementation is in place — Step 2 onward)_

### Appwrite backend
_(instructions added once the implementation is in place)_

## Design notes
_(the four required write-ups — JWT vs. session reasoning, how logout works, how
data isolation is enforced, what Appwrite handled automatically vs. manually — are
added progressively as each piece is built, then finalized at the end)_

## What I'd improve given more time
_(filled in at the end)_
