# VLM Radar

A daily radar for vision-language models: new model weights, papers, benchmarks,
and datasets, collected from primary sources, scored on a published rubric, and
rendered as a static dashboard.

It is a companion to [`zli12321/Vision-Language-Models-Overview`](https://github.com/zli12321/Vision-Language-Models-Overview),
a hand-curated survey of what already exists. This project answers the other
question: **what changed today.** The survey is also treated as a source, so its
dated progressive reports become part of the radar's history.

Published at **https://zli12321.github.io/VLM_Survey/**.

## Where things live

This collector sits inside the `zli12321.github.io` Jekyll site. Only the
generated dashboard is published; `_config.yml` excludes `VLM_Survey/collector`
from the build.

```
VLM_Survey/                 <- served at /VLM_Survey/
├── index.html
├── assets/{app.js,styles.css}
├── data/radar.json         <- generated, committed, read by the browser
└── collector/              <- this project, not published
    ├── config.yml
    ├── src/vlm_radar/
    └── data/{snapshots/,atlas.json}
```

```
config.yml ──> sources/ ──> pipeline ──> collector/data/snapshots/YYYY-MM-DD.json
                                              │
              survey README ──> collector/data/atlas.json
                                              │
                                              ▼
                                    ../data/radar.json ──> the dashboard
```

## Quick start

Requires Python 3.9 or newer. No Node, no bundler, no database.

```bash
cd VLM_Survey/collector

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'

# Build history from the survey's dated progressive reports, plus the catalogue.
vlm-radar seed

# Serve the dashboard at http://127.0.0.1:8000
vlm-radar serve --open
```

`config.yml` points `sources.survey.path` at a local checkout of the survey
repository. If yours lives elsewhere, set `VLM_RADAR_SURVEY_PATH` instead of
editing the file.

`vlm-radar seed` needs no network access: it reads the sibling survey repository
from disk. On the current survey checkout that yields 8 dated scans, 179 scored
records, 457 catalogued entries, and a 221-node entity graph — so the dashboard
has real content, real dates, and real trends before you ever hit an API.

To collect live data:

```bash
vlm-radar run --dry-run --only arxiv          # one source, nothing written
vlm-radar run                                 # every enabled source, snapshot, rebuild
```

Start with `--dry-run --only arxiv`: it needs no credentials and prints the
funnel plus per-source health, which is the fastest way to confirm the network
path works before committing a snapshot. A source that fails is reported in the
health table rather than aborting the scan, unless it is marked `required`.

## Commands

| Command | What it does |
| --- | --- |
| `vlm-radar run` | Collect from every enabled source, write today's snapshot, rebuild the dashboard and the Markdown digest. |
| `vlm-radar seed` | Replay the survey's progressive reports into dated snapshots. Offline. |
| `vlm-radar atlas` | Re-parse the survey README into `data/atlas.json`. |
| `vlm-radar rebuild` | Rebuild `site/data/radar.json` from existing snapshots. Deterministic. |
| `vlm-radar serve` | Serve `site/` locally with caching disabled. |
| `vlm-radar status` | Show configuration, snapshots on disk, and which sources are enabled. |

Useful flags: `run --only SOURCE ...`, `run --dry-run`, `run --now ISO8601` for
reproducible scans, `seed --overwrite`, `serve --port 9000`.

## How a record is chosen

Every scan publishes its funnel, so a quiet day is distinguishable from a broken
one:

```
fetched → deduplicated → in domain → not suppressed → above threshold → published
```

1. **Domain gate.** The upstream text must mention vision-language work at all.
   Without this, `benchmark` and `evaluation` pull in every text-only LLM paper.
2. **Category gate.** The record must land in at least one of the taxonomy
   buckets in `config.yml` (VLM releases, benchmarks, datasets, post-training,
   video, document/OCR, embodied/VLA, GUI agents, efficiency, hallucination,
   safety, and more).
3. **Suppression.** Placeholder uploads and withdrawn records are dropped.
   Quantized re-uploads and adapter weights are *demoted*, not hidden, so the
   funnel stays honest.
4. **Score.** A weighted 0–100 blend of relevance, evidence, recency, and
   adoption. The full rubric ships inside `radar.json` and is readable from the
   dashboard's Rubric panel.
5. **Pins.** A hit on a tracked model family (Qwen-VL, InternVL, LLaVA, Gemini,
   Molmo, …) or a watchlisted benchmark (MMMU, MMBench, MathVista, Video-MME, …)
   pins the record above generic ranking. A pin is a routing decision, not a
   quality claim.

A score ranks *discovery confidence*, never research quality.

## Sources

All defaults work without credentials.

| Source | What it catches | Auth |
| --- | --- | --- |
| arXiv category RSS | `cs.CV`, `cs.CL`, `cs.AI`, `cs.LG`, `cs.RO`, `cs.MM` daily announcements | none |
| Hugging Face models | new and updated VLM weights | none |
| Hugging Face datasets | benchmark and instruction-tuning data | none |
| Hugging Face papers | the community-voted daily papers feed | none |
| GitHub search | new repositories | optional `GITHUB_TOKEN` for higher rate limits |
| GitHub releases | versioned drops from an allowlist of VLM projects and eval harnesses | optional token |
| Semantic Scholar | venue and citation context | optional key |
| OpenAlex | institutional affiliations (off by default) | none |
| Survey repository | the curated progressive reports, read from disk | none |

Copy `.env.example` to `.env` and export it if you want the optional keys. Add a
source by writing a `fetch(spec, ctx)` callable and registering it in
`src/vlm_radar/sources/__init__.py`; nothing else needs to change.

## The dashboard

The published folder is plain HTML, one CSS file, and one ES module. There is no
build step, so the deployed artifact is the source. Every path in it is relative,
which is what lets it serve from `/VLM_Survey/` rather than a domain root.

- **Today** — every record from a chosen scan date, filterable by search, topic,
  source, model family, organization, event kind, and provenance.
- **Models** — releases grouped by tracked model family, plus the newest weights
  and datasets on the Hub.
- **Trends** — per-topic volume by day, momentum against the previous scan, and a
  daily ledger with source mix and fetch health.
- **Atlas** — the curated catalogue parsed from the survey README, browsable by
  section.
- **Rubric** — the scoring definition, with a worked example you can check.

## Data layout

| Path | Tracked | Meaning |
| --- | --- | --- |
| `collector/data/snapshots/YYYY-MM-DD.json` | yes | Canonical daily record. Append-only. |
| `collector/data/atlas.json` | yes | Catalogue parsed from the survey README. |
| `data/radar.json` | yes | Everything the browser reads, rebuilt from the above. |
| `collector/out/report.md` | no | Markdown digest for a GitHub Issue. |

Two of these are derived but still committed, for the same underlying reason:
nothing regenerates them at deploy time. Jekyll only copies files, so
`data/radar.json` has to be in the repository. And `atlas.json` is derived from a
*different repository*, so a build that could not find the survey checkout would
publish an empty Atlas without failing.

Snapshots are the source of truth; the dashboard is derived. `vlm-radar rebuild`
is deterministic, so the same snapshots always produce the same site. The
snapshot contract is documented in `docs/snapshot.schema.json`.

## Scheduling

Nothing scans on its own locally: a snapshot is written only when you run
`vlm-radar run`. Automatic daily scans come from GitHub Actions.

The site repository's `.github/workflows/vlm-radar.yml` runs at 06:20 UTC. It:

1. checks out `zli12321/Vision-Language-Models-Overview` into `.survey-source/`
   and refreshes `data/atlas.json`, so the Atlas tracks the survey without anyone
   rebuilding it by hand. It points the collector there with
   `VLM_RADAR_SURVEY_PATH`, which overrides `sources.survey.path`;
2. runs `ruff` and `pytest` before touching any data;
3. scans, writes a dated snapshot, and rebuilds `../data/radar.json`;
4. commits, then **calls** `deploy.yml` to rebuild the Jekyll site;
5. opens or updates a dated Issue with the digest.

Step 4 calls the deploy workflow explicitly rather than letting the commit
trigger it, because GitHub suppresses workflow triggers for pushes made with the
default `GITHUB_TOKEN`. Relying on the push would commit data that never reached
the site. That is why `deploy.yml` carries a `workflow_call:` trigger.

The commit step also refuses to stage anything outside the snapshot directory,
`atlas.json`, and `radar.json`, so a misbehaving scan cannot rewrite the website.

For this to work, Settings → Actions → General → Workflow permissions must be
**Read and write**.

Two things to know about scheduled workflows: cron is best-effort and can run
late under load, and GitHub disables schedules after 60 days without repository
activity on public repos, which the daily commit is enough to prevent.

To schedule on your own machine instead, run `vlm-radar run` from `launchd` on
macOS or `cron` elsewhere, using the interpreter inside `.venv`.

A missed day is not fully recoverable: arXiv's RSS feed only serves the current
announcement cycle. Hub and repository sources sort by last-modified date, so
widening `radar.lookback_hours` lets a late scan catch up on those.

## Development

```bash
ruff check .
ruff format --check .
pytest -q
vlm-radar rebuild        # must stay deterministic
```

Runtime dependencies are `PyYAML` and `certifi`. HTTP goes through
`urllib` in `src/vlm_radar/http.py` so a fresh checkout stays installable
anywhere.

## License

MIT.
