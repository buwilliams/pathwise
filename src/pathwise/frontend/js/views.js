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
          placeholder: "Emma",
          oninput: (e) => { data.first_name = e.target.value; refresh(); },
        }),
      ),
      el("div", { class: "field" },
        el("label", {}, "Gender"),
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
          placeholder: "30301",
          oninput: (e) => { data.zip_code = e.target.value.replace(/\D/g, "").slice(0, 5); e.target.value = data.zip_code; },
        }),
      ),
      el("div", { class: "btn-row" }, submit),
    );
  }

  // ───────── Home ─────────
  function home(profile, latestVersion) {
    return el("div", {},
      card(
        el("h1", {}, `Hey, ${profile.first_name}.`),
        el("p", { class: "tagline" }, "one step at a time, on purpose."),
        latestVersion
          ? el("p", { class: "lede" }, "You can read your latest plan, revise your answers, or generate a new version anytime.")
          : el("p", { class: "lede" }, "Let's start with a few questions. About 10 minutes."),
        el("div", { class: "btn-row" },
          latestVersion
            ? el("a", { class: "btn btn-accent", href: "#/plan" }, "Read my plan")
            : el("a", { class: "btn btn-accent", href: "#/season/transition-to-adulthood" }, "Begin"),
          latestVersion && el("a", { class: "btn btn-secondary", href: "#/season/transition-to-adulthood" }, "Revise my answers"),
        ),
      ),
    );
  }

  // ───────── Questionnaire ─────────
  function questionnaire(pack, answers, completion, onAnswer, onGenerate) {
    const root = el("div", {});

    const progressBar = el("span", { style: `width: ${completion.percent}%` });
    const progressLabel = el("p", { class: "progress-label" },
      `${completion.percent}% — ${completion.required_total - completion.missing_required.length} of ${completion.required_total} required answered`
    );
    root.appendChild(el("div", {},
      el("div", { class: "progress" }, progressBar),
      progressLabel,
    ));

    const updateProgress = (pct, answered, total) => {
      progressBar.style.width = pct + "%";
      progressLabel.textContent = `${pct}% — ${answered} of ${total} required answered`;
    };

    const sections = pack.sections;
    for (const sec of sections) {
      const sectionQs = pack.questions.filter(q => q.section === sec.id);
      if (!sectionQs.length) continue;
      const sectionEl = card(
        el("h2", {}, sec.title),
        sec.blurb && el("p", { class: "section-blurb" }, sec.blurb),
        ...sectionQs.map(q => questionField(q, answers[q.key], async (val) => {
          try {
            const res = await onAnswer(q.key, val);
            answers[q.key] = res.answers[q.key];
            updateProgress(
              res.completion.percent,
              res.completion.required_total - res.completion.missing_required.length,
              res.completion.required_total,
            );
            generateBtn.disabled = !res.completion.is_complete;
          } catch (e) { toast(e.message, "error"); }
        })),
      );
      root.appendChild(sectionEl);
    }

    const generateBtn = el("button", {
      class: "btn btn-accent",
      onclick: onGenerate,
    }, "Generate my plan");
    generateBtn.disabled = !completion.is_complete;

    root.appendChild(card(
      el("p", { class: "lede" }, "When you're ready, we'll think it through and write you a plan. You can always revise."),
      el("div", { class: "btn-row" }, generateBtn),
    ));

    return root;
  }

  function questionField(q, currentValue, onChange) {
    const wrap = el("div", { class: "field" },
      el("label", { for: `q-${q.key}` }, q.prompt + (q.required ? "" : "  (optional)")),
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
  function plan(profile, planText, sources, version, totalVersions, onRegenerate, onRevise) {
    const html = md.render(planText);
    return el("div", {},
      el("div", { class: "plan-content", html }),
      sources && sources.length ? el("details", { class: "sources" },
        el("summary", {}, `Sources (${sources.length})`),
        el("ul", {}, ...sources.map(u => el("li", {}, el("a", { href: u, target: "_blank", rel: "noopener noreferrer" }, u)))),
      ) : null,
      el("div", { class: "btn-row" },
        el("button", { class: "btn btn-secondary", onclick: onRevise }, "Revise my answers"),
        el("button", { class: "btn", onclick: onRegenerate }, "Generate a new version"),
      ),
      el("p", { class: "progress-label" },
        `Plan v${version}` + (totalVersions > 1 ? ` of ${totalVersions} — ` : ""),
        totalVersions > 1 ? el("a", { href: "#/plans" }, "view all versions") : null,
      ),
    );
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
            id: "name", type: "text", value: data.first_name,
            oninput: (e) => { data.first_name = e.target.value; markDirty(); },
          }),
        ),
        el("div", { class: "field" },
          el("label", {}, "Gender"),
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

  // ───────── Plan history (versions list) ─────────
  function planHistory(versions) {
    return card(
      el("h2", {}, "Your plans"),
      el("p", { class: "lede" },
        versions.length === 1
          ? "One plan so far. As you revise your answers and regenerate, every version stays here so you can see how your thinking has shifted."
          : "Every version of your plan, newest first. Revising your answers and generating again creates a new version — your previous ones stay put."
      ),
      el("div", { class: "plan-list" },
        ...[...versions].reverse().map(v =>
          el("a", { href: `#/plan/${v.version}` },
            el("span", { class: "plan-version" }, `Plan v${v.version}`),
            el("span", { class: "plan-date" }, v.date),
          ),
        ),
      ),
    );
  }

  // ───────── Loading / status ─────────
  function loading(label = "One moment…") {
    return card(
      el("p", {}, el("span", { class: "spinner" }), label),
    );
  }

  function generating(profile) {
    return card(
      el("h2", {}, "Thinking it through…"),
      el("p", { class: "lede" }, "Looking up real prices and programs near you, then writing you something honest. This usually takes about a minute."),
      el("p", {}, el("span", { class: "spinner" }), "Working…"),
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
    welcome, code, onboarding, home,
    questionnaire, plan, planHistory, settings,
    loading, generating, error,
  };
})();
