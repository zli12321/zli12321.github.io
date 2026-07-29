/* VLM Radar dashboard.
 *
 * One ES module, no dependencies, no build step. It reads the single JSON file
 * produced by `vlm-radar rebuild` and renders five views from it. All text goes
 * through textContent, so nothing in the data can inject markup.
 */

const DATA_URL = "data/radar.json";
const SUPPORTED_SCHEMA = 1;
const VIEWS = ["today", "models", "trends", "map", "atlas"];
const ALL = "all";

/* Fixed hues keep a topic the same colour across every view and every reload.
 * Saturation stays low so eighteen topics can coexist without shouting. */
const HUES = [212, 168, 32, 342, 268, 194, 96, 12, 300, 232, 148, 44, 318, 182, 110, 356, 284, 204];
const TOPIC_SATURATION = "34%";
const TOPIC_LIGHTNESS = "41%";

const state = {
  data: null,
  view: "today",
  categoryIndex: new Map(),
  categoryLabels: new Map(),
  daysByDate: new Map(),
  filters: {
    q: "",
    date: "",
    category: ALL,
    source: ALL,
    family: ALL,
    organization: ALL,
    event: ALL,
    provenance: ALL,
  },
  atlas: { q: "", section: ALL, category: ALL },
  selectedNode: null,
};

/* ------------------------------------------------------------------ helpers */

function h(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "text") node.textContent = String(value);
    else if (key === "class") node.className = value;
    else if (key === "style") node.setAttribute("style", value);
    else if (key === "dataset") Object.assign(node.dataset, value);
    else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2), value);
    } else node.setAttribute(key, value === true ? "" : String(value));
  }
  for (const child of [].concat(children)) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

const $ = (id) => document.getElementById(id);
const num = (value) => Number(value || 0).toLocaleString("en-US");

function replaceChildren(node, children) {
  node.replaceChildren(...[].concat(children).filter(Boolean));
}

function categoryColor(key) {
  const index = state.categoryIndex.get(key);
  const hue = HUES[(index === undefined ? 0 : index) % HUES.length];
  return `hsl(${hue} ${TOPIC_SATURATION} ${TOPIC_LIGHTNESS})`;
}

function categoryLabel(key) {
  return state.categoryLabels.get(key) || String(key).replace(/_/g, " ");
}

function shortDate(value) {
  if (!value) return "";
  return String(value).slice(0, 10);
}

function truncate(text, limit) {
  const value = String(text || "");
  return value.length <= limit ? value : `${value.slice(0, limit - 1).trimEnd()}…`;
}

