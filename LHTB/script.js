/* ==========================================================================
   Long-Horizon Terminal-Bench — interactions & generated graphics
   --------------------------------------------------------------------------
   Modules (vanilla JS, no dependencies):
     1. Theme toggle
     2. Reading progress + TOC scrollspy
     3. Reveal-on-scroll
     4. Hero figure (inline SVG, theme-aware through CSS custom properties)
     5. Charts: leaderboard, domain bars, distribution, frontier donut,
        cost-vs-reward scatter, hardest-tasks table
     6. Copy BibTeX
   All data below is generated from harness/jobs (July 2026 snapshot);
   colors reference CSS variables directly so dark mode needs no re-render.
   ========================================================================== */
(function () {
  "use strict";
  const $  = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  /* ---- language + asset base (Chinese pages live in /LHTB/zh/) ---- */
  const ZH = (document.documentElement.lang || "en").toLowerCase().indexOf("zh") === 0;
  const BASE = /\/zh\/?$|\/zh\//.test(location.pathname) ? "../" : "";
  const t = (en, zh) => (ZH ? zh : en);

  const I18N = {
    // hero figure
    agent: t("AGENT", "智能体"),
    oneLLM: t("one LLM per run", "每次运行一个大模型"),
    identicalHarness: t("identical harness", "统一评测框架"),
    budget: t("Terminus-2 · 90 min budget", "Terminus-2 · 90 分钟预算"),
    commands: t("commands", "命令"),
    textObs: t("text observations", "文本反馈"),
    hundredsSteps: t("× hundreds of steps", "× 数百步"),
    container: t("DOCKER CONTAINER", "DOCKER 容器"),
    onStop: t("on stop", "停止时"),
    hiddenVerifier: t("HIDDEN VERIFIER", "隐藏验证器"),
    replays: t("replays the evidence:", "回放执行证据："),
    seededEngine: t("seeded engine · moves.log", "固定种子引擎 · moves.log"),
    hiddenTests: t("hidden tests · answer keys", "隐藏测试 · 标准答案"),
    claimed: t("claimed progress ≠ progress", "自称进度 ≠ 真实进度"),
    gradedReward: t("GRADED REWARD", "分级奖励"),
    // leaderboard
    model: t("Model", "模型"),
    solved: t("Solved", "已解决"),
    meanRewardHead: t("Mean reward", "平均奖励"),
    meanShort: t("Mean", "平均"),
    binaryPassHead: t("Binary pass rate (R = 1.0)", "二元通过率 (R = 1.0)"),
    passShort: t("Pass", "通过"),
    lbSubReward: t("Mean reward over 46 tasks · solved = reward ≥ 0.95 · one identical harness",
                   "46 项任务的平均奖励 · 解决 = 奖励 ≥ 0.95 · 同一套评测框架"),
    lbSubPass: t("Strict binary pass/fail at a perfect reward of R = 1.0 · share of the 46 tasks fully solved · errors = 0",
                  "在完美奖励 R = 1.0 下的严格二元判定 · 完全解决的任务占 46 项的比例 · 错误 = 0"),
    // horizon
    avgSteps: t("Avg steps / task", "平均步数 / 任务"),
    steps: t("Steps", "步数"),
    timePerTask: t("Time / task · total", "单任务用时 · 总计"),
    min: t("min", "分"),
    hour: t("h", "时"),
    // frontier donut
    neverSolved: t("never solved", "从未解决"),
    solvedByOne: t("solved by ≥1 model — 17 tasks", "至少一个模型解决 — 17 项"),
    neverAny: t("never solved by any — 29 tasks", "无任何模型解决 — 29 项"),
    solveThreshold: t("solve threshold: reward ≥ 0.95", "解决阈值：奖励 ≥ 0.95"),
    // cost scatter
    costTitleReward: t("Mean reward vs. cost per task", "平均奖励 vs. 单任务成本"),
    costTitlePass: t("Pass@1 vs. cost per task", "Pass@1 vs. 单任务成本"),
    ylabelReward: t("mean reward", "平均奖励"),
    ylabelPass: t("pass@1 at R ≥ 0.95  [%]", "pass@1（R ≥ 0.95）[%]"),
    xlabel: t("mean cost per task (log scale)", "单任务平均成本（对数刻度）"),
    average: t("Average", "平均"),
    legend: t("LEGEND", "图例"),
    avgAll: t("Average (17 models)", "平均（17 个模型）"),
    acrossAll: t("across all 17 models", "所有 17 个模型的平均"),
    costPerTask: t("Cost / task", "单任务成本"),
    meanCost: t("Mean cost", "平均成本"),
    medianCost: t("Median cost", "成本中位数"),
    // community table
    showing: (a, b) => t(`Showing ${a} of ${b} entries`, `显示 ${b} 条中的 ${a} 条`),
    noEntries: t("No entries match these filters.", "没有符合筛选条件的条目。"),
    allAgents: t("All agents", "全部智能体"),
    allModels: t("All models", "全部模型"),
    allOrgs: t("All organizations", "全部机构"),
    verified: t("verified", "已验证"),
    solvedThresh: (v) => t(`Solved (≥${v})`, `已解决 (≥${v})`),
    // misc
    copy: t("Copy", "复制"),
    copied: t("Copied!", "已复制！"),
  };

  // Category labels for the domain bar chart + hardest-tasks table (zh).
  const CAT_ZH = {
    "Software & reverse engineering": "软件与逆向工程",
    "Scientific computing & simulation": "科学计算与仿真",
    "Earth, climate & energy": "地球、气候与能源",
    "Multimodal & imaging analysis": "多模态与图像分析",
    "Research reproduction & ML": "研究复现与机器学习",
    "Systems, performance & security": "系统、性能与安全",
    "Interactive games": "交互式游戏",
    "APEX professional workflows": "APEX 专业工作流",
    "Logic & constraint puzzles": "逻辑与约束谜题",
    "Mathematical modeling": "数学建模",
    "Structural engineering": "结构工程",
    "Robotics": "机器人",
    "Multimodal": "多模态",
    "Climate science": "气候科学",
    "ML experimentation": "机器学习实验",
  };
  const catLabel = (s) => (ZH && CAT_ZH[s]) ? CAT_ZH[s] : s;

  /* ---- shared tokens for generated SVG ---- */
  const INK   = "var(--ink)";
  const SOFT  = "var(--ink-soft)";
  const MUT   = "var(--muted)";
  const FAINT = "var(--faint)";
  const LINE  = "var(--line)";
  const SURF  = "var(--surface)";
  const BLUE  = "var(--accent)";
  const BLUEI = "var(--accent-ink)";
  const BLUEW = "var(--accent-wash)";
  const SIEN  = "var(--sienna)";
  const SIENI = "var(--sienna-ink)";
  const MONO  = "var(--font-mono)";

  /* ===================== DATA (from harness/jobs, July 2026) ============ */
  // 17 models · mean reward over 46 tasks (errors = 0) · solved = reward >= 0.95
  const LB = [
    { name: "Grok 4.5",           vendor: "xAI",       logo: "grok-color",     mean: 0.505, solved: 13, cost: 11.19 },
    { name: "Claude Sonnet 5",    vendor: "Anthropic", logo: "claude-color",   mean: 0.497, solved: 8,  cost: 60.37, anthropic: true },
    { name: "Claude Opus 4.8",    vendor: "Anthropic", logo: "claude-color",   mean: 0.492, solved: 9,  cost: 39.11, anthropic: true },
    { name: "Claude Fable 5",     vendor: "Anthropic", logo: "claude-color",   mean: 0.487, solved: 12, cost: 73.11, anthropic: true },
    { name: "GPT-5.5",            vendor: "OpenAI",    logo: "openai",         mean: 0.445, solved: 7,  cost: 21.46 },
    { name: "MiniMax M3",         vendor: "MiniMax",   logo: "minimax-color",  mean: 0.385, solved: 3,  cost: 6.13 },
    { name: "Claude Sonnet 4.6",  vendor: "Anthropic", logo: "claude-color",   mean: 0.373, solved: 4,  cost: 38.00, anthropic: true },
    { name: "Kimi K2.7 Code",     vendor: "Moonshot",  logo: "kimi-color",     mean: 0.367, solved: 3,  cost: 8.31 },
    { name: "GLM 5.2",            vendor: "Zhipu",     logo: "zhipu-color",    mean: 0.316, solved: 1,  cost: 11.93 },
    { name: "Qwen3.6 Plus",       vendor: "Alibaba",   logo: "qwen-color",     mean: 0.313, solved: 1,  cost: 4.47 },
    { name: "DeepSeek V4 Pro",    vendor: "DeepSeek",  logo: "deepseek-color", mean: 0.307, solved: 3,  cost: 6.32 },
    { name: "Qwen3.7 Max",        vendor: "Alibaba",   logo: "qwen-color",     mean: 0.296, solved: 2,  cost: 7.78 },
    { name: "Hy3",          vendor: "Tencent",   logo: "hunyuan-color",  mean: 0.288, solved: 1,  cost: 2.47 },
    { name: "Doubao Seed 2.1 Pro",vendor: "ByteDance", logo: "doubao-color",   mean: 0.286, solved: 2,  cost: 5.16 },
    { name: "Gemini 3.1 Pro",     vendor: "Google",    logo: "gemini-color",   mean: 0.279, solved: 2,  cost: 7.61 },
    { name: "GPT-5.4",            vendor: "OpenAI",    logo: "openai",         mean: 0.272, solved: 1,  cost: 27.57 },
    { name: "GLM 5.1",            vendor: "Zhipu",     logo: "zhipu-color",    mean: 0.267, solved: 2,  cost: 5.13 },
    { name: "Kimi K2.6",          vendor: "Moonshot",  logo: "kimi-color",     mean: 0.255, solved: 0,  cost: 9.94 },
    { name: "GPT-5.3 Codex",      vendor: "OpenAI",    logo: "openai",         mean: 0.203, solved: 2,  cost: 8.20 },
    { name: "Grok 4.20",          vendor: "xAI",       logo: "grok-color",     mean: 0.080, solved: 0,  cost: 20.63 }
  ];

  // Tasks solved at the STRICT perfect-reward threshold R = 1.0 (d.solved is at R >= 0.95).
  // Same main-run selection as the paper leaderboard; ten models solve zero at R = 1.0.
  const SOLVED_100 = {
    "Grok 4.5": 9,
    "Claude Sonnet 5": 5,
    "Claude Opus 4.8": 5, "Claude Fable 5": 7, "GPT-5.5": 5, "MiniMax M3": 3,
    "Claude Sonnet 4.6": 2, "Kimi K2.7 Code": 2, "GLM 5.2": 0, "Qwen3.6 Plus": 0,
    "DeepSeek V4 Pro": 0, "Qwen3.7 Max": 0, "Hy3": 0, "Doubao Seed 2.1 Pro": 0,
    "Gemini 3.1 Pro": 0, "GPT-5.4": 1, "GLM 5.1": 0, "Kimi K2.6": 0,
    "GPT-5.3 Codex": 1, "Grok 4.20": 0,
  };
  const solved100 = (d) => SOLVED_100[d.name] ?? 0;

  // task categories (46 tasks, 9 categories) — labels/colors mirror results.html
  const DOMAINS = [
    ["Software & reverse engineering",    7, "#0969da"],
    ["Scientific computing & simulation", 6, "#bc4c00"],
    ["Earth, climate & energy",           6, "#1a7f37"],
    ["Multimodal & imaging analysis",     6, "#d63384"],
    ["Research reproduction & ML",        5, "#a83232"],
    ["Systems, performance & security",   5, "#9a6700"],
    ["Interactive games",                 4, "#8957e5"],
    ["APEX professional workflows",       4, "#0a7ea4"],
    ["Logic & constraint puzzles",        3, "#6741d9"]
  ];

  // reward-band distribution over all 782 model×task runs
  const DIST = [
    ["0", 9.2], ["0–.25", 46.2], [".25–.5", 15.3], [".5–.75", 10.2], [".75–.95", 12.0], ["≥.95", 7.0]
  ];

  // hardest tasks: mean over 17 models + best single run
  const HARD = [
    ["epidemic-inverse-control-audit", "Mathematical modeling", 0.027, 0.169],
    ["opensees-seismic-structural-regression-audit", "Structural engineering", 0.027, 0.102],
    ["robotics-slam-benchmark-repair", "Robotics", 0.028, 0.032],
    ["document-table-layout-reconstruction", "Multimodal", 0.034, 0.072],
    ["scientific-figure-data-reconstruction", "Multimodal", 0.038, 0.040],
    ["climate-netcdf-extreme-event-audit", "Climate science", 0.060, 0.088],
    ["microscopy-cell-count-qc-audit", "Multimodal", 0.061, 0.124],
    ["tabular-data-feature-covshift", "ML experimentation", 0.062, 0.302]
  ];

  // Long-horizon scale: average per task across the 46-task suite.
  //   steps = mean agent steps (n_episodes) · mins = mean wall-clock minutes / task
  //   hours = total wall-clock hours to run all 46 tasks once. Sorted by steps.
  const HORIZON = [
    { name: "DeepSeek V4 Pro",    vendor: "DeepSeek",  logo: "deepseek-color", steps: 321, mins: 84, hours: 64 },
    { name: "MiniMax M3",         vendor: "MiniMax",   logo: "minimax-color",  steps: 314, mins: 90, hours: 69 },
    { name: "GPT-5.4",            vendor: "OpenAI",    logo: "openai",         steps: 302, mins: 79, hours: 61 },
    { name: "GPT-5.3 Codex",      vendor: "OpenAI",    logo: "openai",         steps: 299, mins: 81, hours: 62 },
    { name: "Grok 4.20",          vendor: "xAI",       logo: "grok-color",     steps: 288, mins: 69, hours: 53 },
    { name: "Hy3",                vendor: "Tencent",   logo: "hunyuan-color",  steps: 258, mins: 92, hours: 70 },
    { name: "Claude Sonnet 5",    vendor: "Anthropic", logo: "claude-color",   steps: 256, mins: 87, hours: 67, anthropic: true },
    { name: "Qwen3.7 Max",        vendor: "Alibaba",   logo: "qwen-color",     steps: 218, mins: 84, hours: 64 },
    { name: "GPT-5.5",            vendor: "OpenAI",    logo: "openai",         steps: 208, mins: 73, hours: 56 },
    { name: "Claude Opus 4.8",    vendor: "Anthropic", logo: "claude-color",   steps: 205, mins: 78, hours: 60, anthropic: true },
    { name: "Grok 4.5",           vendor: "xAI",       logo: "grok-color",     steps: 197, mins: 75, hours: 57 },
    { name: "GLM 5.2",            vendor: "Zhipu",     logo: "zhipu-color",    steps: 195, mins: 89, hours: 68 },
    { name: "Qwen3.6 Plus",       vendor: "Alibaba",   logo: "qwen-color",     steps: 194, mins: 89, hours: 68 },
    { name: "Kimi K2.6",          vendor: "Moonshot",  logo: "kimi-color",     steps: 188, mins: 92, hours: 71 },
    { name: "Doubao Seed 2.1 Pro",vendor: "ByteDance", logo: "doubao-color",   steps: 183, mins: 92, hours: 70 },
    { name: "Kimi K2.7 Code",     vendor: "Moonshot",  logo: "kimi-color",     steps: 183, mins: 85, hours: 66 },
    { name: "Claude Sonnet 4.6",  vendor: "Anthropic", logo: "claude-color",   steps: 169, mins: 92, hours: 71, anthropic: true },
    { name: "Gemini 3.1 Pro",     vendor: "Google",    logo: "gemini-color",   steps: 148, mins: 85, hours: 65 },
    { name: "GLM 5.1",            vendor: "Zhipu",     logo: "zhipu-color",    steps: 120, mins: 93, hours: 71 },
    { name: "Claude Fable 5",     vendor: "Anthropic", logo: "claude-color",   steps: 118, mins: 86, hours: 66, anthropic: true }
  ];

  /* ===================== 1. THEME ===================== */
  const root = document.documentElement;
  const forced = new URLSearchParams(location.search).get("theme");
  const saved = forced || localStorage.getItem("lhtb-theme");
  if (saved === "dark" || (!saved && matchMedia("(prefers-color-scheme: dark)").matches)) {
    root.classList.add("dark");
  } else if (saved === "light") {
    root.classList.remove("dark");
  }
  $("#theme-toggle")?.addEventListener("click", () => {
    root.classList.toggle("dark");
    localStorage.setItem("lhtb-theme", root.classList.contains("dark") ? "dark" : "light");
  });

  /* ===================== 2. PROGRESS + SCROLLSPY ===================== */
  const bar = $("#progress-bar");
  const tocItems = $$(".toc__item");
  const sections = tocItems
    .map((a) => document.getElementById(a.getAttribute("href").slice(1)))
    .filter(Boolean);

  function onScroll() {
    const h = document.documentElement;
    const scrolled = h.scrollTop / (h.scrollHeight - h.clientHeight);
    if (bar) bar.style.width = (scrolled * 100).toFixed(2) + "%";
    let active = sections[0];
    const probe = h.scrollTop + 130;
    for (const sec of sections) if (sec.offsetTop <= probe) active = sec;
    tocItems.forEach((a) =>
      a.classList.toggle("is-active", a.getAttribute("href") === "#" + (active && active.id))
    );
  }
  document.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);

  /* ===================== 3. REVEAL ===================== */
  const revealSel = [
    ".hero__figure", ".tldr", ".note", ".figure", ".specs",
    ".insights", ".ticklist--takeaways", ".chart-card", ".aside", ".closing"
  ].join(",");
  $$(revealSel).forEach((el) => el.classList.add("reveal"));
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); }
    });
  }, { threshold: 0.1 });
  $$(".reveal").forEach((el) => io.observe(el));

  /* ===================== 4. HERO FIGURE ===================== */
  function T(x, y, s, o = {}) {
    const a = [
      `x="${x}"`, `y="${y}"`,
      `font-size="${o.size || 13}"`,
      o.w ? `font-weight="${o.w}"` : "",
      `fill="${o.fill || SOFT}"`,
      o.anchor ? `text-anchor="${o.anchor}"` : "",
      o.ls ? `letter-spacing="${o.ls}"` : "",
      o.italic ? `font-style="italic"` : "",
      o.mono ? `font-family="${MONO}"` : "",
      o.op ? `opacity="${o.op}"` : ""
    ].filter(Boolean).join(" ");
    return `<text ${a}>${s}</text>`;
  }
  const harrow = (x1, x2, y, color, wdt = 1.6) =>
    `<path d="M${x1} ${y} H${x2 - 7}" stroke="${color}" stroke-width="${wdt}" fill="none"/>` +
    `<polygon points="${x2 - 8},${y - 4.5} ${x2},${y} ${x2 - 8},${y + 4.5}" fill="${color}"/>`;

  function heroSVG() {
    // left: agent — center: containerized environment loop — right: verifier + reward
    const termLines = [
      ["$ g2048 status", MUT],
      ["score=132 max_tile=32", FAINT],
      ["$ g2048 move ULLD", MUT],
      ["score=164 max_tile=64", FAINT],
      ["$ python rerun.py -q", MUT],
      ["3/17 suites drifted", FAINT],
      ["$ …", MUT]
    ].map((l, i) => T(392, 128 + i * 24, l[0], { size: 12, mono: true, fill: l[1] })).join("");

    return `
<svg viewBox="0 0 960 330" role="img" aria-label="An agent loops shell commands and observations against a container for hundreds of steps; a hidden verifier then replays the evidence into a graded reward">
  <!-- left: the agent -->
  ${T(160, 84, I18N.agent, { size: 11, w: 650, fill: SIENI, anchor: "middle", ls: ".12em" })}
  <rect x="88" y="100" width="144" height="96" rx="10" fill="${SURF}" stroke="${LINE}"/>
  <circle cx="160" cy="134" r="17" fill="none" stroke="${SIEN}" stroke-width="1.8"/>
  <rect x="146" y="156" width="28" height="3.2" rx="1.6" fill="${SIEN}" opacity=".7"/>
  ${T(160, 182, I18N.oneLLM, { size: 11.5, fill: MUT, anchor: "middle" })}
  ${T(160, 226, I18N.identicalHarness, { size: 12, w: 600, fill: SOFT, anchor: "middle" })}
  ${T(160, 243, I18N.budget, { size: 11, fill: MUT, anchor: "middle" })}

  <!-- loop arrows -->
  ${harrow(238, 372, 128, SIEN)}
  ${T(305, 118, I18N.commands, { size: 11.5, w: 550, fill: SIENI, anchor: "middle" })}
  ${harrow(372, 238, 172, "var(--graphite)")}
  ${T(305, 195, I18N.textObs, { size: 11.5, w: 550, fill: MUT, anchor: "middle" })}
  ${T(305, 158, I18N.hundredsSteps, { size: 11, italic: true, fill: FAINT, anchor: "middle" })}

  <!-- center: container -->
  ${T(480, 84, I18N.container, { size: 11, w: 650, fill: BLUEI, anchor: "middle", ls: ".12em" })}
  <rect x="378" y="100" width="204" height="196" rx="10" fill="${SURF}" stroke="${LINE}"/>
  <rect x="378" y="100" width="204" height="14" rx="7" fill="${BLUEW}"/>
  ${termLines}

  <!-- arrow to verifier -->
  ${harrow(590, 672, 198, BLUE)}
  ${T(631, 188, I18N.onStop, { size: 11, italic: true, fill: FAINT, anchor: "middle" })}

  <!-- right: verifier -->
  ${T(790, 84, I18N.hiddenVerifier, { size: 11, w: 650, fill: BLUEI, anchor: "middle", ls: ".12em" })}
  <rect x="680" y="100" width="220" height="120" rx="10" fill="${SURF}" stroke="${LINE}"/>
  ${T(700, 130, I18N.replays, { size: 12.5, w: 600, fill: INK })}
  ${T(700, 152, I18N.seededEngine, { size: 11.5, mono: true, fill: MUT })}
  ${T(700, 170, I18N.hiddenTests, { size: 11.5, mono: true, fill: MUT })}
  ${T(700, 196, I18N.claimed, { size: 11.5, italic: true, fill: FAINT })}

  <!-- reward strip -->
  <rect x="680" y="240" width="220" height="56" rx="10" fill="${SURF}" stroke="${LINE}"/>
  ${T(700, 263, I18N.gradedReward, { size: 10.5, w: 650, fill: SIENI, ls: ".1em" })}
  <rect x="700" y="272" width="180" height="8" rx="4" fill="var(--line-soft)"/>
  <rect x="700" y="272" width="118" height="8" rx="4" fill="${SIEN}"/>
  ${T(886, 281, "0.66", { size: 11.5, w: 650, fill: SIENI, anchor: "end" })}
  <path d="M790 220 v14" stroke="${LINE}" stroke-width="1.4"/>
</svg>`;
  }
  const heroEl = $("#hero-illustration");
  if (heroEl) heroEl.innerHTML = heroSVG();

  /* ===================== 5. CHARTS ===================== */
  const C_MAIN = "var(--c-main)";
  const C_DIM  = "var(--c-dim)";
  const C_WARN = "var(--c-warn)";

  function whenVisible(el, fn) {
    if (!el) return;
    const o = new IntersectionObserver((es) => {
      es.forEach((e) => { if (e.isIntersecting) { fn(); o.disconnect(); } });
    }, { threshold: 0.12 });
    o.observe(el);
  }

  /* ---- leaderboard rows (toggle: partial reward vs strict binary pass rate) ---- */
  // Rows stay in mean-reward order in BOTH modes: under binary scoring the bars
  // no longer descend monotonically, which is exactly the point — several models
  // with real partial credit solve zero tasks. Bars share one scale (max mean
  // reward) so the collapse from partial -> binary is directly comparable.
  const LB_MODES = {
    reward: {
      val: (d) => d.mean,
      num: (d) => d.mean.toFixed(3),
      solvedText: (d) => `${d.solved}/46`,
      barHead: I18N.meanRewardHead,
      numHead: I18N.meanShort,
      sub: I18N.lbSubReward,
    },
    pass: {
      val: (d) => solved100(d) / 46,
      num: (d) => (solved100(d) / 46 * 100).toFixed(1) + "%",
      solvedText: (d) => `${solved100(d)}/46`,
      barHead: I18N.binaryPassHead,
      numHead: I18N.passShort,
      sub: I18N.lbSubPass,
    },
  };
  let lbMode = "reward";
  function renderLeaderboard() {
    const el = $("#leaderboard");
    if (!el) return;
    const scale = Math.max(...LB.map((d) => d.mean));
    const m = LB_MODES[lbMode];
    let html = `
      <div class="lb-head">
        <span></span><span>${I18N.model}</span><span class="lb-head__bar">${m.barHead}</span>
        <span class="lb-head__num" style="text-align:right">${m.numHead}</span><span style="text-align:right">${I18N.solved}</span>
      </div>`;
    LB.forEach((d, i) => {
      const pct = (m.val(d) / scale) * 100;
      const logo = d.logo
        ? `<img class="lb__logo" src="${BASE}assets/logos/${d.logo}.svg" alt="" width="22" height="22" loading="lazy" decoding="async"/>`
        : `<span class="lb__logo lb__logo--dot"></span>`;
      html += `
      <div class="lb-row${i === 0 ? " top" : ""}">
        <span class="lb__rank">${i + 1}</span>
        <span class="lb__model">
          ${logo}
          <span class="lb__modeltext">
            <span class="lb__name">${d.name}</span>
            <span class="lb__vendor">${d.vendor}</span>
          </span>
        </span>
        <span class="lb__barwrap">
          <span class="lb__track"></span>
          <span class="lb__fill" style="width:${pct.toFixed(1)}%; animation-delay:${(i * 0.04).toFixed(2)}s"></span>
        </span>
        <span class="lb__mean">${m.num(d)}</span>
        <span class="lb__solved">${m.solvedText(d)}</span>
      </div>`;
    });
    el.innerHTML = html;
  }
  // Animate between modes: update widths/numbers in place so CSS transitions run.
  function updateLeaderboard() {
    const el = $("#leaderboard");
    if (!el) return;
    const scale = Math.max(...LB.map((d) => d.mean));
    const m = LB_MODES[lbMode];
    $$(".lb-row", el).forEach((row, i) => {
      const d = LB[i];
      if (!d) return;
      const fill = row.querySelector(".lb__fill");
      const num = row.querySelector(".lb__mean");
      const sol = row.querySelector(".lb__solved");
      if (fill) fill.style.width = ((m.val(d) / scale) * 100).toFixed(1) + "%";
      if (num) num.textContent = m.num(d);
      if (sol) sol.textContent = m.solvedText(d);
    });
    const bh = $(".lb-head__bar", el), nh = $(".lb-head__num", el), sub = $("#lb-sub");
    if (bh) bh.textContent = m.barHead;
    if (nh) nh.textContent = m.numHead;
    if (sub) sub.textContent = m.sub;
  }
  $$("#lb-metric .seg__btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const next = btn.getAttribute("data-lb");
      if (!next || next === lbMode) return;
      lbMode = next;
      $$("#lb-metric .seg__btn").forEach((b) =>
        b.classList.toggle("is-active", b === btn)
      );
      updateLeaderboard();
    });
  });
  whenVisible($("#leaderboard"), () => {
    renderLeaderboard();
    const seg = $("#lb-metric");
    if (seg) { seg.classList.add("seg--attn"); }
  });

  /* ---- anatomy: hover a layout file to preview its real contents ---- */
  (function initLayoutPreview() {
    const chips = $$(".evchip[data-file]");
    const panel = $("#evpanel");
    if (!chips.length || !panel) return;
    const nameEl = $("#evpanel-name");
    const codeEl = $("#evpanel-code");
    const card = panel.closest(".unit-card");
    let pinned = null; // data-file key locked open via click
    const fill = (chip) => {
      const src = document.getElementById("file-" + chip.getAttribute("data-file"));
      if (!src) return;
      codeEl.textContent = src.textContent.replace(/^\n+/, "").replace(/\s+$/, "");
      nameEl.textContent = src.getAttribute("data-name") || "";
      panel.hidden = false;
      panel.querySelector(".evpanel__body").scrollTop = 0;
      chips.forEach((c) => c.classList.toggle("is-active", c === chip));
    };
    const hide = () => {
      panel.hidden = true;
      chips.forEach((c) => c.classList.remove("is-active"));
    };
    chips.forEach((chip) => {
      const key = chip.getAttribute("data-file");
      chip.addEventListener("mouseenter", () => fill(chip));
      chip.addEventListener("focus", () => { if (!pinned) fill(chip); });
      chip.addEventListener("click", () => {
        if (pinned === key) { pinned = null; hide(); }
        else { pinned = key; fill(chip); }
      });
    });
    // Hide when the pointer leaves the card, unless a file is pinned open.
    if (card) card.addEventListener("mouseleave", () => { if (!pinned) hide(); });
  })();

  /* ---- long-horizon scale (steps + time per task) ---- */
  function renderHorizon() {
    const el = $("#chart-horizon");
    if (!el) return;
    const max = Math.max(...HORIZON.map((d) => d.steps));
    let html = `
      <div class="hz-head">
        <span></span><span>${I18N.model}</span><span>${I18N.avgSteps}</span>
        <span style="text-align:right">${I18N.steps}</span>
        <span style="text-align:right">${I18N.timePerTask}</span>
      </div>`;
    HORIZON.forEach((d, i) => {
      const pct = (d.steps / max) * 100;
      const logo = d.logo
        ? `<img class="hz__logo" src="${BASE}assets/logos/${d.logo}.svg" alt="" width="22" height="22" loading="lazy" decoding="async"/>`
        : `<span class="hz__logo hz__logo--dot"></span>`;
      html += `
      <div class="hz-row">
        ${logo}
        <span class="hz__modeltext">
          <span class="hz__name">${d.name}</span>
          <span class="hz__vendor">${d.vendor}</span>
        </span>
        <span class="hz__barwrap">
          <span class="hz__track"></span>
          <span class="hz__fill" style="width:${pct.toFixed(1)}%; animation-delay:${(i * 0.04).toFixed(2)}s"></span>
        </span>
        <span class="hz__steps">${d.steps}</span>
        <span class="hz__meta">~${d.mins} ${I18N.min}&nbsp;·&nbsp;<b>${d.hours} ${I18N.hour}</b></span>
      </div>`;
    });
    el.innerHTML = html;
  }
  whenVisible($("#chart-horizon"), renderHorizon);

  /* ---- horizontal domain bars ---- */
  function renderDomains() {
    const el = $("#chart-domains");
    if (!el) return;
    const rowH = 27, x0 = 252, x1 = 738;
    const max = Math.max(...DOMAINS.map((d) => d[1]));
    const x = (v) => x0 + (v / max) * (x1 - x0);
    let body = "", y = 18;
    DOMAINS.forEach((d, i) => {
      const w = x(d[1]) - x0;
      body += `
        <text x="${x0 - 12}" y="${y + 13}" text-anchor="end" font-size="12" fill="${MUT}">${catLabel(d[0])}</text>
        <rect class="bar" x="${x0}" y="${y}" width="${w}" height="17" rx="4"
              fill="${d[2] || C_MAIN}" style="animation-delay:${(i * .05).toFixed(2)}s"/>
        <text class="fade-label" x="${x0 + w + 9}" y="${y + 13}" font-size="11.5" font-weight="650" fill="${SOFT}" style="font-variant-numeric:tabular-nums">${d[1]}</text>`;
      y += rowH;
    });
    el.innerHTML = `<svg viewBox="0 0 760 ${y + 6}" role="img">${body}</svg>`;
  }
  whenVisible($("#chart-domains"), renderDomains);

  /* ---- reward-band distribution (vertical bars) ---- */
  function renderDist() {
    const el = $("#chart-dist");
    if (!el) return;
    const W = 440, H = 232, padL = 40, padR = 6, padT = 18, padB = 30;
    const plotW = W - padL - padR, plotH = H - padT - padB;
    const max = 50;
    const y = (v) => padT + plotH - (v / max) * plotH;
    let grid = "";
    [0, 10, 20, 30, 40, 50].forEach((v) => {
      grid += `<line class="grid-line" x1="${padL}" y1="${y(v)}" x2="${W - padR}" y2="${y(v)}"/>` +
        `<text class="tick-label" x="${padL - 7}" y="${y(v) + 3.5}" text-anchor="end" font-size="10.5">${v}%</text>`;
    });
    const n = DIST.length, groupW = plotW / n, barW = Math.min(38, groupW * 0.52);
    let bars = "";
    DIST.forEach((d, i) => {
      const cx = padL + groupW * i + groupW / 2;
      const yy = y(d[1]);
      const solved = i === n - 1;
      bars += `
        <path class="bar bar--v" d="M${cx - barW / 2} ${padT + plotH} L${cx - barW / 2} ${yy + 4} Q${cx - barW / 2} ${yy} ${cx - barW / 2 + 4} ${yy} L${cx + barW / 2 - 4} ${yy} Q${cx + barW / 2} ${yy} ${cx + barW / 2} ${yy + 4} L${cx + barW / 2} ${padT + plotH} Z"
              fill="${solved ? "var(--c-good)" : C_MAIN}" opacity="${solved ? 1 : 1 - i * 0.08}"/>
        <text class="val-label fade-label" x="${cx}" y="${yy - 6}" text-anchor="middle" font-size="11" font-weight="600">${d[1].toFixed(1)}</text>
        <text class="grp-label" x="${cx}" y="${H - 8}" text-anchor="middle" font-size="11.5" font-weight="550">${d[0]}</text>`;
    });
    el.innerHTML = `
      <svg viewBox="0 0 ${W} ${H}" role="img">
        ${grid}
        <line class="axis-line" x1="${padL}" y1="${padT + plotH}" x2="${W - padR}" y2="${padT + plotH}"/>
        ${bars}
      </svg>`;
  }
  whenVisible($("#chart-dist"), renderDist);

  /* ---- unsolved frontier donut ---- */
  function renderFrontier() {
    const el = $("#chart-frontier");
    if (!el) return;
    const W = 440, H = 232, cx = 150, cy = 118, R = 78, r = 50;
    const solved = 17, total = 46;
    const frac = solved / total;
    const a0 = -Math.PI / 2, a1 = a0 + frac * 2 * Math.PI;
    const arc = (rad, a, b) => {
      const large = (b - a) > Math.PI ? 1 : 0;
      return `A${rad} ${rad} 0 ${large} 1 ${cx + rad * Math.cos(b)} ${cy + rad * Math.sin(b)}`;
    };
    const seg = (a, b, fill) => `
      <path d="M${cx + R * Math.cos(a)} ${cy + R * Math.sin(a)} ${arc(R, a, b)}
               L${cx + r * Math.cos(b)} ${cy + r * Math.sin(b)}
               A${r} ${r} 0 ${(b - a) > Math.PI ? 1 : 0} 0 ${cx + r * Math.cos(a)} ${cy + r * Math.sin(a)} Z"
            fill="${fill}"/>`;
    el.innerHTML = `
      <svg viewBox="0 0 ${W} ${H}" role="img">
        ${seg(a0, a1, "var(--c-good)")}
        ${seg(a1, a0 + 2 * Math.PI, C_WARN)}
        ${T(cx, cy - 2, "29", { size: 30, w: 700, fill: SIENI, anchor: "middle" })}
        ${T(cx, cy + 20, I18N.neverSolved, { size: 11.5, fill: MUT, anchor: "middle" })}
        <rect x="268" y="86" width="11" height="11" rx="3.5" fill="var(--c-good)"/>
        ${T(287, 96, I18N.solvedByOne, { size: 12.5, fill: SOFT })}
        <rect x="268" y="116" width="11" height="11" rx="3.5" fill="${C_WARN}"/>
        ${T(287, 126, I18N.neverAny, { size: 12.5, fill: SOFT })}
        ${T(268, 158, I18N.solveThreshold, { size: 11, italic: true, fill: FAINT })}
      </svg>`;
  }
  whenVisible($("#chart-frontier"), renderFrontier);

  /* ---- cost vs {reward | pass@1} scatter (log-x, toggleable y) ---- */
  const AVG_C = "var(--c-avg)";
  const passOf = (d) => d.solved / 46 * 100;

  // y-axis mode configs. `off` holds hand-tuned label offsets [dx, dy, anchor].
  const COST_MODES = {
    reward: {
      title: I18N.costTitleReward,
      ylabel: I18N.ylabelReward, max: 0.55, ticks: [0, 0.1, 0.2, 0.3, 0.4, 0.5],
      tickFmt: (v) => v.toFixed(1), val: (d) => d.mean,
      off: {
        // well-separated right side
        "Grok 4.5":           [0, -15, "middle"],
        "Claude Sonnet 5":    [0, -16, "middle"],
        "Claude Opus 4.8":    [0, -14, "middle"], "Claude Fable 5": [-12, 4, "end"],
        "GPT-5.5":            [0, -14, "middle"], "Claude Sonnet 4.6": [12, 4],
        "GPT-5.4":            [10, 5],            "Hy3": [0, 36, "middle", true],
        "MiniMax M3":         [0, -16, "middle"], "Grok 4.20": [0, -14, "middle"],
        // crowded $4–12 cluster: routed out with leader lines
        "GLM 5.2":            [57, 30, "start", true],   "DeepSeek V4 Pro": [-35, -87, "middle", true],
        "Kimi K2.7 Code":     [57, -65, "middle", true], "Qwen3.6 Plus": [-34, -30, "end", true],
        "Doubao Seed 2.1 Pro":[-65, -15, "end", true],   "GLM 5.1": [-64, 3, "end", true],
        "Qwen3.7 Max":        [30, -30, "start", true],  "Gemini 3.1 Pro": [34, 26, "start", true],
        "GPT-5.3 Codex":      [22, 20, "start", true],   "Kimi K2.6": [62, 33, "start", true]
      }
    },
    pass: {
      title: I18N.costTitlePass,
      ylabel: I18N.ylabelPass, max: 30, ticks: [0, 5, 10, 15, 20, 25, 30],
      tickFmt: (v) => String(v), val: passOf,
      off: {
        // well-separated right side + top
        "Grok 4.5":           [0, -14, "middle"],
        "Claude Sonnet 5":    [14, 5],
        "Claude Fable 5":     [-12, 5, "end"],    "Claude Opus 4.8": [0, -14, "middle"],
        "GPT-5.5":            [0, -14, "middle"], "Claude Sonnet 4.6": [12, 4],
        "GPT-5.4":            [0, -15, "middle"], "Hy3": [10, -6], "Grok 4.20": [0, -14, "middle"],
        // crowded low-pass cluster: routed up into the open upper region with leaders
        "Qwen3.6 Plus":       [-42, -83, "end", true],   "Doubao Seed 2.1 Pro": [-65, -80, "end", true],
        "GLM 5.1":            [-64, -35, "end", true],    "MiniMax M3": [-24, -97, "middle", true],
        "DeepSeek V4 Pro":    [50, -117, "start", true],  "Qwen3.7 Max": [40, -115, "start", true],
        "Gemini 3.1 Pro":     [44, -95, "start", true],   "GPT-5.3 Codex": [30, -60, "start", true],
        "Kimi K2.7 Code":     [57, -137, "start", true],  "Kimi K2.6": [-12, 4, "end"],
        "GLM 5.2":            [42, -93, "start", true]
      }
    }
  };

  function renderCost(mode) {
    const el = $("#chart-cost");
    if (!el) return;
    const cfg = COST_MODES[mode] || COST_MODES.reward;
    const W = 860, H = 360, padL = 56, padR = 24, padT = 18, padB = 44;
    const plotW = W - padL - padR, plotH = H - padT - padB;
    const cLo = 1.9, cHi = 105;
    const lx = (c) => padL + ((Math.log10(c) - Math.log10(cLo)) / (Math.log10(cHi) - Math.log10(cLo))) * plotW;
    const y = (v) => padT + plotH - (v / cfg.max) * plotH;

    let grid = "";
    [2, 5, 10, 20, 50, 100].forEach((c) => {
      grid += `<line class="grid-line" x1="${lx(c)}" y1="${padT}" x2="${lx(c)}" y2="${padT + plotH}"/>` +
        `<text class="tick-label" x="${lx(c)}" y="${padT + plotH + 18}" text-anchor="middle" font-size="10.5">$${c}</text>`;
    });
    cfg.ticks.forEach((v) => {
      grid += `<line class="grid-line" x1="${padL}" y1="${y(v)}" x2="${W - padR}" y2="${y(v)}"/>` +
        `<text class="tick-label" x="${padL - 8}" y="${y(v) + 3.5}" text-anchor="end" font-size="10.5">${cfg.tickFmt(v)}</text>`;
    });

    let dots = "";
    LB.forEach((d, i) => {
      const cxp = lx(d.cost), cyp = y(cfg.val(d));
      const o = cfg.off[d.name] || [10, 0];
      const dx = o[0], dy = o[1], anch = o[2], lead = o[3];
      const tx = cxp + dx, ty = cyp + dy + 4;
      // Faint leader line for labels routed far from their dot (crowded clusters).
      const leadSeg = lead
        ? `<line x1="${cxp}" y1="${cyp}" x2="${tx}" y2="${ty - 3}" stroke="var(--line)" stroke-width="1"/>`
        : "";
      dots += `
        ${leadSeg}
        <circle class="cost-dot" data-i="${i}" cx="${cxp}" cy="${cyp}" r="6.5"
                fill="${C_MAIN}" stroke="${SURF}" stroke-width="2"/>
        <text class="fade-label" x="${tx}" y="${ty}" font-size="11" font-weight="550"
              fill="${SOFT}" ${anch ? `text-anchor="${anch}"` : ""}>${d.name}</text>`;
    });

    // Average across all 17 models (arithmetic mean of the active y-metric and cost).
    const avgY = LB.reduce((s, d) => s + cfg.val(d), 0) / LB.length;
    const avgCost = LB.reduce((s, d) => s + d.cost, 0) / LB.length;
    const avgReward = LB.reduce((s, d) => s + d.mean, 0) / LB.length;
    const avgPass = LB.reduce((s, d) => s + passOf(d), 0) / LB.length;
    const acx = lx(avgCost), acy = y(avgY), ds = 7.5;
    const avgMark =
      `<polygon class="avg-dot" points="${acx},${acy - ds} ${acx + ds},${acy} ${acx},${acy + ds} ${acx - ds},${acy}"
                fill="${AVG_C}" stroke="${SURF}" stroke-width="2"/>` +
      `<text class="fade-label" x="${acx}" y="${acy - ds - 6}" font-size="11" font-weight="700"
             fill="${AVG_C}" text-anchor="middle">${I18N.average}</text>`;

    // Explicit bordered legend box in the empty top-left region.
    const lx0 = padL + 16, ly0 = padT + 6, lw = 150, lh = 62;
    const legend = `
      <g font-family="var(--font-sans)">
        <rect x="${lx0}" y="${ly0}" width="${lw}" height="${lh}" rx="8"
              fill="${SURF}" stroke="var(--line)" stroke-width="1"/>
        ${T(lx0 + 12, ly0 + 17, I18N.legend, { size: 9, w: 650, fill: FAINT, ls: ".1em" })}
        <circle cx="${lx0 + 17}" cy="${ly0 + 34}" r="5.5" fill="${C_MAIN}"/>
        ${T(lx0 + 29, ly0 + 38, I18N.model, { size: 11.5, fill: SOFT })}
        <polygon points="${lx0 + 17},${ly0 + 46} ${lx0 + 23},${ly0 + 52} ${lx0 + 17},${ly0 + 58} ${lx0 + 11},${ly0 + 52}" fill="${AVG_C}"/>
        ${T(lx0 + 29, ly0 + 56, I18N.avgAll, { size: 11.5, fill: SOFT })}
      </g>`;

    el.style.position = "relative";
    el.innerHTML = `
      <svg viewBox="0 0 ${W} ${H}" role="img">
        ${grid}
        <line class="axis-line" x1="${padL}" y1="${padT + plotH}" x2="${W - padR}" y2="${padT + plotH}"/>
        ${T(W / 2, H - 6, I18N.xlabel, { size: 11.5, fill: MUT, anchor: "middle" })}
        <text x="16" y="${padT + plotH / 2}" font-size="11.5" fill="${MUT}" text-anchor="middle"
              transform="rotate(-90 16 ${padT + plotH / 2})" font-family="var(--font-sans)">${cfg.ylabel}</text>
        ${dots}
        ${avgMark}
        ${legend}
      </svg>
      <div class="chart-tip" id="cost-tip" role="tooltip" aria-hidden="true"></div>`;

    const title = $("#chart-cost-title");
    if (title) title.textContent = cfg.title;

    const tip = $("#cost-tip", el);
    const row = (k, v, on) => `<dt${on ? ' class="on"' : ""}>${k}</dt><dd${on ? ' class="on"' : ""}>${v}</dd>`;
    const show = (i) => {
      const d = LB[i];
      const pass = passOf(d).toFixed(1);
      tip.innerHTML =
        `<div class="chart-tip__logo-name">` +
          (d.logo ? `<img src="${BASE}assets/logos/${d.logo}.svg" alt="" width="18" height="18"/>` : "") +
          `<b>${d.name}</b></div>` +
        `<div class="chart-tip__vendor">${d.vendor}</div>` +
        `<dl class="chart-tip__stats">` +
          row(I18N.meanRewardHead, d.mean.toFixed(3), mode === "reward") +
          row("Pass@1", `${d.solved}/46 (${pass}%)`, mode === "pass") +
          row(I18N.costPerTask, `$${d.cost.toFixed(2)}`, false) +
        `</dl>`;
      tip.classList.add("is-on");
      tip.setAttribute("aria-hidden", "false");
    };
    const move = (ev) => {
      const rect = el.getBoundingClientRect();
      let px = ev.clientX - rect.left + 14;
      let py = ev.clientY - rect.top + 14;
      const tw = tip.offsetWidth, th = tip.offsetHeight;
      if (px + tw > rect.width) px = ev.clientX - rect.left - tw - 14;
      if (py + th > rect.height) py = rect.height - th - 4;
      tip.style.left = Math.max(0, px) + "px";
      tip.style.top = Math.max(0, py) + "px";
    };
    const showAvg = () => {
      const med = [...LB].map((d) => d.cost).sort((a, b) => a - b);
      const median = med[(med.length - 1) >> 1];
      tip.innerHTML =
        `<div class="chart-tip__logo-name"><b>${I18N.average}</b></div>` +
        `<div class="chart-tip__vendor">${I18N.acrossAll}</div>` +
        `<dl class="chart-tip__stats">` +
          row(I18N.meanRewardHead, avgReward.toFixed(3), mode === "reward") +
          row("Pass@1", `${avgPass.toFixed(1)}%`, mode === "pass") +
          row(I18N.meanCost, `$${avgCost.toFixed(2)}`, false) +
          row(I18N.medianCost, `$${median.toFixed(2)}`, false) +
        `</dl>`;
      tip.classList.add("is-on");
      tip.setAttribute("aria-hidden", "false");
    };
    const hide = () => { tip.classList.remove("is-on"); tip.setAttribute("aria-hidden", "true"); };
    $$(".cost-dot", el).forEach((c) => {
      c.addEventListener("mouseenter", () => show(+c.dataset.i));
      c.addEventListener("mousemove", move);
      c.addEventListener("mouseleave", hide);
    });
    const avg = $(".avg-dot", el);
    if (avg) {
      avg.style.cursor = "pointer";
      avg.addEventListener("mouseenter", showAvg);
      avg.addEventListener("mousemove", move);
      avg.addEventListener("mouseleave", hide);
    }
  }

  let costMode = "reward";
  whenVisible($("#chart-cost"), () => renderCost(costMode));
  $$("#cost-yaxis .seg__btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      costMode = btn.dataset.y;
      $$("#cost-yaxis .seg__btn").forEach((b) => b.classList.toggle("is-active", b === btn));
      renderCost(costMode);
    });
  });

  /* ---- hardest-tasks table ---- */
  function renderHard() {
    const tbody = $("#hard-table tbody");
    if (!tbody) return;
    const maxBar = 0.35; // scale bars to the largest "best" value
    tbody.innerHTML = HARD.map(([task, dom, mean, best]) => `
      <tr>
        <td class="cell-task">${task}</td>
        <td class="cell-domain">${catLabel(dom)}</td>
        <td>
          <div class="loc-bar">
            <span class="loc-bar__track"></span>
            <span class="loc-bar__fill" style="width:${(mean / maxBar * 100).toFixed(1)}%; background:var(--c-dim)"></span>
            <span class="loc-bar__val">${mean.toFixed(3)}</span>
          </div>
        </td>
        <td>
          <div class="loc-bar">
            <span class="loc-bar__track"></span>
            <span class="loc-bar__fill" style="width:${(best / maxBar * 100).toFixed(1)}%"></span>
            <span class="loc-bar__val">${best.toFixed(3)}</span>
          </div>
        </td>
      </tr>`).join("");
  }
  whenVisible($("#hard-table"), renderHard);

  /* ---- community leaderboard (tbench-style, filterable) ---- */
  // Seeded with our Terminus-2 baselines (all replayed + verified). Community
  // submissions append here; scores are mean reward over the 46-task suite.
  // `st` = solved-task counts at reward thresholds [>=0.90, >=0.95, >=1.00],
  // computed from per-task rewards in harness/jobs (July 2026 snapshot).
  const N_TASKS = 46;
  const SOLVED_T = {
    "Grok 4.5":            [13, 13, 9],
    "Claude Sonnet 5":     [10, 8, 5],
    "Claude Opus 4.8":     [11, 9, 5], "Claude Fable 5":  [12, 12, 7],
    "GPT-5.5":             [8, 7, 5],   "MiniMax M3":     [6, 3, 3],
    "Claude Sonnet 4.6":   [7, 4, 2],   "Kimi K2.7 Code": [6, 3, 2],
    "GLM 5.2":             [4, 1, 0],   "Qwen3.6 Plus":   [3, 1, 0],
    "DeepSeek V4 Pro":     [4, 3, 0],   "Qwen3.7 Max":    [3, 2, 0],
    "Doubao Seed 2.1 Pro": [3, 2, 0],   "Gemini 3.1 Pro": [2, 2, 0],
    "GPT-5.4":             [3, 1, 1],   "GLM 5.1":        [3, 2, 0],
    "Kimi K2.6":           [1, 0, 0],   "Hy3":      [2, 1, 0],
    "GPT-5.3 Codex":       [3, 2, 1],
    "Grok 4.20":           [0, 0, 0]
  };
  const THRESH_IDX = { "0.9": 0, "0.95": 1, "1": 2 };
  const COMMUNITY = LB.map((d) => ({
    agent: "Terminus-2", name: d.name, vendor: d.vendor, logo: d.logo,
    mean: d.mean, st: SOLVED_T[d.name] || [d.solved, d.solved, d.solved],
    submitter: d.vendor === "Anthropic" ? "Lehigh University" : "Tencent",
    org: d.vendor, date: "2026-07-01", verified: true
  }));
  const CHECK = `<svg viewBox="0 0 24 24" width="11" height="11" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>`;

  function renderCommunity() {
    const tbody = $("#community-table tbody");
    if (!tbody) return;
    const fa = $("#filter-agent"), fm = $("#filter-model"), fo = $("#filter-org"),
          fv = $("#filter-verified"), ft = $("#filter-threshold");
    const tv = ft ? ft.value : "0.95";
    const ti = THRESH_IDX[tv] ?? 1;
    const thSolved = $("#th-solved");
    if (thSolved) thSolved.textContent = I18N.solvedThresh(Number(tv).toFixed(2));
    const sorted = COMMUNITY.slice().sort((a, b) => b.mean - a.mean);
    const rankOf = new Map(sorted.map((d, i) => [d, i + 1]));
    const rows = sorted.filter((d) =>
      (!fa.value || d.agent === fa.value) &&
      (!fm.value || d.name === fm.value) &&
      (!fo.value || d.org === fo.value) &&
      (!fv.checked || d.verified));
    $("#lbrd-count").textContent = I18N.showing(rows.length, COMMUNITY.length);
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="lbrd-empty">${I18N.noEntries}</td></tr>`;
      return;
    }
    tbody.innerHTML = rows.map((d) => {
      const rank = rankOf.get(d);
      const logo = d.logo
        ? `<img src="${BASE}assets/logos/${d.logo}.svg" alt="" width="20" height="20" loading="lazy" decoding="async"/>`
        : "";
      const badge = d.verified ? `<span class="verified lbrd-badge">${CHECK}${I18N.verified}</span>` : "";
      const solved = d.st[ti];
      const pct = Math.round((solved / N_TASKS) * 100);
      return `
        <tr${rank === 1 ? ' class="top"' : ""}>
          <td class="cell-rank">${rank}</td>
          <td class="cell-agent">${d.agent}</td>
          <td><span class="lbrd-model">${logo}<span class="lbrd-model__name">${d.name}</span></span></td>
          <td class="cell-sub">${d.submitter}</td>
          <td class="cell-date">${d.date}</td>
          <td class="cell-solved">${solved}/${N_TASKS} <span class="cell-solved__pct">${pct}%</span></td>
          <td><span class="lbrd-score">${badge}<span class="lbrd-score__val">${d.mean.toFixed(3)}</span></span></td>
        </tr>`;
    }).join("");
  }

  function initCommunity() {
    const fa = $("#filter-agent"), fm = $("#filter-model"), fo = $("#filter-org"),
          fv = $("#filter-verified"), ft = $("#filter-threshold");
    if (!fa) return;
    const uniq = (arr) => Array.from(new Set(arr));
    const fill = (sel, label, values) => {
      sel.innerHTML = `<option value="">${label}</option>` +
        values.map((v) => `<option value="${v}">${v}</option>`).join("");
    };
    fill(fa, I18N.allAgents, uniq(COMMUNITY.map((d) => d.agent)));
    fill(fm, I18N.allModels, uniq(COMMUNITY.map((d) => d.name)));
    fill(fo, I18N.allOrgs, uniq(COMMUNITY.map((d) => d.org)).sort());
    [fa, fm, fo, fv, ft].forEach((c) => c && c.addEventListener("change", renderCommunity));
    $("#filter-clear")?.addEventListener("click", () => {
      fa.value = ""; fm.value = ""; fo.value = ""; fv.checked = false;
      if (ft) ft.value = "0.95";
      renderCommunity();
    });
    renderCommunity();
  }
  whenVisible($("#community-table"), initCommunity);

  /* ---- copy submission commands ---- */
  $$(".cmd__copy").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const pre = btn.parentElement?.querySelector("pre");
      if (!pre) return;
      try {
        await navigator.clipboard.writeText(pre.textContent || "");
        btn.textContent = I18N.copied;
        setTimeout(() => (btn.textContent = I18N.copy), 1600);
      } catch { /* clipboard unavailable */ }
    });
  });

  /* ===================== 6. COPY BIBTEX ===================== */
  $("#copy-bib")?.addEventListener("click", async (e) => {
    const txt = $("#bibtex-block")?.textContent || "";
    try {
      await navigator.clipboard.writeText(txt);
      e.target.textContent = I18N.copied;
      setTimeout(() => (e.target.textContent = I18N.copy), 1600);
    } catch { /* clipboard unavailable */ }
  });
})();
