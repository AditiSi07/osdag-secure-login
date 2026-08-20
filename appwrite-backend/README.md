# Appwrite Backend

## Setup

1. Create an Appwrite Cloud project (or self-hosted instance).
2. Enable Email/Password auth: **Auth → Settings**.
3. Create a database, and inside it a `files` collection with attributes:

   | Attribute | Type | Required |
   |---|---|---|
   | `ownerId` | string, indexed | yes |
   | `fileName` | string | yes |
   | `mimeType` | string | yes |
   | `sizeBytes` | integer | yes |
   | `content` | string | no |
   | `uploadedAt` | datetime | yes |

4. In the `files` collection's **Settings**, enable **Document Security** — without this, per-document read permissions are ignored on list/query operations and every request is rejected.
5. Leave collection-level permissions empty/restrictive — access is granted entirely per-document at creation time (see seed script).
6. Add a **Web platform** (Settings → Platforms) with hostname `localhost`, type **JavaScript** — required for the browser SDK to be allowed to call the API from `http://localhost:8080`.
7. Create a server **API key** (Settings → API Keys) with scopes covering Auth (`users.read`, `users.write`) and Databases (`documents.read`/`write`) — used only by `seed.py`, never exposed to the browser.
8. Copy `.env.example` to `.env` and fill in your real Project ID, Database ID, and API key.

   > Appwrite Cloud endpoints are region-specific, e.g. `https://fra.cloud.appwrite.io/v1` — copy the exact value from your project's Settings page.

9. Install dependencies and seed the 3 required test users:

   ```bash
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python seed.py
   ```

---

## Test credentials

Same three seeded users as the custom backend, same password:

| Email | Password |
|---|---|
| alice@example.com | Password123! |
| bob@example.com | Password123! |
| carol@example.com | Password123! |

---

## Testing against the provided client

`client/index.html` includes an **Appwrite** backend mode that talks directly to Appwrite via its Web SDK, using `client/appwrite-adapter.js` — it intercepts the same `/login`, `/me`, `/files`, etc. calls the client makes, the same way `mock-api.js` does for mock mode, but backed by real Appwrite Account/Databases calls.

Serve the client over HTTP (not `file://`):

```bash
cd ../client
python -m http.server 8080
```

Open `http://localhost:8080/index.html`, select **Appwrite** mode, and fill in the Endpoint / Project ID / Database ID / Files collection ID fields from your `.env` values.

---

## Design notes

### What Appwrite handled automatically

Password hashing, session issuance and validation, and the actual server-side logout mechanism — `account.deleteSession('current')` immediately invalidates that session; no code of mine implements this, it's native to the platform. `account.get()` provides the authenticated-user-only profile lookup for `/me` with no possibility of supplying a different user's ID, since the SDK call takes no parameters at all — the user is entirely determined by the active session.

### What I configured myself

The database schema, per-document read permissions (`Permission.read(Role.user(ownerId))`, set at document creation in `seed.py`) which is what actually enforces that a user can only read their own files, and the Document Security toggle required for those permissions to apply to list/query operations at all.

### Known platform-level difference from the custom backend — the 404 vs. 403 distinction

Appwrite's `getDocument()` returns an identical `404` whether a document genuinely doesn't exist or exists but the caller lacks read permission on it. This is a deliberate Appwrite security choice — it prevents an attacker from distinguishing "exists but not yours" from "doesn't exist" to enumerate valid IDs.

Unlike the custom backend, where I wrote that distinction myself as two explicit checks, here both cases collapse to `404`. I chose to preserve Appwrite's native behavior rather than override it with a server-side Appwrite Function that would fetch documents with an admin key and manually compare ownership. That's a reasonable next step, but adds real scope for a platform-level nuance that's arguably a legitimate security property in its own right, not a bug.

---

## What I'd improve given more time

- A server-side Appwrite Function to restore an explicit 403 vs. 404 distinction on `/files/:id`, if that exact contract match is required
- Real Storage bucket uploads instead of storing file content as a text attribute
- Automated tests against the Appwrite SDK (currently verified manually)
- A custom domain for the API endpoint (Appwrite's own browser console warning recommends this over using the default Cloud domain with localStorage-based session fallback)
