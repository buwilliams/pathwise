// Hash router + state. Single page; views live in views.js.

(() => {
  const root = document.getElementById("view");
  const logoutBtn = document.getElementById("logout-btn");
  const headerNav = document.getElementById("header-nav");

  // phoneInFlight persists across page refreshes so a refresh on /auth/code
  // doesn't dump the user back to the start. Cleared on successful verify or
  // when they explicitly start over.
  const PHONE_KEY = "pathwise.phone_in_flight";
  const phoneInFlight = {
    get: () => sessionStorage.getItem(PHONE_KEY) || "",
    set: (v) => sessionStorage.setItem(PHONE_KEY, v),
    clear: () => sessionStorage.removeItem(PHONE_KEY),
  };

  function show(node) {
    root.replaceChildren(node);
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  // ───── Hamburger menu ─────
  const menuBtn = document.getElementById("menu-btn");
  const menuPanel = document.getElementById("menu-panel");
  function setMenuOpen(open) {
    menuPanel.hidden = !open;
    menuBtn.setAttribute("aria-expanded", String(open));
  }
  menuBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    setMenuOpen(menuPanel.hidden);
  });
  // Close on outside click
  document.addEventListener("click", (e) => {
    if (!menuPanel.hidden && !menuPanel.contains(e.target) && e.target !== menuBtn) {
      setMenuOpen(false);
    }
  });
  // Close when a menu item is selected (link click or logout button)
  menuPanel.addEventListener("click", () => setMenuOpen(false));
  // Close on Escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !menuPanel.hidden) setMenuOpen(false);
  });
  // Close on route change as a safety net
  window.addEventListener("hashchange", () => setMenuOpen(false));

  function setLogoutVisible(v) {
    headerNav.hidden = !v;
    if (!v) setMenuOpen(false);
  }
  logoutBtn.addEventListener("click", async () => {
    // Best-effort: tell the server to invalidate the token, but always clear
    // the local copy so the user is logged out client-side even if offline.
    try { await api.revokeSession(); } catch (_) {}
    api.clearToken();
    phoneInFlight.clear();
    // If the hash is already "#/", setting it again won't fire hashchange,
    // so call go() directly to re-route into the welcome view.
    if (location.hash === "" || location.hash === "#/") go();
    else location.hash = "#/";
  });

  // ───────── Routes ─────────
  async function go() {
    const route = (location.hash || "#/").slice(2); // strip "#/"

    try {
      // Public routes first
      if (route.startsWith("auth/code")) return showCode();
      if (route === "" && !api.getToken()) return showWelcome();

      // Authenticated routes — verify session
      if (!api.getToken()) return showWelcome();
      let me;
      try {
        me = await api.me();
      } catch (e) {
        if (e.status === 404) return showOnboarding();
        if (e.status === 401) return showWelcome();
        throw e;
      }
      setLogoutVisible(true);

      if (route === "" || route === "home") return showHome(me);
      if (route === "onboarding") return showOnboarding();
      if (route === "settings") return showSettings(me);
      if (route === "seasons") return showSeasons(me);
      if (route === "history") return showHistory(me);
      if (route === "docs") return showDocs();
      const docMatch = route.match(/^docs\/(.+)$/);
      if (docMatch) return showDocPage(docMatch[1]);

      // Season-scoped routes — order matters (longest first).
      const sChat = route.match(/^season\/([^/]+)\/plan\/(\d+)\/chat$/);
      if (sChat) return showChat(me, sChat[1], parseInt(sChat[2], 10));
      const sPlanV = route.match(/^season\/([^/]+)\/plan\/(\d+)$/);
      if (sPlanV) return showPlanVersion(me, sPlanV[1], parseInt(sPlanV[2], 10));
      const sLatest = route.match(/^season\/([^/]+)\/plan$/);
      if (sLatest) return showLatestPlan(me, sLatest[1]);
      const sPlans = route.match(/^season\/([^/]+)\/plans$/);
      if (sPlans) return showPlanHistory(me, sPlans[1]);
      const sQuiz = route.match(/^season\/([^/]+)$/);
      if (sQuiz) return showQuestionnaire(me, sQuiz[1]);

      // Backward-compat: old top-level plan routes redirect to the picker.
      if (route === "plans" || route === "plan" ||
          route.startsWith("plan/")) {
        location.hash = "#/seasons";
        return;
      }
      // unknown — back home
      return showHome(me);
    } catch (e) {
      console.error(e);
      show(views.error(e.message || "Unexpected error."));
    }
  }

  // ───────── Welcome → code → onboarding flow ─────────
  function showWelcome() {
    setLogoutVisible(false);
    show(views.welcome(async (phone) => {
      try {
        await api.startCode(phone);
        phoneInFlight.set(phone);
        location.hash = "#/auth/code";
      } catch (e) { views.toast(e.message, "error"); }
    }));
  }

  function showCode() {
    setLogoutVisible(false);
    const phone = phoneInFlight.get();
    if (!phone) { location.hash = "#/"; return; }
    show(views.code(
      phone,
      async (code) => {
        try {
          const res = await api.verifyCode(phone, code);
          api.setToken(res.session_token);
          if (res.needs_onboarding) {
            // Keep phoneInFlight — the onboarding form needs it for POST /me/onboard.
            location.hash = "#/onboarding";
          } else {
            phoneInFlight.clear();
            location.hash = "#/home";
          }
        } catch (e) { views.toast(e.message, "error"); }
      },
      async () => {
        try { await api.startCode(phone); views.toast("New code sent."); }
        catch (e) { views.toast(e.message, "error"); }
      },
    ));
  }

  async function showOnboarding() {
    setLogoutVisible(true);
    // The onboarding form needs the verified phone to send to POST /me/onboard.
    // Most arrivals come straight from /auth/verify and have it in sessionStorage.
    // If a user lost it (cleared session storage, switched browsers), fall back
    // to asking them to sign in again — we deliberately don't expose the phone
    // anywhere readable from /me, so reverification is the right path.
    const phone = phoneInFlight.get();
    if (!phone) {
      views.toast("Please sign in again to finish setting up your account.", "error");
      api.clearToken();
      return showWelcome();
    }
    show(views.onboarding(phone, async (data) => {
      try {
        await api.onboard(data);
        phoneInFlight.clear();
        location.hash = "#/seasons";
      } catch (e) { views.toast(e.message, "error"); }
    }));
  }

  // ───────── Settings ─────────
  async function showSettings(me) {
    show(views.settings(
      me,
      async (data) => {
        try {
          await api.updateMe(data);
          views.toast("Saved.");
          location.hash = "#/home";
        } catch (e) { views.toast(e.message, "error"); }
      },
      async () => {
        try {
          await api.deleteMe();
        } catch (e) {
          // Even if the call fails, log out locally — the user wants out.
          console.error(e);
        }
        api.clearToken();
        phoneInFlight.clear();
        views.toast("Your account has been deleted.");
        location.hash = "#/";
      },
    ));
  }

  // ───────── Home / seasons / history ─────────
  async function showHome(me) {
    show(views.loading());
    let mine = [];
    try { mine = (await api.mySeasons()).seasons; } catch (e) {}
    show(views.home(me, mine));
  }

  async function showSeasons(me) {
    show(views.loading("Loading seasons…"));
    const [packs, mineRes] = await Promise.all([
      api.seasons(),
      api.mySeasons().catch(() => ({ seasons: [] })),
    ]);
    const mineById = new Map(mineRes.seasons.map(s => [s.season_id, s]));
    show(views.seasons(packs, mineById));
  }

  async function showHistory(me) {
    show(views.loading("Loading your plans…"));
    const mine = (await api.mySeasons()).seasons;
    show(views.history(mine));
  }

  async function showDocs() {
    show(views.loading("Loading docs…"));
    const docs = await api.listDocs();
    show(views.docsIndex(docs));
  }

  async function showDocPage(slug) {
    show(views.loading("Loading…"));
    let doc;
    try { doc = await api.getDoc(slug); }
    catch (e) {
      if (e.status === 404) {
        views.toast("Doc not found.", "error");
        location.hash = "#/docs";
        return;
      }
      throw e;
    }
    show(views.docPage(doc));
  }

  // ───────── Questionnaire ─────────
  async function showQuestionnaire(me, seasonId) {
    show(views.loading("Loading your questions…"));
    const [pack, current] = await Promise.all([
      api.questions(seasonId),
      api.getAnswers(seasonId),
    ]);
    const node = views.questionnaire(
      pack,
      current.answers,
      current.completion,
      async (key, value) => {
        const r = await api.putAnswers(seasonId, { [key]: value });
        return r;
      },
      async () => {
        show(views.generating(me));
        try {
          await api.generatePlan(seasonId);
          location.hash = `#/season/${seasonId}/plan`;
        } catch (e) {
          show(views.error(e.message));
        }
      },
    );
    show(node);
  }

  // ───────── Plan ─────────
  async function showLatestPlan(me, seasonId) {
    show(views.loading("Loading your plan…"));
    let p, list;
    try {
      [p, list] = await Promise.all([
        api.latestPlan(seasonId),
        api.listPlans(seasonId),
      ]);
    } catch (e) {
      if (e.status === 404) { location.hash = "#/season/" + seasonId; return; }
      throw e;
    }
    renderPlan(me, seasonId, p, list.versions.length);
  }

  async function showPlanVersion(me, seasonId, version) {
    show(views.loading(`Loading plan v${version}…`));
    let p, list;
    try {
      [p, list] = await Promise.all([
        api.getPlan(seasonId, version),
        api.listPlans(seasonId),
      ]);
    } catch (e) {
      if (e.status === 404) {
        views.toast(`No plan v${version} found.`, "error");
        location.hash = `#/season/${seasonId}/plans`;
        return;
      }
      throw e;
    }
    renderPlan(me, seasonId, p, list.versions.length);
  }

  function renderPlan(me, seasonId, p, totalVersions) {
    show(views.plan(
      me,
      seasonId,
      p.markdown,
      (p.meta && p.meta.sources) || [],
      p.version,
      totalVersions,
      async () => {
        show(views.generating(me));
        try {
          await api.generatePlan(seasonId);
          location.hash = `#/season/${seasonId}/plan`;
          go();
        } catch (e) { show(views.error(e.message)); }
      },
      () => { location.hash = "#/season/" + seasonId; },
    ));
  }

  async function showChat(me, seasonId, version) {
    show(views.loading("Loading your conversation…"));
    let history, planRes;
    try {
      [history, planRes] = await Promise.all([
        api.getChat(seasonId, version),
        api.getPlan(seasonId, version),
      ]);
    } catch (e) {
      if (e.status === 404) { location.hash = `#/season/${seasonId}/plans`; return; }
      throw e;
    }
    show(views.chat(
      me, seasonId, version, history.turns, planRes.markdown,
      async (text) => api.sendChat(seasonId, version, text),
      async () => {
        show(views.generating(me));
        try {
          const newPlan = await api.regenerateFromChat(seasonId, version);
          location.hash = `#/season/${seasonId}/plan/${newPlan.version}`;
          go();
        } catch (e) { show(views.error(e.message)); }
      },
    ));
  }

  async function showPlanHistory(me, seasonId) {
    show(views.loading("Loading your plans…"));
    const list = await api.listPlans(seasonId);
    if (!list.versions.length) {
      location.hash = "#/season/" + seasonId;
      return;
    }
    const fmt = (ts) => {
      if (!ts) return "—";
      const d = new Date(ts * 1000);
      return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) +
        " · " + d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
    };
    show(views.planHistory(
      list.versions.map(v => ({ version: v.version, date: fmt(v.generated_at) }))
    ));
  }

  window.addEventListener("hashchange", go);
  window.addEventListener("DOMContentLoaded", go);
})();
