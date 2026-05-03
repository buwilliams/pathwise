// View renderers. Each returns an HTMLElement (or string) and wires its events
// inside its render function. Routing & state lives in app.js.

const views = (() => {
  const el = (tag, attrs = {}, ...children) => {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "class") e.className = v;
      else if (k === "html") e.innerHTML = v;
      else if (k.startsWith("on") && typeof v === "function") e.addEventListener(k.slice(2), v);
      else if (v === true) e.setAttribute(k, "");
      else if (v !== false && v != null) e.setAttribute(k, v);
    }
    for (const c of children) {
      if (c == null || c === false) continue;
      e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    }
    return e;
  };

  const card = (...children) => el("div", { class: "card" }, ...children);

  function toast(msg, type = "info") {
    const t = document.getElementById("toast");
    t.textContent = msg;
    t.className = "toast" + (type === "error" ? " error" : "");
    t.hidden = false;
    clearTimeout(toast._h);
    toast._h = setTimeout(() => { t.hidden = true; }, 3500);
  }

  // ───────── Welcome / phone entry ─────────
  function welcome(onSubmit) {
    let phone = "";
    const submit = el("button", { class: "btn", onclick: () => onSubmit(phone) }, "Continue");
    submit.disabled = true;

    return card(
      el("h1", {}, "pathwise"),
      el("div", { class: "dotted-path" }, "···●···●···●···▶"),
      el("p", { class: "tagline" }, "one step at a time, on purpose."),
      el("p", { class: "lede" }, "A small space to think clearly about your money, your time, and what's next."),
      el("div", { class: "field" },
        el("label", { for: "phone" }, "Your phone number"),
        el("input", {
          id: "phone", type: "tel", autocomplete: "tel",
          placeholder: "(555) 555-0100", inputmode: "tel",
          oninput: (e) => { phone = e.target.value; submit.disabled = phone.replace(/\D/g, "").length < 10; },
        }),
        el("p", { class: "help" }, "We'll text you a one-time code. We never share your number."),
      ),
      el("div", { class: "btn-row" }, submit),
    );
  }

  // ───────── Code entry ─────────
  function code(phone, onSubmit, onResend) {
    let value = "";
    const submit = el("button", { class: "btn", onclick: () => onSubmit(value) }, "Verify");
    submit.disabled = true;

    return card(
      el("h2", {}, "Enter your code"),
      el("p", { class: "lede" }, `We sent a 6-digit code to ${phone}.`),
      el("div", { class: "field" },
        el("label", { for: "code" }, "Code"),
        el("input", {
          id: "code", type: "text", inputmode: "numeric", autocomplete: "one-time-code",
          maxlength: "6", placeholder: "123456",
          oninput: (e) => {
            value = e.target.value.replace(/\D/g, "").slice(0, 6);
            e.target.value = value;
            submit.disabled = value.length !== 6;
          },
        }),
      ),
      el("div", { class: "btn-row" },
        submit,
        el("button", { class: "text-btn", onclick: onResend }, "Send again"),
      ),
    );
  }

  // ───────── Onboarding ─────────
  function onboarding(phone, onSubmit) {
    const data = { phone, first_name: "", gender: "", zip_code: "" };
    const submit = el("button", { class: "btn btn-accent", onclick: () => onSubmit(data) }, "Start");
    function refresh() {
      submit.disabled = !(data.first_name.trim() && data.gender);
    }
    refresh();

    const genderRadio = (value, label) =>
      el("label", { class: "choice-item" },
        el("input", {
          type: "radio", name: "gender", value,
          onchange: () => {
            data.gender = value;
            document.querySelectorAll(".choice-item").forEach(c => c.classList.remove("selected"));
            const checked = document.querySelector(`input[name="gender"]:checked`);
            if (checked) checked.closest(".choice-item").classList.add("selected");
            refresh();
          },
        }),
        el("span", { class: "label" }, label),
      );

    return card(
      el("h2", {}, "Nice to meet you."),
      el("p", { class: "lede" }, "Just a few things — we keep this small on purpose."),
      el("div", { class: "field" },
        el("label", { for: "name" }, "First name"),
        el("input", {
          id: "name", type: "text", autocomplete: "given-name",
          placeholder: "Your name",
          oninput: (e) => { data.first_name = e.target.value; refresh(); },
        }),
      ),
      el("div", { class: "field", role: "radiogroup", "aria-labelledby": "onb-gender-label" },
        // Not a <label> — there's no single input to associate with; the
        // radios inside genderRadio carry their own labels.
        el("div", { id: "onb-gender-label", class: "field-label" }, "Gender"),
        el("div", { class: "choice-list" },
          genderRadio("female", "Female"),
          genderRadio("male", "Male"),
          genderRadio("non-binary", "Non-binary"),
        ),
      ),
      el("div", { class: "field" },
        el("label", { for: "zip" }, "ZIP code (optional)"),
        el("p", { class: "help" }, "Helps us look up real prices and programs near you."),
        el("input", {
          id: "zip", type: "text", inputmode: "numeric", maxlength: "5",
          autocomplete: "postal-code",
          placeholder: "5 digits",
          oninput: (e) => { data.zip_code = e.target.value.replace(/\D/g, "").slice(0, 5); e.target.value = data.zip_code; },
        }),
      ),
      el("div", { class: "btn-row" }, submit),
    );
  }

  // ───────── Home ─────────
  function home(profile, mySeasons) {
    const formatAge = (s) =>
      s.age_min && s.age_max ? `Ages ${s.age_min}–${s.age_max}` : "";
    const fmtDate = (ts) => ts
      ? new Date(ts * 1000).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
      : "—";
    const fmtElapsed = (startedAt) => {
      if (!startedAt) return "";
      const seconds = Math.max(1, Math.floor(Date.now() / 1000 - startedAt));
      if (seconds < 60) return `${seconds}s ago`;
      return `${Math.floor(seconds / 60)}m ago`;
    };

    function seasonCard(s) {
      // Mid-flight: link goes nowhere, show spinner + elapsed + last error if any
      if (s.generating) {
        const card = el("div", { class: "season-row season-row-busy" },
          el("div", { class: "season-row-head" },
            el("span", { class: "season-row-name" }, s.name),
            el("span", { class: "season-row-age" }, formatAge(s)),
          ),
          el("p", { class: "season-row-meta" },
            el("span", { class: "spinner" }),
            (s.from_chat ? "Updating from your conversation… " : "Building your plan… ") +
            `(started ${fmtElapsed(s.started_at)}, usually 2–4 min)`,
          ),
        );
        return card;
      }

      const linkTarget = s.latest_version
        ? `#/season/${s.season_id}/plan`
        : `#/season/${s.season_id}`;
      const meta = s.latest_version
        ? `${s.plan_count} plan${s.plan_count === 1 ? "" : "s"} · last updated ${fmtDate(s.latest_at)}` +
          (s.chat_count ? ` · ${s.chat_count} conversation${s.chat_count === 1 ? "" : "s"}` : "")
        : "No plan yet — finish answering to generate one";

      const head = el("div", { class: "season-row-head" },
        el("span", { class: "season-row-name" }, s.name),
        el("span", { class: "season-row-age" }, formatAge(s)),
      );
      if (s.newer_revision_available) {
        head.appendChild(el("span", { class: "revision-pill" }, "season updated"));
      }

      const node = el("a", { class: "season-row", href: linkTarget },
        head,
        el("p", { class: "season-row-meta" }, meta),
      );
      if (s.last_error) {
        node.appendChild(el("p", { class: "season-row-error" },
          `Last attempt failed: ${s.last_error}`,
        ));
      }
      return node;
    }

    const inProgress = mySeasons.length
      ? card(
          el("h2", {}, "Your seasons"),
          el("div", { class: "season-list" }, ...mySeasons.map(seasonCard)),
        )
      : null;

    return el("div", {},
      card(
        el("h1", {}, `Hey, ${profile.first_name}.`),
        el("p", { class: "tagline" }, "one step at a time, on purpose."),
        mySeasons.length
          ? el("p", { class: "lede" }, "Pick up where you left off, or start a new season.")
          : el("p", { class: "lede" }, "Pick a season of life to start. About 10 minutes of questions, then a real plan."),
        el("div", { class: "btn-row" },
          el("a", {
            class: "btn btn-accent",
            href: "#/seasons",
          }, mySeasons.length ? "Browse seasons" : "Choose a season"),
          mySeasons.length
            ? el("a", { class: "btn btn-secondary", href: "#/history" }, "Plan history")
            : null,
        ),
      ),
      inProgress,
    );
  }

  // ───────── Season picker ─────────
  function seasons(packs, mySeasonsById) {
    const formatAge = (p) =>
      p.age_min && p.age_max ? `Recommended ages ${p.age_min}–${p.age_max}` : "";

    const cards = packs.map(p => {
      const mine = mySeasonsById.get(p.id);
      const cta = mine
        ? el("a", { class: "btn btn-accent", href: `#/season/${p.id}/plan` }, "View latest plan")
        : el("a", { class: "btn btn-accent", href: `#/season/${p.id}` }, "Start");
      const secondary = mine
        ? el("a", { class: "btn btn-secondary", href: `#/season/${p.id}` }, "Revise answers")
        : null;
      return card(
        el("h2", {}, p.name),
        el("p", { class: "season-age" }, formatAge(p)),
        el("p", { class: "lede" }, p.summary),
        mine ? el("p", { class: "season-row-meta" },
          `${mine.plan_count} plan${mine.plan_count === 1 ? "" : "s"}` +
          (mine.chat_count ? ` · ${mine.chat_count} conversation${mine.chat_count === 1 ? "" : "s"}` : ""),
        ) : null,
        el("div", { class: "btn-row" }, cta, secondary),
      );
    });

    return el("div", {},
      card(
        el("h1", {}, "Seasons of life"),
        el("p", { class: "lede" }, "Each season is a different chapter, with its own questions and tradeoffs. Pick the one that fits where you are now."),
      ),
      ...cards,
    );
  }

  // ───────── Cross-season history ─────────
  function history(mySeasons) {
    if (!mySeasons.length) {
      return card(
        el("h2", {}, "No plans yet"),
        el("p", { class: "lede" }, "Once you finish a season, your plans and conversations will live here."),
        el("div", { class: "btn-row" },
          el("a", { class: "btn btn-accent", href: "#/seasons" }, "Choose a season"),
        ),
      );
    }
    const fmt = (ts) => ts
      ? new Date(ts * 1000).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
      : "—";
    return el("div", {},
      card(
        el("h1", {}, "Plan history"),
        el("p", { class: "lede" }, "Every season you've worked through, with its plans and conversations."),
      ),
      ...mySeasons.map(s => card(
        el("h2", {}, s.name),
        el("p", { class: "season-row-meta" },
          `${s.plan_count} plan${s.plan_count === 1 ? "" : "s"} · last updated ${fmt(s.latest_at)}` +
          (s.chat_count ? ` · ${s.chat_count} conversation${s.chat_count === 1 ? "" : "s"}` : ""),
        ),
        el("div", { class: "btn-row" },
          el("a", { class: "btn btn-accent", href: `#/season/${s.season_id}/plan` }, "Read latest plan"),
          el("a", { class: "btn btn-secondary", href: `#/season/${s.season_id}/plans` }, "All versions"),
        ),
      )),
    );
  }

  // ───────── Questionnaire (one section per step) ─────────
  function questionnaire(pack, answers, completion, onAnswer, onGenerate) {
    const root = el("div", {});
    const sections = pack.sections.filter(sec =>
      pack.questions.some(q => q.section === sec.id)
    );
    const totalSteps = sections.length;
    let currentIdx = 0;
    let isComplete = !!completion.is_complete;

    const stepLabel = el("p", { class: "progress-label", style: "margin-bottom: var(--space-2);" }, "");
    const progressBar = el("span", { style: `width: ${completion.percent}%` });
    let currentPct = completion.percent;

    function updateStepLabel() {
      stepLabel.textContent = `Step ${currentIdx + 1} of ${totalSteps} (${currentPct}%)`;
    }
    function setProgress(pct) {
      currentPct = pct;
      progressBar.style.width = pct + "%";
      updateStepLabel();
    }

    root.appendChild(el("div", {},
      stepLabel,
      el("div", { class: "progress" }, progressBar),
    ));

    const body = el("div", {});
    root.appendChild(body);

    function renderStep() {
      const sec = sections[currentIdx];
      const isLast = currentIdx === totalSteps - 1;
      updateStepLabel();

      const sectionQs = pack.questions.filter(q => q.section === sec.id);
      const sectionEl = card(
        el("h2", {}, sec.title),
        sec.blurb && el("p", { class: "section-blurb" }, sec.blurb),
        ...sectionQs.map(q => questionField(q, answers[q.key], async (val) => {
          try {
            const res = await onAnswer(q.key, val);
            answers[q.key] = res.answers[q.key];
            isComplete = !!res.completion.is_complete;
            setProgress(res.completion.percent);
            if (isLast) primaryBtn.disabled = !isComplete;
          } catch (e) { toast(e.message, "error"); }
        })),
      );

      const backBtn = el("button", {
        class: "btn btn-secondary",
        onclick: () => { if (currentIdx > 0) { currentIdx -= 1; renderStep(); } },
      }, "Back");
      backBtn.disabled = currentIdx === 0;

      const primaryBtn = isLast
        ? el("button", { class: "btn btn-accent", onclick: onGenerate }, "Generate my plan")
        : el("button", {
            class: "btn",
            onclick: () => { currentIdx += 1; renderStep(); },
          }, "Next");
      if (isLast) primaryBtn.disabled = !isComplete;

      const nav = el("div", {
        class: "btn-row",
        style: "flex-direction: row; gap: var(--space-3); margin-top: var(--space-4);",
      }, backBtn, primaryBtn);

      body.replaceChildren(sectionEl, nav);
      window.scrollTo({ top: 0, behavior: "instant" });
    }

    renderStep();
    return root;
  }

  function questionField(q, currentValue, onChange) {
    // Only `text` and the numeric variants render a single input we can
    // associate with via for=. Group-style answers (single_choice,
    // multi_choice, yes_no, scale) get a non-label heading so we don't emit
    // an orphan <label for> that points at no element.
    const labelText = q.prompt + (q.required ? "" : "  (optional)");
    const labelHasMatchingInput =
      q.type === "text" || q.type === "number" ||
      q.type === "money" || q.type === "hours";
    const fieldAttrs = labelHasMatchingInput
      ? { class: "field" }
      : { class: "field", role: "group", "aria-labelledby": `qlabel-${q.key}` };
    const wrap = el("div", fieldAttrs,
      labelHasMatchingInput
        ? el("label", { for: `q-${q.key}` }, labelText)
        : el("div", { id: `qlabel-${q.key}`, class: "field-label" }, labelText),
      q.help && el("p", { class: "help" }, q.help),
    );

    if (q.type === "single_choice") {
      const list = el("div", { class: "choice-list" });
      for (const opt of q.options) {
        const item = el("label", { class: "choice-item" + (currentValue === opt.value ? " selected" : "") },
          el("input", {
            type: "radio", name: q.key, value: opt.value,
            checked: currentValue === opt.value,
            onchange: () => {
              list.querySelectorAll(".choice-item").forEach(c => c.classList.remove("selected"));
              item.classList.add("selected");
              onChange(opt.value);
            },
          }),
          el("span", { class: "label" }, opt.label),
        );
        list.appendChild(item);
      }
      wrap.appendChild(list);
    } else if (q.type === "multi_choice") {
      const list = el("div", { class: "choice-list" });
      const selected = new Set(currentValue || []);
      for (const opt of q.options) {
        const item = el("label", { class: "choice-item" + (selected.has(opt.value) ? " selected" : "") },
          el("input", {
            type: "checkbox", value: opt.value,
            checked: selected.has(opt.value),
            onchange: (e) => {
              if (e.target.checked) selected.add(opt.value); else selected.delete(opt.value);
              item.classList.toggle("selected", e.target.checked);
              onChange(Array.from(selected));
            },
          }),
          el("span", { class: "label" }, opt.label),
        );
        list.appendChild(item);
      }
      wrap.appendChild(list);
    } else if (q.type === "yes_no") {
      const list = el("div", { class: "choice-list" });
      for (const [val, label] of [[true, "Yes"], [false, "No"]]) {
        const item = el("label", { class: "choice-item" + (currentValue === val ? " selected" : "") },
          el("input", {
            type: "radio", name: q.key, checked: currentValue === val,
            onchange: () => {
              list.querySelectorAll(".choice-item").forEach(c => c.classList.remove("selected"));
              item.classList.add("selected");
              onChange(val);
            },
          }),
          el("span", { class: "label" }, label),
        );
        list.appendChild(item);
      }
      wrap.appendChild(list);
    } else if (q.type === "scale") {
      const min = q.min || 1, max = q.max || 5;
      const row = el("div", { class: "scale-row" });
      row.appendChild(el("span", { class: "scale-end" }, "Low"));
      for (let v = min; v <= max; v++) {
        const btn = el("button", {
          type: "button",
          class: "scale-btn" + (currentValue === v ? " selected" : ""),
          onclick: () => {
            row.querySelectorAll(".scale-btn").forEach(b => b.classList.remove("selected"));
            btn.classList.add("selected");
            onChange(v);
          },
        }, String(v));
        row.appendChild(btn);
      }
      row.appendChild(el("span", { class: "scale-end" }, "High"));
      wrap.appendChild(row);
    } else if (q.type === "text") {
      const ta = el("textarea", {
        id: `q-${q.key}`, rows: "2", placeholder: q.placeholder || "",
        oninput: (e) => onChangeDebounced(e.target.value),
      });
      if (currentValue) ta.value = currentValue;
      wrap.appendChild(ta);
      let timer;
      function onChangeDebounced(v) {
        clearTimeout(timer);
        timer = setTimeout(() => onChange(v), 600);
      }
    } else { // number, money, hours
      const prefix = q.type === "money" ? "$" : "";
      const suffix = q.unit ? ` ${q.unit}` : "";
      const input = el("input", {
        id: `q-${q.key}`, type: "number", inputmode: "decimal",
        min: q.min, max: q.max,
        placeholder: prefix + (q.type === "money" ? "1000" : "") + suffix,
        oninput: (e) => onChangeDebounced(e.target.value),
      });
      if (currentValue !== undefined && currentValue !== null) input.value = currentValue;
      wrap.appendChild(input);
      let timer;
      function onChangeDebounced(v) {
        clearTimeout(timer);
        if (v === "") return;
        timer = setTimeout(() => onChange(v), 500);
      }
    }
    return wrap;
  }

  // ───────── Plan ─────────
  function revisionBanner(revisionStatus) {
    if (!revisionStatus || !revisionStatus.newer_available) return null;
    return el("div", { class: "revision-banner", role: "status" },
      `A newer version of this season is available (v${revisionStatus.latest_revision}). ` +
      `Generating a new plan will use the new version.`,
    );
  }

  function plan(profile, seasonId, planText, sources, version, totalVersions, onRegenerate, onRevise, revisionStatus) {
    const html = md.render(planText);
    return el("div", {},
      revisionBanner(revisionStatus),
      el("div", { class: "plan-content", html }),
      sources && sources.length ? el("details", { class: "sources" },
        el("summary", {}, `Sources (${sources.length})`),
        el("ul", {}, ...sources.map(u => el("li", {}, el("a", { href: u, target: "_blank", rel: "noopener noreferrer" }, u)))),
      ) : null,
      el("div", { class: "btn-row" },
        el("a", { class: "btn btn-accent", href: `#/season/${seasonId}/plan/${version}/chat` }, "Talk it through"),
        el("button", { class: "btn btn-secondary", onclick: onRevise }, "Revise my answers"),
        el("button", { class: "btn", onclick: onRegenerate }, "Generate a new version"),
      ),
      el("p", { class: "progress-label" },
        `Plan v${version}` +
          (revisionStatus && revisionStatus.plan_revision ? ` · pack v${revisionStatus.plan_revision}` : "") +
          (totalVersions > 1 ? ` of ${totalVersions} — ` : ""),
        totalVersions > 1 ? el("a", { href: `#/season/${seasonId}/plans` }, "view all versions") : null,
      ),
    );
  }

  // ───────── Chat ─────────
  function chat(profile, seasonId, version, initialTurns, planMarkdown, onSend, onRegenerate, revisionStatus) {
    const root = el("div", {});
    let userTurnCount = 0;
    let regenBtn;  // assigned later; guarded inside appendTurn
    const banner = revisionBanner(revisionStatus);
    if (banner) root.appendChild(banner);
    root.appendChild(card(
      el("h2", {}, `Talk it through`),
      el("p", { class: "lede" },
        `Ask anything about your plan v${version}. Push back, explore alternatives, or work through a tradeoff. ` +
        `It knows the model and your numbers.`
      ),
      el("details", { class: "chat-plan" },
        el("summary", {}, "View plan"),
        el("div", { class: "plan-content", html: md.render(planMarkdown || "") }),
      ),
    ));

    const messagesEl = el("div", { class: "chat-messages" });
    const turnEls = new Map();

    function bubbleFor(turn) {
      const wrap = el("div", { class: `chat-bubble chat-${turn.role}` });
      const body = el("div", { class: "chat-body" });
      // Render assistant turns through markdown so lists/emphasis work.
      if (turn.role === "assistant") body.innerHTML = md.render(turn.text);
      else body.textContent = turn.text;
      wrap.appendChild(body);
      return { wrap, body };
    }
    function appendTurn(turn) {
      const { wrap } = bubbleFor(turn);
      messagesEl.appendChild(wrap);
      turnEls.set(turn, wrap);
      messagesEl.scrollTop = messagesEl.scrollHeight;
      if (turn.role === "user") {
        userTurnCount += 1;
        if (regenBtn) regenBtn.disabled = false;
      }
      return wrap;
    }

    if (initialTurns.length === 0) {
      messagesEl.appendChild(el("p", { class: "chat-empty" },
        "No messages yet. Try: \"What's the riskiest part of this plan?\""));
    }
    initialTurns.forEach(appendTurn);

    root.appendChild(messagesEl);

    let pending = false;
    const input = el("textarea", {
      class: "chat-input",
      rows: "2",
      placeholder: "Ask a question…",
      "aria-label": "Message",
      onkeydown: (e) => {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
      },
    });
    const sendBtn = el("button", { class: "btn", onclick: () => submit() }, "Send");

    async function submit() {
      const text = input.value.trim();
      if (!text || pending) return;
      // Drop the empty hint if it's still there.
      const empty = messagesEl.querySelector(".chat-empty");
      if (empty) empty.remove();

      pending = true;
      sendBtn.disabled = true;
      input.disabled = true;

      const userTurn = { role: "user", text, at: Date.now() / 1000 };
      appendTurn(userTurn);
      input.value = "";

      const thinking = el("div", { class: "chat-bubble chat-assistant chat-thinking" },
        el("span", { class: "spinner" }), "Thinking…",
      );
      messagesEl.appendChild(thinking);
      messagesEl.scrollTop = messagesEl.scrollHeight;

      try {
        const res = await onSend(text);
        thinking.remove();
        appendTurn(res.assistant);
      } catch (e) {
        thinking.remove();
        toast(e.message, "error");
      } finally {
        pending = false;
        sendBtn.disabled = false;
        input.disabled = false;
        input.focus();
      }
    }

    root.appendChild(el("div", { class: "chat-composer" }, input, sendBtn));

    regenBtn = el("button", {
      class: "btn btn-accent",
      onclick: () => onRegenerate(),
    }, "Update plan from this conversation");
    regenBtn.disabled = userTurnCount === 0;

    root.appendChild(el("div", { class: "btn-row" },
      regenBtn,
      el("a", { class: "btn btn-secondary", href: `#/season/${seasonId}/plan/${version}` }, "Back to plan"),
    ));

    setTimeout(() => input.focus(), 50);
    return root;
  }

  // ───────── Settings (edit profile + delete account) ─────────
  function settings(profile, onSave, onDelete) {
    const data = {
      first_name: profile.first_name,
      gender: profile.gender,
      zip_code: profile.zip_code || "",
    };
    let dirty = false;
    const save = el("button", { class: "btn", onclick: () => onSave(data) }, "Save changes");
    save.disabled = true;
    const markDirty = () => { dirty = true; save.disabled = false; };

    const genderRadio = (value, label) =>
      el("label", { class: "choice-item" + (data.gender === value ? " selected" : "") },
        el("input", {
          type: "radio", name: "gender", value, checked: data.gender === value,
          onchange: (e) => {
            data.gender = value;
            e.target.closest(".choice-list").querySelectorAll(".choice-item")
              .forEach(c => c.classList.remove("selected"));
            e.target.closest(".choice-item").classList.add("selected");
            markDirty();
          },
        }),
        el("span", { class: "label" }, label),
      );

    // Two-step delete confirmation lives inside the danger-zone card.
    let deleteArmed = false;
    const deleteBtn = el("button", { class: "btn btn-danger", onclick: () => {
      if (!deleteArmed) {
        deleteArmed = true;
        deleteBtn.textContent = "Tap again to confirm — this can't be undone";
        setTimeout(() => {
          if (deleteArmed) {
            deleteArmed = false;
            deleteBtn.textContent = "Delete my account";
          }
        }, 5000);
        return;
      }
      onDelete();
    }}, "Delete my account");

    return el("div", {},
      card(
        el("h2", {}, "Settings"),
        el("p", { class: "lede" }, "You can change these whenever. They're only used to make your plan feel like yours."),
        el("div", { class: "field" },
          el("label", { for: "name" }, "First name"),
          el("input", {
            id: "name", type: "text", autocomplete: "given-name",
            value: data.first_name,
            oninput: (e) => { data.first_name = e.target.value; markDirty(); },
          }),
        ),
        el("div", { class: "field", role: "radiogroup", "aria-labelledby": "settings-gender-label" },
          el("div", { id: "settings-gender-label", class: "field-label" }, "Gender"),
          el("div", { class: "choice-list" },
            genderRadio("female", "Female"),
            genderRadio("male", "Male"),
            genderRadio("non-binary", "Non-binary"),
          ),
        ),
        el("div", { class: "field" },
          el("label", { for: "zip" }, "ZIP code"),
          el("p", { class: "help" }, "Helps us look up real prices and programs near you."),
          el("input", {
            id: "zip", type: "text", inputmode: "numeric", maxlength: "5",
            autocomplete: "postal-code",
            value: data.zip_code,
            oninput: (e) => {
              data.zip_code = e.target.value.replace(/\D/g, "").slice(0, 5);
              e.target.value = data.zip_code;
              markDirty();
            },
          }),
        ),
        el("div", { class: "btn-row" }, save),
      ),
      el("div", { class: "danger-zone" },
        el("h3", {}, "Danger zone"),
        el("p", {}, "This deletes your profile, all your answers, and every plan version. There's no recovery."),
        deleteBtn,
      ),
    );
  }

  // ───────── Plan history (versions list, single season) ─────────
  function planHistory(seasonId, versions, latestRevision) {
    return el("div", {},
      card(
        el("h2", {}, "Plan history"),
        el("p", { class: "lede" },
          versions.length === 1
            ? "One plan so far. As you revise your answers and regenerate, every version stays here so you can see how your thinking has shifted."
            : "Every version of your plan, newest first. Revising your answers and generating again creates a new version — your previous ones stay put."
        ),
        el("div", { class: "plan-list" },
          ...[...versions].reverse().map(v => {
            const main = el("div", { class: "plan-row-main" },
              el("span", { class: "plan-version" }, `Plan v${v.version}`),
              el("span", { class: "plan-date" }, v.date),
            );
            if (v.packVersion) {
              const pill = el("span", { class: "plan-version-pill" }, `pack v${v.packVersion}`);
              if (latestRevision && v.packVersion !== latestRevision) {
                pill.classList.add("plan-version-pill-stale");
              }
              main.appendChild(pill);
            }
            const row = el("a", { href: `#/season/${seasonId}/plan/${v.version}`, class: "plan-row" }, main);
            if (v.chatMessages > 0) {
              row.appendChild(el("a", {
                class: "plan-chat-link",
                href: `#/season/${seasonId}/plan/${v.version}/chat`,
                onclick: (e) => e.stopPropagation(),
              }, `Conversation (${v.chatMessages})`));
            }
            return row;
          }),
        ),
        el("div", { class: "btn-row" },
          el("a", { class: "btn btn-secondary", href: "#/seasons" }, "Back to seasons"),
        ),
      ),
    );
  }

  // ───────── Docs (technical details) ─────────
  function docsIndex(docs) {
    return el("div", {},
      card(
        el("h1", {}, "Technical details"),
        el("p", { class: "lede" },
          "The thinking and research behind the planner. These are the design docs the model is built on — the math, the assumptions, the tradeoffs."),
        docs.length
          ? el("div", { class: "doc-list" },
              ...docs.map(d => el("a", { class: "doc-row", href: `#/docs/${d.slug}` }, d.title)),
            )
          : el("p", { class: "lede" }, "No docs yet."),
      ),
    );
  }

  function docPage(doc) {
    return el("div", {},
      el("div", { class: "plan-content", html: md.render(doc.markdown) }),
      el("div", { class: "btn-row" },
        el("a", { class: "btn btn-secondary", href: "#/docs" }, "Back to all docs"),
      ),
    );
  }

  // ───────── Loading / status ─────────
  function loading(label = "One moment…") {
    return card(
      el("p", {}, el("span", { class: "spinner" }), label),
    );
  }

  function error(message) {
    return card(
      el("h2", {}, "Something went wrong."),
      el("p", { class: "lede" }, message),
      el("div", { class: "btn-row" },
        el("a", { class: "btn", href: "#/" }, "Back to start"),
      ),
    );
  }

  return {
    el, card, toast,
    welcome, code, onboarding, home, seasons, history,
    questionnaire, plan, chat, planHistory, settings,
    docsIndex, docPage,
    loading, error,
  };
})();
