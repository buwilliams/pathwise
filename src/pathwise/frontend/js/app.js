// Hash router + state. Single page; views live in views.js.

(() => {
  const root = document.getElementById("view");
  const logoutBtn = document.getElementById("logout-btn");
  const headerNav = document.getElementById("header-nav");
  const SEASON = "transition-to-adulthood"; // only one for now

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

  function setLogoutVisible(v) { headerNav.hidden = !v; }
  logoutBtn.addEventListener("click", async () => {
    // Best-effort: tell the server to invalidate the token, but always clear
    // the local copy so the user is logged out client-side even if offline.
    try { await api.revokeSession(); } catch (_) {}
    api.clearToken();
    phoneInFlight.clear();
    location.hash = "#/";
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
      if (route.startsWith("season/")) return showQuestionnaire(me, SEASON);
      if (route === "plans") return showPlanHistory(me, SEASON);
      if (route === "plan") return showLatestPlan(me, SEASON);
      const planMatch = route.match(/^plan\/(\d+)$/);
      if (planMatch) return showPlanVersion(me, SEASON, parseInt(planMatch[1], 10));
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
          phoneInFlight.clear();
          if (res.needs_onboarding) location.hash = "#/onboarding";
          else location.hash = "#/home";
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
        location.hash = "#/season/" + SEASON;
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

  // ───────── Home ─────────
  async function showHome(me) {
    show(views.loading());
    let versions = [];
    try { versions = (await api.listPlans(SEASON)).versions; } catch (e) {}
    show(views.home(me, versions.length ? versions[versions.length - 1] : null));
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
          location.hash = "#/plan";
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
        location.hash = "#/plans";
        return;
      }
      throw e;
    }
    renderPlan(me, seasonId, p, list.versions.length);
  }

  function renderPlan(me, seasonId, p, totalVersions) {
    show(views.plan(
      me,
      p.markdown,
      (p.meta && p.meta.sources) || [],
      p.version,
      totalVersions,
      async () => {
        show(views.generating(me));
        try {
          await api.generatePlan(seasonId);
          location.hash = "#/plan";
          go();
        } catch (e) { show(views.error(e.message)); }
      },
      () => { location.hash = "#/season/" + seasonId; },
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