function titleCase(value) {
  const text = String(value || "").replace(/[_-]/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/* --------------------------------------------------------------- URL state */

function readUrl() {
  const params = new URLSearchParams(window.location.search);
  const view = params.get("view");
  if (VIEWS.includes(view)) state.view = view;
  for (const key of Object.keys(state.filters)) {
    const value = params.get(key);
    if (value) state.filters[key] = value;
  }
  if (!state.filters.date) state.filters.date = state.data.latest_date || ALL;
}

function writeUrl() {
  const params = new URLSearchParams();
  if (state.view !== "today") params.set("view", state.view);
  for (const [key, value] of Object.entries(state.filters)) {
    if (!value || value === ALL) continue;
    if (key === "date" && value === state.data.latest_date) continue;
    params.set(key, value);
  }
  const query = params.toString();
  const target = `${window.location.pathname}${query ? `?${query}` : ""}`;
  window.history.replaceState(null, "", target);
}

/* ------------------------------------------------------------------ filters */

function fillSelect(select, values, allLabel, current) {
  const options = [h("option", { value: ALL, text: allLabel })];
  for (const value of values) {
    options.push(h("option", { value, text: titleCase(value) }));
  }
  replaceChildren(select, options);
  select.value = values.includes(current) || current === ALL ? current : ALL;
}

function buildFilterControls() {
  const facets = state.data.facets;

  const dateOptions = [h("option", { value: ALL, text: `All scans (${facets.dates.length})` })];
  for (const date of facets.dates) {
    const day = state.daysByDate.get(date);
    dateOptions.push(
      h("option", { value: date, text: `${date} · ${day ? day.item_count : 0} records` }),
    );
  }
  replaceChildren($("date-filter"), dateOptions);
  $("date-filter").value = state.filters.date;

  const categorySelect = $("category-filter");
  replaceChildren(categorySelect, [
    h("option", { value: ALL, text: "All topics" }),
    ...facets.categories.map((key) => h("option", { value: key, text: categoryLabel(key) })),
  ]);
  categorySelect.value = state.filters.category;

  fillSelect($("source-filter"), facets.sources, "All sources", state.filters.source);
  fillSelect($("family-filter"), facets.model_families, "All families", state.filters.family);
  fillSelect(
    $("organization-filter"),
    facets.organizations,
    "All organizations",
    state.filters.organization,
  );
  fillSelect($("event-filter"), facets.event_kinds, "All events", state.filters.event);
  fillSelect($("provenance-filter"), facets.provenance, "Live and curated", state.filters.provenance);
  $("search-filter").value = state.filters.q;
}

function activeDays() {
  if (state.filters.date === ALL) return state.data.days.slice().reverse();
  const day = state.daysByDate.get(state.filters.date);
  return day ? [day] : [];
}

function matchesFilters(item) {
  const f = state.filters;
  if (f.category !== ALL && !(item.categories || []).includes(f.category)) return false;
  if (f.source !== ALL && item.source !== f.source) return false;
  if (f.family !== ALL && !(item.model_families || []).includes(f.family)) return false;
  if (f.organization !== ALL && !(item.organizations || []).includes(f.organization)) return false;
  if (f.event !== ALL && item.event_kind !== f.event) return false;
  if (f.provenance !== ALL && (item.provenance || "live") !== f.provenance) return false;
  if (f.q) {
    const needle = f.q.toLowerCase();
    const haystack = [
      item.title,
      item.summary,
      item.source,
      item.section,
      (item.organizations || []).join(" "),
      (item.model_families || []).join(" "),
      (item.watchlist || []).join(" "),
    ]
      .join(" ")
      .toLowerCase();
    if (!haystack.includes(needle)) return false;
  }
  return true;
}

function filteredRecords() {
  const records = [];
  for (const day of activeDays()) {
    for (const item of day.items || []) {
      if (matchesFilters(item)) records.push({ item, day });
    }
  }
  records.sort((a, b) => {
    const pinA = isPinned(a.item) ? 1 : 0;
    const pinB = isPinned(b.item) ? 1 : 0;
    if (pinA !== pinB) return pinB - pinA;
    if (b.item.total_score !== a.item.total_score) return b.item.total_score - a.item.total_score;
    return String(b.item.published_at || "").localeCompare(String(a.item.published_at || ""));
  });
  return records;
}

/* ------------------------------------------------------------ record cards */

function isPinned(item) {
  return Boolean((item.model_families || []).length || (item.watchlist || []).length);
}

function scoreChip(item) {
  const primary = (item.categories || [])[0];
  const pinned = isPinned(item);
  return h("div", { class: "score-chip" }, [
    h("b", { text: Math.round(item.total_score) }),
    h("div", { class: "score-track" }, [
      h("i", {
        style: `width:${Math.max(2, Math.min(100, item.total_score))}%;background:${
          primary ? categoryColor(primary) : "var(--accent)"
        }`,
      }),
    ]),
    // Pinned records sort above score order, so say so where the number is.
    h("span", { text: pinned ? "pinned" : "score" }),
  ]);
}

function metaPills(item) {
  const provenance = item.provenance || "live";
  const pills = [h("span", { class: "meta-source", text: item.source })];
  if (item.event_kind && item.event_kind !== provenance) {
    pills.push(h("span", { text: item.event_kind }));
  }
  if (item.published_at) pills.push(h("span", { text: shortDate(item.published_at) }));
  for (const key of item.categories || []) {
    pills.push(
      h("span", {
        class: "pill topic",
        text: categoryLabel(key),
        style: `--pill-color:${categoryColor(key)}`,
      }),
    );
  }
  for (const family of item.model_families || []) {
    pills.push(h("span", { class: "pill pin", text: family }));
  }
  for (const name of item.watchlist || []) {
    pills.push(h("span", { class: "pill pin", text: name }));
  }
  if (provenance === "curated") {
    pills.push(h("span", { class: "pill curated", text: "curated" }));
  }
  return h("div", { class: "signal-meta" }, pills);
}

function keyValues(pairs) {
  const nodes = [];
  for (const [label, value] of pairs) {
    if (!value) continue;
    nodes.push(h("dt", { text: label }));
    nodes.push(h("dd", {}, value instanceof Node ? value : String(value)));
  }
  return nodes.length ? h("dl", { class: "kv" }, nodes) : null;
}

function linkList(urls) {
  if (!urls || !urls.length) return null;
  const nodes = [];
  urls.slice(0, 6).forEach((url, index) => {
    if (index) nodes.push(document.createTextNode(" · "));
    let label = url;
    try {
      label = new URL(url).hostname.replace(/^www\./, "");
    } catch (error) {
      /* keep the raw string when the URL is unparsable */
    }
    nodes.push(h("a", { href: url, rel: "noopener noreferrer", target: "_blank", text: label }));
  });
  return h("span", {}, nodes);
}

function signalCard({ item, day }) {
  const primary = (item.categories || [])[0];
  const pinned = isPinned(item);

  const metrics = Object.entries(item.metrics || {})
    .map(([name, value]) => `${name} ${num(Math.round(value))}`)
    .join(" · ");

  const body = h("div", { class: "signal-body" }, [
    item.summary ? h("p", { text: item.summary }) : h("p", { class: "card-note", text: "No upstream abstract available." }),
    keyValues([
      ["Scan", day.date],
      ["Published", shortDate(item.published_at)],
      ["Updated", item.updated_at && shortDate(item.updated_at) !== shortDate(item.published_at) ? shortDate(item.updated_at) : ""],
      ["Section", item.section],
      ["Venue", item.venue],
      ["Organizations", (item.organizations || []).join(", ")],
      ["Signals", metrics],
      ["Also found via", (item.corroborating_sources || []).join(", ")],
      ["Matched", (item.matched_terms || []).slice(0, 10).join(", ")],
      ["Why", (item.rationale || []).join(" · ")],
      ["Links", linkList(item.artifact_urls)],
    ]),
    h("div", { class: "signal-actions" }, [
      h("a", {
        class: "ghost-button",
        href: item.url,
        target: "_blank",
        rel: "noopener noreferrer",
        text: "Open record ↗",
      }),
      h("button", {
        class: "ghost-button",
        type: "button",
        text: "Why this score",
        onclick: () => openRubric(item),
      }),
    ]),
  ]);

  return h(
    "details",
    {
      class: "signal",
      dataset: { pinned: String(pinned) },
    },
    [
      h("summary", {}, [
        scoreChip(item),
        h("div", {}, [
          h("h3", { class: "signal-title" }, [
            h("a", {
              href: item.url,
              target: "_blank",
              rel: "noopener noreferrer",
              text: item.title,
            }),
          ]),
          metaPills(item),
        ]),
      ]),
      body,
    ],
  );
}

/* -------------------------------------------------------------- Today view */

function renderToday() {
  const records = filteredRecords();
  const cap = 220;

  $("today-count").textContent =
    records.length === 0
      ? "no matches"
      : `${num(records.length)} record${records.length === 1 ? "" : "s"}${
          records.length > cap ? ` · showing ${cap}` : ""
        }`;

  replaceChildren(
    $("today-list"),
    records.length
      ? records.slice(0, cap).map(signalCard)
      : h("p", {
          class: "empty",
          text: "No records match these filters. Clear them, or choose another scan date.",
        }),
  );

  renderFunnel();
  renderHealth();
}

function renderFunnel() {
  const days = activeDays();
  const totals = {};
  for (const day of days) {
    for (const [key, value] of Object.entries(day.selection || {})) {
      if (key === "minimum_score") continue;
      totals[key] = (totals[key] || 0) + Number(value || 0);
    }
  }
  const order = [
    ["fetched", "Fetched"],
    ["deduplicated", "After dedupe"],
    ["out_of_domain", "Out of domain"],
    ["suppressed", "Suppressed"],
    ["below_threshold", "Below threshold"],
    ["published", "Published"],
    ["pinned", "Pinned"],
  ];
  const rows = order
    .filter(([key]) => key in totals)
    .map(([key, label]) => h("li", {}, [h("span", { text: label }), h("b", { text: num(totals[key]) })]));

  if (!rows.length) rows.push(h("li", {}, [h("span", { text: "No scan selected" })]));
  const minimum = state.data.rubric ? state.data.rubric.minimum_score : null;
  if (minimum !== null && minimum !== undefined) {
    rows.push(h("li", {}, [h("span", { text: "Minimum score" }), h("b", { text: `${minimum}/100` })]));
  }
  replaceChildren($("funnel-list"), rows);
}

function renderHealth() {
  const days = activeDays();
  const latest = days[0];
  const entries = latest ? latest.health || [] : [];
  const rows = entries.map((entry) =>
    h("li", {}, [
      h("span", { text: entry.source }),
      h("span", {
        class: `state ${entry.ok ? "ok" : "bad"}`,
        title: entry.detail || "",
        text: entry.ok ? `ok · ${num(entry.item_count)}` : "failed",
      }),
    ]),
  );
  replaceChildren(
    $("health-list"),
    rows.length ? rows : h("li", {}, [h("span", { text: "No fetch health recorded" })]),
  );
}

/* ------------------------------------------------------------- Models view */

const MODEL_CATEGORIES = ["vlm_model", "omni_unified", "world_model"];

function familySummary() {
  const summary = new Map();
  for (const day of state.data.days) {
    for (const item of day.items || []) {
      for (const family of item.model_families || []) {
        const entry = summary.get(family) || { name: family, count: 0, lastSeen: "", best: null };
        entry.count += 1;
        if (day.date > entry.lastSeen) entry.lastSeen = day.date;
        if (!entry.best || item.total_score > entry.best.total_score) entry.best = item;
        summary.set(family, entry);
      }
    }
  }
  return [...summary.values()].sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
}

function renderModels() {
  const families = familySummary();
  $("family-count").textContent = `${families.length} tracked`;

  replaceChildren(
    $("family-grid"),
    families.length
      ? families.map((entry) =>
          h(
            "button",
            {
              class: "family-card",
              type: "button",
              onclick: () => {
                state.filters = { ...state.filters, family: entry.name, date: ALL };
                setView("today");
              },
            },
            [
              h("h3", { text: entry.name }),
              h("div", { class: "card-figure", text: num(entry.count) }),
              h("div", { class: "delta flat", text: `last seen ${entry.lastSeen}` }),
              entry.best ? h("div", { class: "card-note", text: truncate(entry.best.title, 84) }) : null,
            ],
          ),
        )
      : h("p", { class: "empty", text: "No tracked model families in the corpus yet." }),
  );

  const releases = [];
  for (const day of state.data.days.slice().reverse()) {
    for (const item of day.items || []) {
      if ((item.categories || []).some((key) => MODEL_CATEGORIES.includes(key))) {
        releases.push({ item, day });
      }
    }
  }
  releases.sort(
    (a, b) =>
      String(b.item.published_at || b.day.date).localeCompare(String(a.item.published_at || a.day.date)) ||
      b.item.total_score - a.item.total_score,
  );

  const cap = 60;
  $("release-count").textContent = `${num(releases.length)} records${
    releases.length > cap ? ` · showing ${cap}` : ""
  }`;
  replaceChildren(
    $("release-list"),
    releases.length
      ? releases.slice(0, cap).map(signalCard)
      : h("p", { class: "empty", text: "No model, omni, or world-model records yet." }),
  );
}

/* ------------------------------------------------------------- Trends view */

/* Tallest bar in the volume chart, in pixels. */
const PLOT_HEIGHT = 210;

function topCategories(limit) {
  const totals = new Map();
  for (const day of state.data.days) {
    for (const [key, value] of Object.entries(day.category_counts || {})) {
      totals.set(key, (totals.get(key) || 0) + value);
    }
  }
  return [...totals.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([key]) => key);
}

function renderTrends() {
  const days = state.data.days;
  const latest = days[days.length - 1];

  $("domain-date").textContent = latest ? `scan ${latest.date}` : "";
  const trends = latest ? latest.category_trends || [] : [];
  replaceChildren(
    $("domain-grid"),
    trends.length
      ? trends
          .filter((row) => row.count > 0)
          .map((row) => {
            const direction = row.delta > 0 ? "up" : row.delta < 0 ? "down" : "flat";
            const sign = row.delta > 0 ? "+" : "";
            return h(
              "button",
              {
                class: "domain-card",
                type: "button",
                style: `--topic-color:${categoryColor(row.category)}`,
                onclick: () => {
                  state.filters = { ...state.filters, category: row.category, date: latest.date };
                  setView("today");
                },
              },
              [
                h("h3", { text: categoryLabel(row.category) }),
                h("div", { class: "card-figure", text: num(row.count) }),
                h("div", {
                  class: `delta ${direction}`,
                  text: row.comparable
                    ? `${sign}${row.delta} vs previous scan`
                    : "no previous scan",
                }),
              ],
            );
          })
      : h("p", { class: "empty", text: "No topic counts recorded." }),
  );

  const legendKeys = topCategories(8);
  replaceChildren(
    $("trend-legend"),
    legendKeys.map((key) =>
      h("span", {}, [
        h("i", { style: `--swatch:${categoryColor(key)}` }),
        document.createTextNode(categoryLabel(key)),
      ]),
    ),
  );

  const maxTotal = Math.max(1, ...days.map((day) => day.item_count || 0));
  $("trend-message").textContent =
    days.length < 2
      ? "Only one scan on record, so there is nothing to compare yet."
      : `${days.length} scans, peak ${num(maxTotal)} records in a single scan. Bars stack the eight most common topics; a record in several topics is counted in each.`;

  replaceChildren(
    $("trend-chart"),
    days.map((day) => {
      const barHeight = Math.max(6, Math.round((day.item_count / maxTotal) * PLOT_HEIGHT));
      const segments = legendKeys
        .map((key) => [key, (day.category_counts || {})[key] || 0])
        .filter(([, value]) => value > 0);
      return h("div", { class: "trend-column" }, [
        h("span", { class: "trend-total", text: num(day.item_count) }),
        h(
          "div",
          {
            class: "trend-stack",
            style: `height:${barHeight}px`,
            title: `${day.date}: ${day.item_count} records`,
          },
          segments.map(([key, value]) =>
            h("i", {
              style: `flex:${value} 0 0;--swatch:${categoryColor(key)}`,
              title: `${categoryLabel(key)}: ${value}`,
            }),
          ),
        ),
        h("span", { class: "trend-label", text: day.date.slice(5) }),
      ]);
    }),
  );

  renderLedger();
}

function topEntries(counts, limit) {
  return Object.entries(counts || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit);
}

function renderLedger() {
  const days = state.data.days.slice().reverse();
  $("ledger-count").textContent = `${days.length} scans`;

  replaceChildren(
    $("ledger-body"),
    days.map((day) => {
      const selection = day.selection || {};
      const okCount = (day.health || []).filter((entry) => entry.ok).length;
      return h("tr", {}, [
        h("th", { scope: "row" }, [
          h("a", {
            href: `?date=${day.date}`,
            text: day.date,
            onclick: (event) => {
              event.preventDefault();
              state.filters = { ...state.filters, date: day.date };
              setView("today");
            },
          }),
        ]),
        h("td", {
          text: day.since
            ? `${String(day.since).slice(0, 16).replace("T", " ")} → ${String(
                day.generated_at || "",
              )
                .slice(0, 16)
                .replace("T", " ")}`
            : "—",
        }),
        h("td", { class: "numeric", text: num(day.item_count) }),
        h("td", { class: "numeric", text: num(day.pinned_count) }),
        h("td", {
          text:
            topEntries(day.source_counts, 3)
              .map(([name, value]) => `${name} ${value}`)
              .join(", ") || "—",
        }),
        h("td", {
          text:
            topEntries(day.category_counts, 3)
              .map(([key, value]) => `${categoryLabel(key)} ${value}`)
              .join(", ") || "—",
        }),
        h("td", {
          text: `${num(selection.fetched)} → ${num(selection.published)}`,
        }),
        h("td", { text: `${okCount}/${(day.health || []).length} ok` }),
      ]);
    }),
  );
}

/* ---------------------------------------------------------------- Map view */

const NODE_HEIGHT = 24;
const NODE_GAP = 9;
const COLUMN_WIDTH = 240;
const COLUMN_GAP = 130;
const MAP_PADDING = 30;

function svgEl(tag, attrs = {}) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
  return node;
}

function renderMap() {
  const corpus = state.data.corpus || {};
  const entities = corpus.entities || [];
  const edges = corpus.edges || [];

  const byKind = (kind) =>
    entities
      .filter((entity) => entity.kind === kind)
      .sort((a, b) => b.observations - a.observations || b.score - a.score);

  const sources = byKind("source").slice(0, 8);
  const topics = byKind("topic").slice(0, 12);
  const artifacts = byKind("artifact").slice(0, 14);

  $("map-summary").textContent = `${num(corpus.artifact_count)} artifacts and ${num(
    edges.length,
  )} relationships across ${num(corpus.generated_from_days)} scans. Showing the ${
    artifacts.length
  } highest-scoring artifacts.`;

  const columns = [
    { label: "Discovery source", nodes: sources },
    { label: "Artifact", nodes: artifacts },
    { label: "Topic", nodes: topics },
  ];

  const rows = Math.max(...columns.map((column) => column.nodes.length), 1);
  const height = MAP_PADDING * 2 + rows * (NODE_HEIGHT + NODE_GAP);
  const width = MAP_PADDING * 2 + columns.length * COLUMN_WIDTH + (columns.length - 1) * COLUMN_GAP;

  const svg = svgEl("svg", {
    viewBox: `0 0 ${width} ${height}`,
    preserveAspectRatio: "xMinYMin meet",
    role: "presentation",
    height,
  });

  const positions = new Map();
  columns.forEach((column, columnIndex) => {
    const x = MAP_PADDING + columnIndex * (COLUMN_WIDTH + COLUMN_GAP);
    const label = svgEl("text", { class: "map-column-label", x, y: MAP_PADDING - 12 });
    label.textContent = column.label;
    svg.append(label);

    column.nodes.forEach((entity, rowIndex) => {
      const y = MAP_PADDING + rowIndex * (NODE_HEIGHT + NODE_GAP);
      positions.set(entity.id, { x, y, width: COLUMN_WIDTH, column: columnIndex });
    });
  });

  const edgeLayer = svgEl("g", {});
  svg.append(edgeLayer);

  for (const edge of edges) {
    const from = positions.get(edge.source);
    const to = positions.get(edge.target);
    if (!from || !to) continue;
    const [left, right] = from.column <= to.column ? [from, to] : [to, from];
    const x1 = left.x + left.width;
    const y1 = left.y + NODE_HEIGHT / 2;
    const x2 = right.x;
    const y2 = right.y + NODE_HEIGHT / 2;
    const mid = (x1 + x2) / 2;
    const path = svgEl("path", {
      class: "map-edge",
      d: `M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`,
      "data-from": edge.source,
      "data-to": edge.target,
    });
    edgeLayer.append(path);
  }

  for (const column of columns) {
    for (const entity of column.nodes) {
      const position = positions.get(entity.id);
      const group = svgEl("g", { class: "map-node", tabindex: "0", role: "button" });
      group.dataset.id = entity.id;
      const rect = svgEl("rect", {
        x: position.x,
        y: position.y,
        width: position.width,
        height: NODE_HEIGHT,
      });
      const text = svgEl("text", {
        x: position.x + 8,
        y: position.y + NODE_HEIGHT / 2 + 4,
      });
      text.textContent = truncate(entity.label, 34);
      const title = svgEl("title");
      title.textContent = `${entity.label} — ${entity.observations} observation${
        entity.observations === 1 ? "" : "s"
      }`;
      group.append(rect, text, title);
      const activate = () => selectNode(entity);
      group.addEventListener("click", activate);
      group.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          activate();
        }
      });
      svg.append(group);
    }
  }

  replaceChildren($("map-canvas"), svg);
  if (state.selectedNode) highlightNode(state.selectedNode);
}

