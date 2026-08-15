# API Contract

Derived directly from `client/mock-api.js` (the reference behavior) and `client/index.html`
(the calling code). Both `custom-backend` and `appwrite-backend` must satisfy this contract
exactly, so the same unmodified `index.html` works against either one.

Auth: `Authorization: Bearer <token>` header on every protected route (the client also has a
cookie-mode toggle — optional, Bearer is the primary path and what's built first).

## POST /register
Request: `{ "email": string, "password": string }`
- `201 { "id": string, "email": string }` on success
- `400 { "error": string }` if email or password missing
- `409 { "error": string }` if email already registered

## POST /login
Request: `{ "email": string, "password": string }`
- `200 { "token": string, "user": { "id": string, "email": string } }` on success
- `401 { "error": "Invalid email or password" }` — used for BOTH wrong password AND
  unknown email. Never distinguish these two cases in the response.
- `429 { "error": string }` when locked out after repeated failures

## POST /logout
Auth required.
- `200 { "message": string }`
- Must revoke the token server-side (mock does `sessions.delete(token)`), not just
  rely on the client discarding it.

## GET /me
Auth required.
- `200 { "id": string, "email": string, "profile": { "fullName": string,
  "displayName": string, "bio": string, "createdAt": string (ISO), "role": string } }`
- `401 { "error": string }` if not authenticated
- Must derive the user ONLY from the token — no client-supplied user id is ever accepted.

## GET /files
Auth required.
- `200 { "files": [ { "id", "ownerId", "fileName", "mimeType", "sizeBytes", "uploadedAt" } ] }`
- Only the current user's own files. Never accept a client-supplied owner filter.

## GET /files/:id
Auth required.
- `200 { "file": {...} }` if it exists and belongs to the current user
- `404 { "error": string }` if no file with that id exists at all
- `403 { "error": string }` if it exists but belongs to a different user
  (this distinction is explicitly graded — implement as two separate checks)

## GET /files/:id/download
Auth required. Not JSON — raw content.
- `200` — file bytes/text with an appropriate `Content-Type`
- `404` plain text if not found
- `403` plain text if not the owner

## Rate limiting / lockout (mock's exact numbers, for reference — not mandatory to match precisely)
Mock: lock after 5 failed attempts, 60 second lockout, tracked per-email.
Real backend: same idea, keep it testable (don't set the lockout window so long that a
reviewer can't verify it in the interview) — e.g. 5 attempts / 2–5 minute lockout is a
reasonable real-world choice; document whatever you pick and why in the README.

## Data model reference (from seed-data.json)
```json
{
  "id": "usr_001",
  "email": "alice@example.com",
  "profile": {
    "fullName": "Alice Nakamura",
    "displayName": "alice",
    "bio": "Product designer who likes clean UIs.",
    "createdAt": "2025-01-14T09:32:00Z",
    "role": "user"
  },
  "files": [
    {
      "id": "file_001",
      "ownerId": "usr_001",
      "fileName": "resume_alice.pdf",
      "mimeType": "application/pdf",
      "sizeBytes": 84213,
      "uploadedAt": "2025-01-15T10:02:00Z"
    }
  ]
}
```
Seed users: alice@example.com / bob@example.com / carol@example.com, all password
`Password123!` in the sample data — hash before inserting, never store as-is.

## index.html modes (do not modify this file's structure/logic)
- **Mock** — `mock-api.js` intercepts fetch, no backend needed.
- **Custom** — uses the `Base URL` field, does a real network `fetch` to your running
  custom-backend (default `http://localhost:3000` — CORS must be enabled there).
- **Appwrite** — intended to be handled by an `appwrite-adapter.js` (slot already reserved
  as a commented-out `<script>` tag) that intercepts fetch the same way mock-api.js does,
  but calls the Appwrite Web SDK instead of hitting the network. Built in a later step —
  not needed until the custom-backend is done and working.
