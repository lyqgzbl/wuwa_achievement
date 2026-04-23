#!/usr/bin/env python3
"""Build offline zh-Hans achievement tracker HTML directly from unpacked DB files.

This is an end-to-end single-script flow:
- Input: db_achievement.db (config DB with BinData BLOB)
- Input: one or more lang_multi_text*.db (MultiText DBs for zh-Hans)
- Output: a single offline HTML page (progress stored in browser localStorage)

Requirements:
- This script does NOT scan folders for dependencies.
  You must pass every required DB explicitly.

Example:
  python -m Tools \
    --config-db /path/to/db_achievement.db \
    --multitext-db /path/to/zh-Hans/lang_multi_text.db \
    --multitext-db /path/to/zh-Hans/lang_multi_text_1sthalf.db \
    --out out/achievement_tracker_zh.html
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .dataset import build_dataset
from .db_loader import (
    collect_wanted_text_ids,
    load_from_config_db,
    load_multitext_from_dbs,
    validate_multitext_db,
)
from .html_renderer import render_html

logger = logging.getLogger(__name__)


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _resolve_path(root: Path, value: str) -> Path:
    p = Path(value)
    if p.is_absolute():
        return p
    # Prefer root-relative path over cwd-relative to avoid accidental misuse.
    root_candidate = (root / p).resolve()
    if root_candidate.exists():
        return root_candidate
    if p.exists():
        return p.resolve()
    return root_candidate


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(
        description="Build an offline zh-Hans achievement tracker HTML from DB files"
    )
    parser.add_argument(
        "--root", default=".", help="Output root (default: current directory)"
    )
    parser.add_argument(
        "--out", default="out/achievement_tracker_zh.html", help="Output HTML path"
    )
    parser.add_argument(
        "--locale",
        default="zh-Hans",
        help="Locale label embedded into export (default: zh-Hans)",
    )
    parser.add_argument(
        "--config-db",
        required=True,
        help="Path to db_achievement.db",
    )
    parser.add_argument(
        "--multitext-db",
        action="append",
        default=[],
        required=True,
        help="Path to lang_multi_text*.db (can be passed multiple times)",
    )

    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_path = (
        (root / args.out).resolve()
        if not Path(args.out).is_absolute()
        else Path(args.out).resolve()
    )

    config_db = _resolve_path(root, args.config_db)
    if not config_db.exists():
        raise SystemExit(f"Config DB not found: {config_db}")

    multitext_dbs = [_resolve_path(root, v) for v in args.multitext_db]
    for p in multitext_dbs:
        validate_multitext_db(p)

    achievements, groups, categories = load_from_config_db(config_db)
    wanted = collect_wanted_text_ids(achievements, groups, categories)
    texts = load_multitext_from_dbs(multitext_dbs, wanted)

    dataset = build_dataset(args.locale, achievements, groups, categories, texts)

    _ensure_parent_dir(out_path)
    out_path.write_text(render_html(dataset), encoding="utf-8")
    logger.info("Wrote %s", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