function highlightNode(id) {
  const canvas = $("map-canvas");
  canvas.querySelectorAll(".map-node").forEach((node) => {
    node.classList.toggle("selected", node.dataset.id === id);
  });
  canvas.querySelectorAll(".map-edge").forEach((edge) => {
    const active = edge.dataset.from === id || edge.dataset.to === id;
    edge.classList.toggle("active", active);
  });
}

function selectNode(entity) {
  state.selectedNode = entity.id;
  highlightNode(entity.id);

  const kindLabel = {
    artifact: "Artifact",
    topic: "Topic",
    source: "Discovery source",
    organization: "Organization",
    model_family: "Model family",
  };

  const actions = [];
  if (entity.kind === "artifact" && entity.url) {
    actions.push(
      h("a", {
        class: "ghost-button",
        href: entity.url,
        target: "_blank",
        rel: "noopener noreferrer",
        text: "Open record ↗",
      }),
    );
    actions.push(
      h("button", {
        class: "ghost-button",
        type: "button",
        text: "Find in Today",
        onclick: () => {
          state.filters = { ...state.filters, q: entity.label.slice(0, 60), date: ALL };
          setView("today");
        },
      }),
    );
  } else {
    const filterKey = {
      topic: "category",
      source: "source",
      organization: "organization",
      model_family: "family",
    }[entity.kind];
    const filterValue = entity.kind === "topic" ? entity.id.replace(/^topic:/, "") : entity.label;
    if (filterKey) {
      actions.push(
        h("button", {
          class: "ghost-button",
          type: "button",
          text: "Filter Today by this",
          onclick: () => {
            state.filters = { ...state.filters, [filterKey]: filterValue, date: ALL };
            setView("today");
          },
        }),
      );
    }
  }

  replaceChildren($("map-detail"), [
    h("p", { class: "eyebrow", text: kindLabel[entity.kind] || entity.kind }),
    h("h2", { text: entity.label }),
    keyValues([
      ["Observations", num(entity.observations)],
      ["Peak score", entity.score ? entity.score.toFixed(1) : ""],
      ["First seen", entity.first_seen],
      ["Last seen", entity.last_seen],
      ["Provenance", entity.provenance],
    ]),
    h("div", { class: "signal-actions" }, actions),
  ]);
}

