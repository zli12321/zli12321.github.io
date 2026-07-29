"""Command line entry point.

vlm-radar run        collect, snapshot today, rebuild the dashboard
vlm-radar seed       replay the survey's progressive reports into snapshots
vlm-radar atlas      rebuild the curated catalogue from the survey README
vlm-radar rebuild    rebuild the dashboard from existing snapshots
vlm-radar serve      serve site/ locally
vlm-radar status     show what is on disk and which sources are enabled
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__, atlas, pipeline, report, seed, snapshots
from . import serve as serve_module
from .config import Settings
from .sources import SOURCE_FETCHERS, SOURCE_LABELS
from .textutil import day_key, parse_datetime, utcnow


def _settings(args: argparse.Namespace) -> Settings:
    return Settings.load(Path(args.root) if getattr(args, "root", None) else None)


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def command_run(args: argparse.Namespace) -> int:
    settings = _settings(args)
    settings.ensure_directories()
    now = parse_datetime(args.now) or utcnow()

    run = pipeline.run_pipeline(settings, now=now, only=args.only or None)
    date = args.date or day_key(now)

    print(report.render_terminal(run, settings))

    if args.dry_run:
        print("\nDry run: nothing written.")
        return 0

    snapshot = snapshots.write_snapshot(settings, run, date=date)
    digest = report.render_markdown(run, settings, date=date)
    settings.out_dir.mkdir(parents=True, exist_ok=True)
    (settings.out_dir / "report.md").write_text(digest, encoding="utf-8")
    (settings.out_dir / "items.json").write_text(
        json.dumps(snapshots.snapshot_payload(run, date=date), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    dashboard = snapshots.write_dashboard(settings)

    print(f"\nwrote {_relative(snapshot, settings.root)}")
    print(f"wrote {_relative(settings.out_dir / 'report.md', settings.root)}")
    print(f"wrote {_relative(dashboard, settings.root)}")
    return 0


def command_seed(args: argparse.Namespace) -> int:
    settings = _settings(args)
    settings.ensure_directories()
    results = seed.seed_from_survey(settings, overwrite=args.overwrite)

    for entry in results:
        if entry["skipped"]:
            print(f"  skip {entry['date']}  (snapshot exists; pass --overwrite to replace)")
        else:
            print(
                f"  seed {entry['date']}  {entry['published']:>4} published "
                f"of {entry['fetched']} curated entries"
            )
    if not args.no_rebuild:
        atlas.write_atlas(settings)
        dashboard = snapshots.write_dashboard(settings)
        print(f"\nwrote {_relative(dashboard, settings.root)}")
    return 0


def command_atlas(args: argparse.Namespace) -> int:
    settings = _settings(args)
    payload = atlas.write_atlas(settings)
    if not payload.get("available"):
        print(payload.get("detail", "atlas unavailable"))
        return 1
    counts = payload.get("counts", {})
    print(
        f"catalogued {counts.get('entries', 0)} entries across "
        f"{counts.get('sections', 0)} sections "
        f"({counts.get('reports', 0)} progressive reports seen)"
    )
    for section in payload.get("sections", []):
        print(f"  {section['count']:>4}  {section['title']}")
    print(f"\nwrote {_relative(settings.atlas_path, settings.root)}")
    return 0


def command_rebuild(args: argparse.Namespace) -> int:
    settings = _settings(args)
    settings.ensure_directories()
    if args.refresh_atlas:
        atlas.write_atlas(settings)
    path = snapshots.write_dashboard(settings)
    payload = json.loads(path.read_text(encoding="utf-8"))
    totals = payload.get("totals", {})
    print(
        f"rebuilt {_relative(path, settings.root)} from {payload.get('snapshot_count', 0)} "
        f"snapshots ({totals.get('items', 0)} records, "
        f"{len(payload.get('corpus', {}).get('entities', []))} graph nodes)"
    )
    return 0


def command_serve(args: argparse.Namespace) -> int:
    settings = _settings(args)
    if args.rebuild:
        snapshots.write_dashboard(settings)
    port = args.port if args.port else serve_module.free_port(8000)
    serve_module.serve(settings.site_dir, host=args.host, port=port, open_browser=args.open)
    return 0


def command_status(args: argparse.Namespace) -> int:
    settings = _settings(args)
    print(f"vlm-radar {__version__}")
    print(f"root            {settings.root}")
    survey_root = settings.survey_root()
    print(f"survey repo     {survey_root or 'not found'}")
    print(
        f"lookback        {settings.lookback_hours:g}h "
        f"(curated {settings.curated_lookback_hours:g}h)"
    )
    print(f"minimum score   {settings.minimum_score:g}/100")

    existing = sorted(settings.snapshots_dir.glob("*.json"))
    print(f"snapshots       {len(existing)}", end="")
    if existing:
        print(f"  ({existing[0].stem} → {existing[-1].stem})")
    else:
        print("  (run 'vlm-radar seed' or 'vlm-radar run')")
    print(f"dashboard       {'built' if settings.dashboard_path.is_file() else 'missing'}")

    print("\nsources")
    for key in SOURCE_FETCHERS:
        spec = settings.source(key)
        state = "on " if spec.get("enabled") else "off"
        flag = " (required)" if spec.get("required") else ""
        print(f"  {state} {SOURCE_LABELS.get(key, key)}{flag}")

    reports = seed.available_reports(settings)
    if reports:
        print("\nprogressive reports available to seed")
        for date, count in reports.items():
            print(f"  {date}  {count:>4} entries")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vlm-radar",
        description="Daily radar for vision-language model releases, papers, and benchmarks.",
    )
    parser.add_argument("--version", action="version", version=f"vlm-radar {__version__}")
    parser.add_argument("--root", help="Repository root (defaults to the nearest config.yml)")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Collect, snapshot, and rebuild the dashboard")
    run_parser.add_argument("--date", help="Snapshot date (YYYY-MM-DD, defaults to today UTC)")
    run_parser.add_argument(
        "--now", help="Override the scan time (ISO 8601), for reproducible runs"
    )
    run_parser.add_argument(
        "--only",
        nargs="+",
        metavar="SOURCE",
        choices=sorted(SOURCE_FETCHERS),
        help="Restrict the scan to these source keys",
    )
    run_parser.add_argument("--dry-run", action="store_true", help="Print results without writing")
    run_parser.set_defaults(handler=command_run)

    seed_parser = subparsers.add_parser(
        "seed", help="Replay the survey's progressive reports into dated snapshots"
    )
    seed_parser.add_argument("--overwrite", action="store_true", help="Replace existing snapshots")
    seed_parser.add_argument(
        "--no-rebuild", action="store_true", help="Skip the dashboard rebuild afterwards"
    )
    seed_parser.set_defaults(handler=command_seed)

    atlas_parser = subparsers.add_parser("atlas", help="Rebuild the curated catalogue")
    atlas_parser.set_defaults(handler=command_atlas)

    rebuild_parser = subparsers.add_parser(
        "rebuild", help="Rebuild site/data/radar.json from existing snapshots"
    )
    rebuild_parser.add_argument(
        "--refresh-atlas", action="store_true", help="Re-parse the survey README first"
    )
    rebuild_parser.set_defaults(handler=command_rebuild)

    serve_parser = subparsers.add_parser("serve", help="Serve site/ on localhost")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument(
        "--port", type=int, default=0, help="Port (0 picks 8000 or a free one)"
    )
    serve_parser.add_argument("--open", action="store_true", help="Open a browser window")
    serve_parser.add_argument(
        "--rebuild", action="store_true", help="Rebuild the dashboard before serving"
    )
    serve_parser.set_defaults(handler=command_serve)

    status_parser = subparsers.add_parser("status", help="Show configuration and what is on disk")
    status_parser.set_defaults(handler=command_status)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    raw = list(argv) if argv is not None else sys.argv[1:]
    args = parser.parse_args(raw)
    if not getattr(args, "command", None):
        args = parser.parse_args(raw + ["run"])
    try:
        return int(args.handler(args) or 0)
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
    except (RuntimeError, snapshots.SnapshotError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
