/**
 * appwrite-adapter.js
 * --------------------
 * Makes index.html's "Appwrite" backend mode work by intercepting fetch()
 * the same way mock-api.js does, but translating each call into a real
 * Appwrite Web SDK call instead of using in-memory fake data.
 *
 * IMPORTANT: Appwrite's Web SDK manages the actual session via its own
 * secure cookie once you call account.createEmailPasswordSession(). The
 * "token" this adapter returns to the client is cosmetic (just so the UI's
 * Token field shows something) — real auth for every subsequent call is
 * the SDK's own session, tied to this browser tab, not the Bearer header.
 */

(function () {
  function getConfig() {
    return {
      endpoint: document.getElementById("awEndpoint").value.trim(),
      projectId: document.getElementById("awProjectId").value.trim(),
      databaseId: document.getElementById("awDatabaseId").value.trim(),
      filesCollectionId: document.getElementById("awFilesCollectionId").value.trim(),
    };
  }

 function buildClient() {
    const cfg = getConfig();
    const client = new Appwrite.Client();
    client.setEndpoint(cfg.endpoint).setProject(cfg.projectId);

    // Third-party cookie fallback: Appwrite Cloud's session cookie is set
    // on a different origin than this page (localhost), which modern
    // browsers block by default. Appwrite's SDK persists a fallback
    // session identifier in localStorage specifically for this case —
    // we read it back on every client build so subsequent calls stay
    // authenticated even though the cookie itself never lands.
    const fallback = localStorage.getItem("cookieFallback");
    if (fallback) {
      try {
        const parsed = JSON.parse(fallback);
        const sessionKey = Object.keys(parsed).find((k) => k.startsWith("a_session_"));
        if (sessionKey) client.setSession(parsed[sessionKey]);
      } catch (e) {
        // malformed fallback value, ignore
      }
    }

    return { client, cfg };
}

  function json(status, body) {
    return new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  }

  function isAppwriteMode() {
    const radios = document.getElementsByName("backendMode");
    for (const r of radios) {
      if (r.value === "appwrite" && r.checked) return true;
    }
    return false;
  }

  async function handleRegister(req) {
    const { email, password } = await req.json();
    const { client } = buildClient();
    const account = new Appwrite.Account(client);
    try {
      const user = await account.create(Appwrite.ID.unique(), email, password);
      return json(201, { id: user.$id, email: user.email });
    } catch (e) {
      const status = e.code === 409 ? 409 : 400;
      return json(status, { error: e.message });
    }
  }

 async function handleLogin(req) {
    const { email, password } = await req.json();
    const { client } = buildClient();
    const account = new Appwrite.Account(client);

    // Clear any existing session first — createEmailPasswordSession can
    // fail if one is already active (e.g. switching from alice to bob
    // without an explicit logout in between).
    try {
      await account.deleteSession("current");
    } catch (e) {
      // no existing session, fine
    }

    try {
      const session = await account.createEmailPasswordSession(email, password);
      const user = await account.get();
      return json(200, { token: session.$id, user: { id: user.$id, email: user.email } });
    } catch (e) {
      console.error("[appwrite-adapter] login failed", e);
      return json(401, { error: "Invalid email or password" });
    }
}

  async function handleLogout() {
    const { client } = buildClient();
    const account = new Appwrite.Account(client);
    try {
      await account.deleteSession("current");
    } catch (e) {
      // Already logged out / no session — same forgiving behavior as
      // the custom backend's logout.
    }
    return json(200, { message: "Logged out" });
  }

  async function handleMe() {
    const { client } = buildClient();
    const account = new Appwrite.Account(client);
    try {
      const user = await account.get();
      return json(200, {
        id: user.$id,
        email: user.email,
        profile: {
          fullName: user.name || "",
          displayName: (user.email || "").split("@")[0],
          bio: "",
          createdAt: user.registration || "",
          role: "user",
        },
      });
    } catch (e) {
      return json(401, { error: "Not authenticated" });
    }
  }

async function handleFiles() {
    const { client, cfg } = buildClient();
    const account = new Appwrite.Account(client);
    const databases = new Appwrite.Databases(client);

    let user;
    try {
      user = await account.get();
    } catch (e) {
      console.error("[appwrite-adapter] /files: not authenticated", e);
      return json(401, { error: "Not authenticated" });
    }

    try {
      const result = await databases.listDocuments(cfg.databaseId, cfg.filesCollectionId, [
        Appwrite.Query.equal("ownerId", [user.$id]),
      ]);
      const files = result.documents.map((d) => ({
        id: d.$id,
        ownerId: d.ownerId,
        fileName: d.fileName,
        mimeType: d.mimeType,
        sizeBytes: d.sizeBytes,
        uploadedAt: d.uploadedAt,
      }));
      return json(200, { files });
    } catch (e) {
      console.error("[appwrite-adapter] /files: listDocuments failed", e);
      return json(500, { error: "Failed to list files: " + e.message });
    }
}

  async function getFileOr(errorHandler, fileId) {
    const { client, cfg } = buildClient();
    const account = new Appwrite.Account(client);
    const databases = new Appwrite.Databases(client);
    try {
      await account.get(); // throws if not authenticated
    } catch (e) {
      return errorHandler(401, "Not authenticated");
    }
    try {
      const doc = await databases.getDocument(cfg.databaseId, cfg.filesCollectionId, fileId);
      return { doc };
    } catch (e) {
      // Appwrite returns 404 when the document genuinely doesn't exist.
      // When it exists but the current session lacks read permission,
      // Appwrite returns 401 at the SDK level (it doesn't have a native
      // 403 concept here) — we translate that into our contract's 403
      // ("exists but not yours"), since the session itself IS valid,
      // it's specifically permission on this one document that's denied.
      if (e.code === 404) return errorHandler(404, "File not found");
      return errorHandler(403, "You do not have access to this file");
    }
  }

  async function handleFileById(fileId) {
    let errJson = null;
    const result = await getFileOr((status, message) => {
      errJson = json(status, { error: message });
    }, fileId);
    if (errJson) return errJson;

    const d = result.doc;
    return json(200, {
      file: {
        id: d.$id,
        ownerId: d.ownerId,
        fileName: d.fileName,
        mimeType: d.mimeType,
        sizeBytes: d.sizeBytes,
        uploadedAt: d.uploadedAt,
      },
    });
  }

  async function handleFileDownload(fileId) {
    let errResp = null;
    const result = await getFileOr((status, message) => {
      errResp = new Response(message, { status });
    }, fileId);
    if (errResp) return errResp;

    const d = result.doc;
    return new Response(d.content || `(mock content for ${d.fileName})`, {
      status: 200,
      headers: { "Content-Type": "text/plain" },
    });
  }

  // ---- patch window.fetch, layered on top of whatever mock-api.js already installed ----
  const previousFetch = window.fetch.bind(window);

 window.fetch = async function (input, init) {
    if (!isAppwriteMode()) return previousFetch(input, init);

    const url = typeof input === "string" ? input : input.url;
    let pathname;
    try {
      pathname = new URL(url, window.location.href).pathname;
    } catch (e) {
      return previousFetch(input, init);
    }

    const req = new Request(url, init);

    if (pathname === "/register" && req.method === "POST") return handleRegister(req);
    if (pathname === "/login" && req.method === "POST") return handleLogin(req);
    if (pathname === "/logout" && req.method === "POST") return handleLogout();
    if (pathname === "/me" && req.method === "GET") return handleMe();
    if (pathname === "/files" && req.method === "GET") return handleFiles();

    let m = pathname.match(/^\/files\/([^/]+)\/download$/);
    if (m && req.method === "GET") return handleFileDownload(m[1]);

    m = pathname.match(/^\/files\/([^/]+)$/);
    if (m && req.method === "GET") return handleFileById(m[1]);

    // Doesn't match any of our contract routes — this is the Appwrite
    // SDK's own internal call (e.g. to cloud.appwrite.io/v1/account/...).
    // Let it through untouched.
    return previousFetch(input, init);
};



  console.info("[appwrite-adapter] ready — select 'Appwrite' mode in index.html to use it");
})();