/* -------------------------------------------------------------- Atlas view */

function atlasEntries() {
  const atlas = state.data.atlas || {};
  const rows = [];
  for (const section of atlas.sections || []) {
    for (const entry of section.entries || []) {
      rows.push({ ...entry, sectionKey: section.key, sectionTitle: section.title });
    }
  }
  // Newest first across the whole catalogue, not section by section.
  rows.sort((a, b) => String(b.published_at || "").localeCompare(String(a.published_at || "")));
  return rows;
}

function buildAtlasControls() {
  const atlas = state.data.atlas || {};
  const sections = atlas.sections || [];

  replaceChildren($("atlas-section"), [
    h("option", { value: ALL, text: `All sections (${sections.length})` }),
    ...sections.map((section) =>
      h("option", { value: section.key, text: `${section.title} · ${section.count}` }),
    ),
  ]);
  $("atlas-section").value = state.atlas.section;

  const categories = (atlas.category_counts || []).map((row) => row.category);
  replaceChildren($("atlas-category"), [
    h("option", { value: ALL, text: "All topics" }),
    ...categories.map((key) => h("option", { value: key, text: categoryLabel(key) })),
  ]);
  $("atlas-category").value = state.atlas.category;

  const origin = atlas.origin || {};
  $("atlas-origin").textContent = atlas.available
    ? `Parsed from ${origin.repository || "the survey repository"} — ${num(
        (atlas.counts || {}).entries,
      )} entries, ${num((atlas.counts || {}).reports)} progressive reports.`
    : atlas.detail || "No curated catalogue available.";
}

