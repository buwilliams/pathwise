// Interactive path sandbox. The math is the surface here — sliders for
// stage durations, completion risk (ρ), technology trajectory (δ), and
// global costs. Each move re-runs the simulator on the server; the
// Pareto chart + per-path cards repaint with the new numbers.
//
// The narration panel is the LLM, downstream. The user makes the
// discovery; the LLM names the pattern. No "recommended path".

const sandboxView = (() => {
  const el = views.el;
  const card = views.card;

  const BUCKETS = [
    { id: "fast_freedom", label: "Fast Freedom" },
    { id: "compounding_freedom", label: "Compounding Freedom" },
    { id: "skill_leverage", label: "Skill-Leverage" },
  ];

  // ──────────────────────────────────────────────────────────────────────
  // Slider widget — emits onInput (live, no commit) + onCommit (debounced)
  // ──────────────────────────────────────────────────────────────────────
  function slider({ label, min, max, step, value, format, onCommit }) {
    const wrap = el("label", { class: "sandbox-slider" });
    const labelRow = el("div", { class: "sandbox-slider-label" },
      el("span", { class: "sandbox-slider-name" }, label),
      el("span", { class: "sandbox-slider-value" }, format(value)),
    );
    const valEl = labelRow.querySelector(".sandbox-slider-value");
    const input = el("input", {
      type: "range", min, max, step, value,
      class: "sandbox-slider-input",
      oninput: (e) => {
        const v = parseFloat(e.target.value);
        valEl.textContent = format(v);
      },
      onchange: (e) => onCommit(parseFloat(e.target.value)),
    });
    wrap.appendChild(labelRow);
    wrap.appendChild(input);
    return wrap;
  }

  // ──────────────────────────────────────────────────────────────────────
  // Pareto chart — scatter of {momentum, min_R} per path, with the
  // non-dominated set highlighted. Viable paths only on the frontier
  // (non-viable can't beat anyone since they're filtered out before
  // momentum comparison).
  // ──────────────────────────────────────────────────────────────────────
  function paretoChart(paths, rMin) {
    const W = 360, H = 220;
    const PAD = { l: 38, r: 12, t: 12, b: 28 };
    const enabled = paths.filter(p => p.enabled);
    if (enabled.length === 0) {
      return el("div", { class: "sandbox-pareto-empty" }, "No paths enabled.");
    }

    const moms = enabled.map(p => p.path_momentum);
    const recs = enabled.map(p => p.min_recoverability);
    const xMin = 0;
    const xMax = Math.max(...moms, 1) * 1.05;
    const yMin = 0;
    const yMax = 1.0;

    const sx = (x) => PAD.l + ((x - xMin) / (xMax - xMin || 1)) * (W - PAD.l - PAD.r);
    const sy = (y) => H - PAD.b - ((y - yMin) / (yMax - yMin || 1)) * (H - PAD.t - PAD.b);

    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("class", "sandbox-pareto");

    function svgEl(name, attrs) {
      const e = document.createElementNS(svgNS, name);
      for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
      return e;
    }

    // Axes
    svg.appendChild(svgEl("line", {
      x1: PAD.l, y1: H - PAD.b, x2: W - PAD.r, y2: H - PAD.b,
      class: "sandbox-pareto-axis",
    }));
    svg.appendChild(svgEl("line", {
      x1: PAD.l, y1: PAD.t, x2: PAD.l, y2: H - PAD.b,
      class: "sandbox-pareto-axis",
    }));
    // Axis labels
    const xLabel = svgEl("text", {
      x: W / 2, y: H - 6, "text-anchor": "middle",
      class: "sandbox-pareto-axis-label",
    });
    xLabel.textContent = "Path momentum →";
    svg.appendChild(xLabel);
    const yLabel = svgEl("text", {
      x: -H / 2, y: 12,
      transform: `rotate(-90)`, "text-anchor": "middle",
      class: "sandbox-pareto-axis-label",
    });
    yLabel.textContent = "Min recoverability →";
    svg.appendChild(yLabel);

    // R_min horizontal cutoff
    const yCut = sy(rMin);
    svg.appendChild(svgEl("line", {
      x1: PAD.l, y1: yCut, x2: W - PAD.r, y2: yCut,
      class: "sandbox-pareto-rmin",
    }));
    const rMinLabel = svgEl("text", {
      x: W - PAD.r - 4, y: yCut - 4, "text-anchor": "end",
      class: "sandbox-pareto-rmin-label",
    });
    rMinLabel.textContent = `R_min ${rMin.toFixed(2)}`;
    svg.appendChild(rMinLabel);

    // Draw the Pareto frontier as a connected line over its points
    const frontier = enabled
      .filter(p => p.on_pareto_frontier)
      .sort((a, b) => a.path_momentum - b.path_momentum);
    if (frontier.length > 1) {
      const d = frontier.map((p, i) =>
        `${i === 0 ? "M" : "L"} ${sx(p.path_momentum)} ${sy(p.min_recoverability)}`
      ).join(" ");
      svg.appendChild(svgEl("path", { d, class: "sandbox-pareto-frontier" }));
    }

    // Points
    for (const p of enabled) {
      const cx = sx(p.path_momentum);
      const cy = sy(p.min_recoverability);
      const klass = [
        "sandbox-pareto-pt",
        p.on_pareto_frontier ? "is-frontier" : "",
        p.viable ? "" : "is-nonviable",
        p.terminal_desirable ? "is-desirable" : "",
      ].filter(Boolean).join(" ");
      const r = p.on_pareto_frontier ? 7 : 5;
      svg.appendChild(svgEl("circle", { cx, cy, r, class: klass }));
      const t = svgEl("text", {
        x: cx, y: cy - 9, "text-anchor": "middle",
        class: "sandbox-pareto-pt-label",
      });
      t.textContent = p.label.split(",")[0].slice(0, 28);
      svg.appendChild(t);
    }

    return svg;
  }

  // ──────────────────────────────────────────────────────────────────────
  // Per-path card — durations, ρ, δ, viability lights, MC band when on
  // ──────────────────────────────────────────────────────────────────────
  function pathCard(meta, result, config, onCommit) {
    const enabled = config.paths?.[meta.id]?.enabled !== false;

    const enableToggle = el("label", { class: "sandbox-path-toggle" },
      el("input", {
        type: "checkbox",
        checked: enabled,
        onchange: (e) => onCommit({ kind: "enabled", path: meta.id, value: e.target.checked }),
      }),
      el("span", {}, enabled ? "Enabled" : "Disabled"),
    );

    const lights = el("div", { class: "sandbox-lights" });
    function light(label, ok, hint) {
      lights.appendChild(el("span", { class: "sandbox-light " + (ok ? "ok" : "fail"), title: hint || "" },
        el("span", { class: "sandbox-light-dot" }),
        el("span", {}, label),
      ));
    }
    light("Viable", result.viable, result.viable ? "Every stage clears the viable filter."
      : "At least one stage fails a viable-filter floor.");
    light("Terminal desirable", result.terminal_desirable, "Last stage clears every desirable threshold.");
    light(`R ≥ R_min`, result.r_min_satisfied, "Min recoverability across decisions ≥ R_min.");
    if (result.on_pareto_frontier) {
      light("Pareto frontier", true, "No other enabled path is ≥ on both momentum and recoverability with strict > somewhere.");
    }

    const headerStats = el("div", { class: "sandbox-path-stats" },
      el("div", {}, el("span", { class: "k" }, "Momentum"),
        el("span", { class: "v" }, result.path_momentum.toFixed(1))),
      el("div", {}, el("span", { class: "k" }, "Min R"),
        el("span", { class: "v" }, result.min_recoverability.toFixed(2))),
      result.monte_carlo
        ? el("div", { class: "sandbox-mc-band", title: "Monte Carlo P10 — P90" },
            el("span", { class: "k" }, "MC P10/P90"),
            el("span", { class: "v" },
              `${result.monte_carlo.momentum_p10.toFixed(0)} — ${result.monte_carlo.momentum_p90.toFixed(0)} · ` +
              `viable ${(result.monte_carlo.viable_prob * 100).toFixed(0)}%`),
          )
        : null,
    );

    // ρ slider — completion risk for this path's K
    const rho = config.paths?.[meta.id]?.rho ?? 0;
    const rhoSlider = slider({
      label: "ρ — completion risk",
      min: 0, max: 1, step: 0.01,
      value: rho,
      format: (v) => v.toFixed(2),
      onCommit: (v) => onCommit({ kind: "rho", path: meta.id, value: v }),
    });

    // δ slider — technology trajectory
    const delta = config.paths?.[meta.id]?.delta ?? 0;
    const deltaSlider = slider({
      label: "δ — tech trajectory (annual)",
      min: -0.2, max: 0.2, step: 0.005,
      value: delta,
      format: (v) => (v >= 0 ? "+" : "") + (v * 100).toFixed(1) + "%/yr",
      onCommit: (v) => onCommit({ kind: "delta", path: meta.id, value: v }),
    });

    // Stage rows
    const stageRows = meta.stages.map((sMeta, idx) => {
      const sResult = result.stages[idx] || {};
      const stageOverride = config.paths?.[meta.id]?.stages?.[sMeta.id] || {};
      const curDur = stageOverride.duration_months ?? sMeta.duration_months;
      const dur = slider({
        label: `${sMeta.label}`,
        min: 1, max: 60, step: 1,
        value: curDur,
        format: (v) => `${v} mo`,
        onCommit: (v) => onCommit({
          kind: "stage_duration", path: meta.id, stage: sMeta.id, value: v,
        }),
      });
      const flagRow = el("div", { class: "sandbox-stage-flags" });
      if (sMeta.training_active) flagRow.appendChild(el("span", { class: "tag" }, "training"));
      if (sMeta.moves_out) flagRow.appendChild(el("span", { class: "tag" }, "moves out"));
      if (sMeta.car) flagRow.appendChild(el("span", { class: "tag" }, "car"));
      if (sMeta.income_growth) flagRow.appendChild(el("span", { class: "tag tag-income" }, "income lift"));
      const lifeStats = el("div", { class: "sandbox-stage-life" },
        el("span", {}, `c $${sResult.cash_flow_monthly?.toLocaleString?.() ?? "?"}/mo`),
        el("span", {}, `r ${sResult.risk_buffer_months?.toFixed?.(1) ?? "?"} mo`),
        el("span", {}, `p ${sResult.productive_hours?.toFixed?.(0) ?? "?"} h/wk`),
        el("span", {}, `R ${sResult.recoverability?.toFixed?.(2) ?? "?"}`),
      );
      const failsLine = (sResult.fails && sResult.fails.length)
        ? el("div", { class: "sandbox-stage-fails" }, sResult.fails.join(" · "))
        : null;
      return el("div", { class: "sandbox-stage" + (sResult.viable ? "" : " is-fail") },
        dur, flagRow, lifeStats, failsLine,
      );
    });

    const root = el("div", { class: "sandbox-path-card" + (enabled ? "" : " is-disabled") },
      el("div", { class: "sandbox-path-head" },
        el("div", { class: "sandbox-path-title" },
          el("h3", {}, meta.label),
          el("p", { class: "sandbox-path-desc" }, meta.description),
        ),
        enableToggle,
      ),
      lights,
      headerStats,
      el("div", { class: "sandbox-path-sliders" }, rhoSlider, deltaSlider),
      el("h4", { class: "sandbox-stages-h" }, "Stages"),
      el("div", { class: "sandbox-stages" }, ...stageRows),
    );
    return root;
  }

  // ──────────────────────────────────────────────────────────────────────
  // Globals & Monte Carlo controls
  // ──────────────────────────────────────────────────────────────────────
  function globalsPanel(config, onCommit) {
    const g = config.globals || {};
    return card(
      el("h3", {}, "Global levers"),
      el("p", { class: "help" },
        "These apply to every enabled path. Useful for stress-testing: " +
        "drop rent and see who stays viable; raise R_min and watch paths drop off."),
      el("div", { class: "sandbox-globals" },
        slider({
          label: "Rent (monthly)", min: 200, max: 3500, step: 50,
          value: g.rent_monthly ?? 800,
          format: (v) => "$" + v.toLocaleString(),
          onCommit: (v) => onCommit({ kind: "global", key: "rent_monthly", value: v }),
        }),
        slider({
          label: "Car overhead (monthly)", min: 100, max: 1200, step: 25,
          value: g.car_overhead_monthly ?? 350,
          format: (v) => "$" + v.toLocaleString(),
          onCommit: (v) => onCommit({ kind: "global", key: "car_overhead_monthly", value: v }),
        }),
        slider({
          label: "Training hours / week", min: 0, max: 40, step: 1,
          value: g.training_hours_per_week ?? 15,
          format: (v) => v + " h/wk",
          onCommit: (v) => onCommit({ kind: "global", key: "training_hours_per_week", value: v }),
        }),
        slider({
          label: "Post-training income lift", min: 1.0, max: 2.0, step: 0.01,
          value: g.income_uplift_factor ?? 1.25,
          format: (v) => "×" + v.toFixed(2),
          onCommit: (v) => onCommit({ kind: "global", key: "income_uplift_factor", value: v }),
        }),
        slider({
          label: "R_min (recoverability floor)", min: 0, max: 1, step: 0.01,
          value: g.r_min ?? 0.4,
          format: (v) => v.toFixed(2),
          onCommit: (v) => onCommit({ kind: "global", key: "r_min", value: v }),
        }),
      ),
    );
  }

  function monteCarloPanel(config, onCommit, onRun) {
    const mc = config.monte_carlo || {};
    return card(
      el("h3", {}, "Monte Carlo on uncertain inputs"),
      el("p", { class: "help" },
        "ρ, δ, and prices are estimates, not facts. Jitter each within a band " +
        "and rerun N samples to see the P10–P90 spread on path momentum and " +
        "viability probability."),
      el("div", { class: "sandbox-globals" },
        slider({
          label: "Samples", min: 0, max: 500, step: 25,
          value: mc.samples ?? 0,
          format: (v) => v === 0 ? "off" : `${v}`,
          onCommit: (v) => onCommit({ kind: "mc", key: "samples", value: v }),
        }),
        slider({
          label: "ρ jitter (±)", min: 0, max: 0.5, step: 0.01,
          value: mc.rho_jitter ?? 0.15,
          format: (v) => "±" + v.toFixed(2),
          onCommit: (v) => onCommit({ kind: "mc", key: "rho_jitter", value: v }),
        }),
        slider({
          label: "δ jitter (±, annual)", min: 0, max: 0.2, step: 0.005,
          value: mc.delta_jitter ?? 0.05,
          format: (v) => "±" + (v * 100).toFixed(1) + "%",
          onCommit: (v) => onCommit({ kind: "mc", key: "delta_jitter", value: v }),
        }),
        slider({
          label: "Rent jitter (±)", min: 0, max: 0.5, step: 0.01,
          value: mc.rent_jitter ?? 0.2,
          format: (v) => "±" + (v * 100).toFixed(0) + "%",
          onCommit: (v) => onCommit({ kind: "mc", key: "rent_jitter", value: v }),
        }),
        slider({
          label: "Car cost jitter (±)", min: 0, max: 0.5, step: 0.01,
          value: mc.car_jitter ?? 0.15,
          format: (v) => "±" + (v * 100).toFixed(0) + "%",
          onCommit: (v) => onCommit({ kind: "mc", key: "car_jitter", value: v }),
        }),
      ),
    );
  }

  // ──────────────────────────────────────────────────────────────────────
  // Narration panel — LLM reads the simulation, names the pattern
  // ──────────────────────────────────────────────────────────────────────
  function narrationPanel(onAsk) {
    let focus = "";
    const output = el("div", { class: "sandbox-narration-output" }, "");
    const askBtn = el("button", { class: "btn btn-accent" }, "Ask the math what it found");
    askBtn.onclick = async () => {
      askBtn.disabled = true;
      const prev = askBtn.textContent;
      askBtn.textContent = "Reading the result…";
      output.innerHTML = "";
      output.appendChild(el("span", { class: "spinner" }));
      try {
        const text = await onAsk(focus);
        output.innerHTML = md.render(text);
      } catch (e) {
        output.textContent = e.message || "Narration failed.";
      } finally {
        askBtn.disabled = false;
        askBtn.textContent = prev;
      }
    };
    return card(
      el("h3", {}, "Narration"),
      el("p", { class: "help" },
        "You move the sliders; the math decides what's viable; this names the " +
        "pattern. The LLM never recommends — it tells you what your config " +
        "just revealed."),
      el("div", { class: "field" },
        el("label", { for: "narrate-focus" }, "Optional focus (a question about this state)"),
        el("input", {
          id: "narrate-focus", type: "text",
          placeholder: "e.g. why did the train_then_work path go red?",
          oninput: (e) => { focus = e.target.value; },
        }),
      ),
      el("div", { class: "btn-row" }, askBtn),
      output,
    );
  }

  // ──────────────────────────────────────────────────────────────────────
  // Root view + state
  // ──────────────────────────────────────────────────────────────────────
  function root(initial, simulate, narrate) {
    let config = initial.config;
    let result = initial.result;
    const meta = initial.paths_meta;

    const container = el("div", { class: "sandbox-root" });
    let pending = false;

    // Apply a single user lever change in-place to the config object.
    function applyChange(change) {
      if (!config.paths) config.paths = {};
      if (change.kind === "enabled") {
        config.paths[change.path] = config.paths[change.path] || {};
        config.paths[change.path].enabled = change.value;
      } else if (change.kind === "rho") {
        config.paths[change.path] = config.paths[change.path] || {};
        config.paths[change.path].rho = change.value;
      } else if (change.kind === "delta") {
        config.paths[change.path] = config.paths[change.path] || {};
        config.paths[change.path].delta = change.value;
      } else if (change.kind === "stage_duration") {
        config.paths[change.path] = config.paths[change.path] || {};
        config.paths[change.path].stages = config.paths[change.path].stages || {};
        config.paths[change.path].stages[change.stage] = { duration_months: change.value };
      } else if (change.kind === "global") {
        config.globals = config.globals || {};
        config.globals[change.key] = change.value;
      } else if (change.kind === "mc") {
        config.monte_carlo = config.monte_carlo || {};
        config.monte_carlo[change.key] = change.value;
      }
    }

    async function onCommit(change) {
      applyChange(change);
      if (pending) return;
      pending = true;
      try {
        const res = await simulate(config);
        result = res.result;
        render();
      } catch (e) {
        views.toast(e.message, "error");
      } finally {
        pending = false;
      }
    }

    function render() {
      const paretoCard = card(
        el("h3", {}, "Pareto frontier — momentum × recoverability"),
        el("p", { class: "help" },
          "Each dot is an enabled path. Up-and-to-the-right is better on both axes; " +
          "the line connects the non-dominated set. Red ring = the path fails a viable filter."),
        paretoChart(result.paths, result.r_min),
      );

      const bucketed = BUCKETS.map(b => {
        const inBucket = meta.filter(m => (result.paths.find(p => p.id === m.id) || {}).bucket === b.id);
        if (!inBucket.length) return null;
        return el("section", { class: "sandbox-bucket" },
          el("h2", { class: "sandbox-bucket-h" }, b.label),
          ...inBucket.map(m => {
            const r = result.paths.find(p => p.id === m.id);
            return pathCard(m, r, config, onCommit);
          }),
        );
      }).filter(Boolean);

      container.replaceChildren(
        card(
          el("h1", {}, "Path sandbox"),
          el("p", { class: "lede" },
            "Move the levers. The math reruns and tells you which paths stay viable, " +
            "which sit on the Pareto frontier, and how the numbers shift. The LLM doesn't " +
            "pick the answer — you do."),
        ),
        paretoCard,
        globalsPanel(config, onCommit),
        monteCarloPanel(config, onCommit),
        ...bucketed,
        narrationPanel(async (focus) => {
          const r = await narrate(config, focus);
          return r.narration;
        }),
      );
    }

    render();
    return container;
  }

  return { root };
})();
