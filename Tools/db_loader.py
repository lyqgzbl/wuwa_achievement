"""SQLite database loaders for achievement config and multi-text data."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path

from .flatbuffers_parser import _get_i32, _get_str, _parse_table
from .models import Achievement, Category, Group


# ---------------------------------------------------------------------------
# FlatBuffers blob decoders
# ---------------------------------------------------------------------------


def _decode_achievement(blob: bytes) -> Achievement:
    table_start, offs = _parse_table(blob)

    aid = _get_i32(blob, table_start, offs, 0, default=0)
    gid = _get_i32(blob, table_start, offs, 1, default=0)
    level = _get_i32(blob, table_start, offs, 2, default=0)
    name_key = _get_str(blob, table_start, offs, 3)
    desc_key = _get_str(blob, table_start, offs, 4)

    if not aid or not gid:
        raise ValueError("decoded achievement missing Id/GroupId")

    return Achievement(
        id=aid, group_id=gid, level=level, name_key=name_key, desc_key=desc_key
    )


def _decode_group(blob: bytes) -> Group:
    table_start, offs = _parse_table(blob)

    gid = _get_i32(blob, table_start, offs, 0, default=0)
    cat = _get_i32(blob, table_start, offs, 1, default=0)
    sort = _get_i32(blob, table_start, offs, 2, default=0)
    name_key = _get_str(blob, table_start, offs, 3)

    if not gid or not cat:
        raise ValueError("decoded group missing Id/Category")

    return Group(id=gid, category_id=cat, sort=sort, name_key=name_key)


def _decode_category(blob: bytes) -> Category:
    table_start, offs = _parse_table(blob)

    cid = _get_i32(blob, table_start, offs, 0, default=0)
    name_key = _get_str(blob, table_start, offs, 1)

    if not cid:
        raise ValueError("decoded category missing Id")

    return Category(id=cid, name_key=name_key)


# ---------------------------------------------------------------------------
# Text ID collection
# ---------------------------------------------------------------------------


def collect_wanted_text_ids(
    achievements: Sequence[Achievement],
    groups: Sequence[Group],
    categories: Sequence[Category],
) -> set[str]:
    wanted: set[str] = set()

    def add(value: str) -> None:
        value = (value or "").strip()
        if value:
            wanted.add(value)

    for a in achievements:
        add(a.name_key)
        add(a.desc_key)
    for g in groups:
        add(g.name_key)
    for c in categories:
        add(c.name_key)

    return wanted


# ---------------------------------------------------------------------------
# MultiText DB loader
# ---------------------------------------------------------------------------


def load_multitext_from_dbs(
    multitext_dbs: Sequence[Path], wanted_ids: set[str]
) -> dict[str, str]:
    """Load only wanted Id->Content from one or more MultiText DBs.

    If an Id appears in multiple DBs, the first match wins.
    """

    wanted_list = sorted(wanted_ids)
    found: dict[str, str] = {}

    # SQLite default max variables is usually 999.
    batch_size = 900

    for db_path in multitext_dbs:
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        try:
            for i in range(0, len(wanted_list), batch_size):
                batch = wanted_list[i : i + batch_size]
                missing = [x for x in batch if x not in found]
                if not missing:
                    continue

                placeholders = ",".join(["?"] * len(missing))
                rows = con.execute(
                    f"SELECT Id, Content FROM MultiText WHERE Id IN ({placeholders})",
                    missing,
                ).fetchall()

                for r in rows:
                    tid = str(r["Id"])
                    if tid in found:
                        continue
                    found[tid] = str(r["Content"] or "")
        finally:
            con.close()

    return found


# ---------------------------------------------------------------------------
# DB validation
# ---------------------------------------------------------------------------


def validate_multitext_db(path: Path) -> None:
    """Validate that *path* is a usable MultiText database."""

    if not path.exists():
        raise SystemExit(f"MultiText DB not found: {path}")

    con = sqlite3.connect(path)
    try:
        r = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='MultiText' LIMIT 1"
        ).fetchone()
        if not r:
            raise SystemExit(f"Not a MultiText DB (missing table MultiText): {path}")

        cols = con.execute("PRAGMA table_info(MultiText)").fetchall()
        names = {c[1] for c in cols}
        if "Id" not in names or "Content" not in names:
            raise SystemExit(f"MultiText schema unexpected (needs Id, Content): {path}")
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Config DB loader
# ---------------------------------------------------------------------------


def load_from_config_db(
    config_db: Path,
) -> tuple[list[Achievement], list[Group], list[Category]]:
    con = sqlite3.connect(config_db)
    con.row_factory = sqlite3.Row
    try:
        ach_rows = con.execute(
            "SELECT Id, GroupId, BinData FROM achievement ORDER BY Id"
        ).fetchall()
        grp_rows = con.execute(
            "SELECT Id, Category, BinData FROM achievementgroup ORDER BY Id"
        ).fetchall()
        cat_rows = con.execute(
            "SELECT Id, BinData FROM achievementcategory ORDER BY Id"
        ).fetchall()
    finally:
        con.close()

    achievements: list[Achievement] = []
    for r in ach_rows:
        achievements.append(_decode_achievement(r["BinData"]))  # type: ignore[arg-type]

    groups: list[Group] = []
    for r in grp_rows:
        groups.append(_decode_group(r["BinData"]))  # type: ignore[arg-type]

    categories: list[Category] = []
    for r in cat_rows:
        categories.append(_decode_category(r["BinData"]))  # type: ignore[arg-type]

    return achievements, groups, categories