function renderAtlas() {
  const rows = atlasEntries().filter((entry) => {
    if (state.atlas.section !== ALL && entry.sectionKey !== state.atlas.section) return false;
    if (state.atlas.category !== ALL && !(entry.categories || []).includes(state.atlas.category)) {
      return false;
    }
    if (state.atlas.q) {
      const needle = state.atlas.q.toLowerCase();
      const haystack = [entry.title, entry.summary, entry.section, (entry.organizations || []).join(" ")]
        .join(" ")
        .toLowerCase();
      if (!haystack.includes(needle)) return false;
    }
    return true;
  });

  const cap = 240;
  $("atlas-count").textContent = `${num(rows.length)} entries${
    rows.length > cap ? ` · showing ${cap}` : ""
  }`;

  replaceChildren(
    $("atlas-list"),
    rows.length
      ? rows.slice(0, cap).map((entry) => {
          const columns = Object.entries(entry.columns || {});
          return h("details", { class: "atlas-entry" }, [
            h("summary", {}, [
              h("span", { class: "name" }, [
                h("a", {
                  href: entry.url,
                  target: "_blank",
                  rel: "noopener noreferrer",
                  text: entry.title,
                }),
              ]),
              h("span", { class: "signal-meta" }, [
                entry.published_at ? h("span", { text: shortDate(entry.published_at) }) : null,
                ...(entry.categories || []).slice(0, 4).map((key) =>
                  h("span", {
                    class: "pill topic",
                    text: categoryLabel(key),
                    style: `--pill-color:${categoryColor(key)}`,
                  }),
                ),
                ...(entry.model_families || []).map((family) =>
                  h("span", { class: "pill pin", text: family }),
                ),
              ]),
            ]),
            h("div", { class: "atlas-body" }, [
              keyValues([
                ["Section", entry.section || entry.sectionTitle],
                ["Organizations", (entry.organizations || []).join(", ")],
                ...columns.map(([label, value]) => [label, value]),
                ["Links", linkList(entry.artifact_urls)],
              ]),
            ]),
          ]);
        })
      : h("p", { class: "empty", text: "No catalogue entries match these filters." }),
  );
}

