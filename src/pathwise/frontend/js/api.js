// Tiny fetch wrapper. Reads/writes session token in localStorage.

const TOKEN_KEY = "pathwise.session_token";

const api = (() => {
  function getToken() { return localStorage.getItem(TOKEN_KEY); }
  function setToken(t) { localStorage.setItem(TOKEN_KEY, t); }
  function clearToken() { localStorage.removeItem(TOKEN_KEY); }

  async function request(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    const t = getToken();
    if (t) headers.Authorization = `Bearer ${t}`;
    const res = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (res.status === 401) {
      clearToken();
      const err = new Error("Session expired. Please sign in again.");
      err.status = 401;
      throw err;
    }
    let payload = null;
    try { payload = await res.json(); } catch (_) {}
    if (!res.ok) {
      const err = new Error((payload && payload.detail) || `HTTP ${res.status}`);
      err.status = res.status;
      err.payload = payload;
      throw err;
    }
    return payload;
  }

  return {
    getToken, setToken, clearToken,
    get:    (p)    => request("GET", p),
    post:   (p, b) => request("POST", p, b ?? {}),
    put:    (p, b) => request("PUT", p, b ?? {}),
    patch:  (p, b) => request("PATCH", p, b ?? {}),

    // High-level endpoints
    startCode: (phone)         => request("POST", "/auth/start", { phone }),
    verifyCode: (phone, code)  => request("POST", "/auth/verify", { phone, code }),
    revokeSession:               () => request("POST", "/auth/revoke"),
    me:                          () => request("GET", "/me"),
    onboard: (data)            => request("POST", "/me/onboard", data),
    updateMe: (data)           => request("PATCH", "/me", data),
    deleteMe:                    () => request("DELETE", "/me"),
    seasons:                     () => request("GET", "/seasons"),
    mySeasons:                   () => request("GET", "/me/seasons"),
    questions: (seasonId)      => request("GET", `/seasons/${seasonId}/questions`),
    getAnswers: (seasonId)     => request("GET", `/seasons/${seasonId}/answers`),
    putAnswers: (seasonId, a)  => request("PUT", `/seasons/${seasonId}/answers`, { answers: a }),
    generatePlan: (seasonId)   => request("POST", `/seasons/${seasonId}/plans`),
    listPlans: (seasonId)      => request("GET", `/seasons/${seasonId}/plans`),
    getPlan: (seasonId, v)     => request("GET", `/seasons/${seasonId}/plans/${v}`),
    latestPlan: (seasonId)     => request("GET", `/seasons/${seasonId}/plans/latest`),
    getChat: (seasonId, v)     => request("GET", `/seasons/${seasonId}/plans/${v}/chat`),
    sendChat: (seasonId, v, text) => request("POST", `/seasons/${seasonId}/plans/${v}/chat`, { text }),
    regenerateFromChat: (seasonId, v) => request("POST", `/seasons/${seasonId}/plans/${v}/chat/regenerate`),
    listDocs:                    () => request("GET", "/technical"),
    getDoc: (slug)             => request("GET", `/technical/${slug}`),
  };
})();
