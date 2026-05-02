// Hash router + state. Single page; views live in views.js.

(() => {
  const root = document.getElementById("view");
  const logoutBtn = document.getElementById("logout-btn");
  const SEASON = "transition-to-adulthood"; // only one for now
  let phoneInFlight = ""; // remembered between welcome → code

  function show(node) {
    root.replaceChildren(node);
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  function setLogoutVisible(v) { logoutBtn.hidden = !v; }
  logoutBtn.addEventListener("click", () => {
    api.clearToken();
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
      if (route.startsWith("season/")) return showQuestionnaire(me, SEASON);
      if (route === "plan") return showLatestPlan(me, SEASON);
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
        phoneInFlight = phone;
        location.hash = "#/auth/code";
      } catch (e) { views.toast(e.message, "error"); }
    }));
  }

  function showCode() {
    setLogoutVisible(false);
    if (!phoneInFlight) { location.hash = "#/"; return; }
    show(views.code(
      phoneInFlight,
      async (code) => {
        try {
          const res = await api.verifyCode(phoneInFlight, code);
          api.setToken(res.session_token);
          if (res.needs_onboarding) location.hash = "#/onboarding";
          else location.hash = "#/home";
        } catch (e) { views.toast(e.message, "error"); }
      },
      async () => {
        try { await api.startCode(phoneInFlight); views.toast("New code sent."); }
        catch (e) { views.toast(e.message, "error"); }
      },
    ));
  }

  function showOnboarding() {
    setLogoutVisible(true);
    show(views.onboarding(phoneInFlight, async (data) => {
      try {
        // If we're refreshing onboarding without a fresh phone in flight, get it from /me lookup
        if (!data.phone) {
          views.toast("Phone is missing; please sign in again.", "error");
          api.clearToken();
          return showWelcome();
        }
        await api.onboard(data);
        location.hash = "#/season/" + SEASON;
      } catch (e) { views.toast(e.message, "error"); }
    }));
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
    let p;
    try { p = await api.latestPlan(seasonId); }
    catch (e) {
      if (e.status === 404) { location.hash = "#/season/" + seasonId; return; }
      throw e;
    }
    show(views.plan(
      me,
      p.markdown,
      (p.meta && p.meta.sources) || [],
      p.version,
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

  window.addEventListener("hashchange", go);
  window.addEventListener("DOMContentLoaded", go);
})();