/* ------------------------------------------------------------------ rubric */

function openRubric(item) {
  const rubric = state.data.rubric || {};
  const weights = rubric.weights || {};
  const content = [];

  if (item) {
    content.push(h("p", { class: "eyebrow", text: "Score breakdown" }));
    content.push(h("h2", { text: truncate(item.title, 80) }));
    const components = [
      ["relevance", item.relevance_score],
      ["evidence", item.evidence_score],
      ["recency", item.recency_score],
      ["adoption", item.adoption_score],
    ];
    const table = h("table", {}, [
      h("thead", {}, [
        h("tr", {}, [
          h("th", { scope: "col", text: "Component" }),
          h("th", { scope: "col", text: "Score" }),
          h("th", { scope: "col", text: "Weight" }),
          h("th", { scope: "col", text: "Contribution" }),
        ]),
      ]),
      h(
        "tbody",
        {},
        components.map(([name, score]) =>
          h("tr", {}, [
            h("td", { text: titleCase(name) }),
            h("td", { class: "numeric", text: Number(score || 0).toFixed(1) }),
            h("td", { class: "numeric", text: Number(weights[name] || 0).toFixed(2) }),
            h("td", {
              class: "numeric",
              text: (Number(score || 0) * Number(weights[name] || 0)).toFixed(1),
            }),
          ]),
        ),
      ),
      h("tfoot", {}, [
        h("tr", {}, [
          h("th", { scope: "row", text: "Total" }),
          h("td", {}),
          h("td", {}),
          h("td", { class: "numeric", text: Number(item.total_score || 0).toFixed(1) }),
        ]),
      ]),
    ]);
    content.push(h("div", { class: "table-wrap" }, table));
    if ((item.rationale || []).length) {
      content.push(h("h3", { text: "Why it was kept" }));
      content.push(h("ul", {}, item.rationale.map((line) => h("li", { text: line }))));
    }
    content.push(h("h3", { text: "The rubric" }));
  } else {
    content.push(h("p", { class: "eyebrow", text: `Version ${rubric.version ?? "—"}` }));
    content.push(h("h2", { text: "How records are scored" }));
  }

  content.push(h("p", { text: rubric.summary || "" }));
  content.push(
    h("div", {
      class: "formula",
      text: Object.entries(weights)
        .map(([name, weight]) => `${weight} × ${name}`)
        .join("  +  "),
    }),
  );

  if ((rubric.components || []).length) {
    content.push(h("h3", { text: "Components" }));
    content.push(
      h(
        "ul",
        {},
        rubric.components.map((component) =>
          h("li", {}, [
            h("strong", { text: `${titleCase(component.name)} (${component.weight}) — ` }),
            document.createTextNode(component.detail),
          ]),
        ),
      ),
    );
  }

  if ((rubric.gates || []).length) {
    content.push(h("h3", { text: "Gates applied before scoring" }));
    content.push(h("ul", {}, rubric.gates.map((line) => h("li", { text: line }))));
  }

  const example = rubric.worked_example;
  if (example) {
    content.push(h("h3", { text: "Worked example" }));
    content.push(h("p", { text: example.scenario }));
    content.push(
      h("div", {
        class: "formula",
        text: `${(example.components || [])
          .map((row) => `${row.component} ${row.score} × ${row.weight} = ${row.contribution}`)
          .join("   ")}   ⇒ total ${example.total}`,
      }),
    );
  }

  if ((state.data.bands || []).length) {
    content.push(h("h3", { text: "Reading a score" }));
    content.push(
      h(
        "ul",
        {},
        state.data.bands.map((band) =>
          h("li", {
            text: `${band.label}${band.min ? ` (≥ ${band.min})` : ""} — ${band.detail}`,
          }),
        ),
      ),
    );
  }

  replaceChildren($("rubric-content"), content);
  const dialog = $("rubric-dialog");
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}

/* ------------------------------------------------------------------- views */

function setView(view) {
  state.view = VIEWS.includes(view) ? view : "today";
  for (const name of VIEWS) {
    $(`${name}-view`).hidden = name !== state.view;
  }
  document.querySelectorAll(".view-nav button[data-view]").forEach((button) => {
    if (button.dataset.view === state.view) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
  render();
  window.scrollTo({ top: 0, behavior: "instant" in window ? "instant" : "auto" });
}

function render() {
  buildFilterControls();
  if (state.view === "today") renderToday();
  else if (state.view === "models") renderModels();
  else if (state.view === "trends") renderTrends();
  else if (state.view === "map") renderMap();
  else if (state.view === "atlas") renderAtlas();
  writeUrl();
}

function renderChrome() {
  const site = state.data.site || {};
  if (site.title) {
    $("site-title").textContent = site.title;
    document.title = site.title;
  }
  if (site.tagline) $("site-tagline").textContent = site.tagline;

  const totals = state.data.totals || {};
  const stats = {
    days: num(totals.days),
    items: num(totals.items),
    atlas: num((state.data.atlas || {}).counts?.entries || 0),
    latest: state.data.latest_date || "—",
  };
  for (const [key, value] of Object.entries(stats)) {
    const node = document.querySelector(`[data-stat="${key}"]`);
    if (node) node.textContent = value;
  }

  const generated = String(state.data.generated_at || "").slice(0, 16).replace("T", " ");
  $("build-meta").textContent = `Rebuilt ${generated} UTC from ${num(
    state.data.snapshot_count,
  )} snapshots · scores rank discovery confidence, not research quality`;
}

/* -------------------------------------------------------------------- boot */

function wireEvents() {
  document.querySelectorAll(".view-nav button[data-view]").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });

  $("rubric-nav").addEventListener("click", () => openRubric(null));
  $("rubric-close").addEventListener("click", () => $("rubric-dialog").close());

  const bind = (id, key, immediate = false) => {
    const node = $(id);
    if (!node) return;
    node.addEventListener(immediate ? "input" : "change", () => {
      state.filters[key] = node.value;
      renderToday();
      writeUrl();
    });
  };

  bind("search-filter", "q", true);
  for (const [id, key] of [
    ["date-filter", "date"],
    ["category-filter", "category"],
    ["source-filter", "source"],
    ["family-filter", "family"],
    ["organization-filter", "organization"],
    ["event-filter", "event"],
    ["provenance-filter", "provenance"],
  ]) {
    bind(id, key);
  }

  $("filters").addEventListener("submit", (event) => event.preventDefault());
  $("atlas-filters").addEventListener("submit", (event) => event.preventDefault());

  $("clear-filters").addEventListener("click", () => {
    state.filters = {
      q: "",
      date: state.data.latest_date || ALL,
      category: ALL,
      source: ALL,
      family: ALL,
      organization: ALL,
      event: ALL,
      provenance: ALL,
    };
    render();
  });

  $("atlas-search").addEventListener("input", (event) => {
    state.atlas.q = event.target.value;
    renderAtlas();
  });
  $("atlas-section").addEventListener("change", (event) => {
    state.atlas.section = event.target.value;
    renderAtlas();
  });
  $("atlas-category").addEventListener("change", (event) => {
    state.atlas.category = event.target.value;
    renderAtlas();
  });
  $("atlas-clear").addEventListener("click", () => {
    state.atlas = { q: "", section: ALL, category: ALL };
    buildAtlasControls();
    renderAtlas();
  });
}

function showError(title, detail) {
  for (const name of VIEWS) $(`${name}-view`).hidden = true;
  document.querySelector(".view-nav").hidden = true;
  $("error-state").hidden = false;
  $("error-title").textContent = title;
  $("error-detail").textContent = detail;
  $("build-meta").textContent = "No data loaded";
}

async function init() {
  let payload;
  try {
    const response = await fetch(DATA_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    payload = await response.json();
  } catch (error) {
    showError("The data file could not be loaded.", `${DATA_URL} — ${error.message}`);
    return;
  }

  if (payload.schema_version !== SUPPORTED_SCHEMA) {
    showError(
      "This dashboard cannot read that data file.",
      `Expected schema_version ${SUPPORTED_SCHEMA}, found ${payload.schema_version}.`,
    );
    return;
  }
  if (!Array.isArray(payload.days) || payload.days.length === 0) {
    showError(
      "No scans on record yet.",
      "The data file loaded but contains no snapshots.",
    );
    return;
  }

  state.data = payload;
  (payload.taxonomy?.categories || []).forEach((category, index) => {
    state.categoryIndex.set(category.key, index);
    state.categoryLabels.set(category.key, category.label);
  });
  for (const day of payload.days) state.daysByDate.set(day.date, day);

  readUrl();
  renderChrome();
  buildAtlasControls();
  wireEvents();
  setView(state.view);
}

init();
