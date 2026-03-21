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
  python Tools/build_achievement_tracker_zh_from_dbs.py \
    --config-db /path/to/db_achievement.db \
    --multitext-db /path/to/zh-Hans/lang_multi_text.db \
    --multitext-db /path/to/zh-Hans/lang_multi_text_1sthalf.db \
    --out out/achievement_tracker_zh.html
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


def _u16(b: bytes, pos: int) -> int:
    return int.from_bytes(b[pos : pos + 2], "little")


def _i32(b: bytes, pos: int) -> int:
    return int.from_bytes(b[pos : pos + 4], "little", signed=True)


def _u32(b: bytes, pos: int) -> int:
    return int.from_bytes(b[pos : pos + 4], "little", signed=False)


def _read_string(b: bytes, table_start: int, field_off: int) -> str:
    if field_off == 0:
        return ""
    p = table_start + field_off
    rel = _i32(b, p)
    s0 = p + rel
    if s0 < 0 or s0 + 4 > len(b):
        return ""
    n = _i32(b, s0)
    if n < 0 or s0 + 4 + n > len(b):
        return ""
    return b[s0 + 4 : s0 + 4 + n].decode("utf-8", errors="replace")


def _parse_table(blob: bytes) -> tuple[int, list[int]]:
    """Return (table_start, field_offsets[]) for a FlatBuffers table."""

    if len(blob) < 8:
        raise ValueError("blob too small")

    table_start = _u32(blob, 0)
    if table_start >= len(blob):
        raise ValueError("invalid root/table_start")

    vtable_off = _i32(blob, table_start)
    vtable_start = table_start - vtable_off
    if vtable_start < 0 or vtable_start + 4 > len(blob):
        raise ValueError("invalid vtable_start")

    vtable_len = _u16(blob, vtable_start)
    if vtable_start + vtable_len > len(blob):
        raise ValueError("invalid vtable_len")

    field_count = (vtable_len - 4) // 2
    offs = [_u16(blob, vtable_start + 4 + i * 2) for i in range(field_count)]
    return table_start, offs


def _get_i32(
    blob: bytes, table_start: int, offs: Sequence[int], idx: int, default: int = 0
) -> int:
    if idx >= len(offs):
        return default
    off = offs[idx]
    if off == 0:
        return default
    return _i32(blob, table_start + off)


def _get_str(
    blob: bytes, table_start: int, offs: Sequence[int], idx: int, default: str = ""
) -> str:
    if idx >= len(offs):
        return default
    off = offs[idx]
    if off == 0:
        return default
    return _read_string(blob, table_start, off)


@dataclass(frozen=True)
class Achievement:
    id: int
    group_id: int
    level: int
    name_key: str
    desc_key: str


@dataclass(frozen=True)
class Group:
    id: int
    category_id: int
    sort: int
    name_key: str


@dataclass(frozen=True)
class Category:
    id: int
    name_key: str


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
            # Some dumps include RedirectDbIndex, some don't; we only need Id/Content.
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


def render_html(dataset: dict[str, Any]) -> str:
    dataset_json = json.dumps(dataset, ensure_ascii=False)

    # Minimal, single-file offline HTML.
    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>鸣潮 成就统计</title>
  <style>
    :root {{ color-scheme: light dark; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif; margin: 16px; }}
    header {{ display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; }}
    .muted {{ opacity: .7; }}
    .counter {{ font-variant-numeric: tabular-nums; }}
        details {{ margin: 8px 0; }}
        summary {{ cursor: pointer; user-select: none; }}
        summary::-webkit-details-marker {{ display: none; }}
        summary::before {{ content: '▸'; display: inline-block; width: 1em; }}
        details[open] > summary::before {{ content: '▾'; }}
        .tree {{ list-style: none; padding-left: 0; margin: 10px 0 0; }}
        .tree details {{ margin-left: 0; }}
        .tree .node {{ margin-left: 18px; }}
        .ach-list {{ list-style: none; padding-left: 22px; margin: 6px 0 10px; }}
        .ach-item {{ display: grid; grid-template-columns: 22px 1fr; gap: 8px; padding: 6px 0; border-bottom: 1px solid rgba(127,127,127,.18); }}
        .ach-title {{ font-weight: 600; }}
        .ach-desc {{ white-space: pre-wrap; margin-top: 2px; }}
    .nowrap {{ white-space: nowrap; }}
    .small {{ font-size: 12px; }}
    input[type=\"search\"] {{ min-width: 260px; padding: 6px 10px; }}
    .toolbar {{ display:flex; gap:10px; align-items:center; flex-wrap: wrap; margin-top: 8px; }}
    .pill {{ padding: 2px 8px; border: 1px solid rgba(127,127,127,.35); border-radius: 999px; }}
  </style>
</head>
<body>
  <header>
    <h2 style=\"margin:0\">成就统计</h2>
    <span id=\"overall\" class=\"counter muted\"></span>
  </header>

  <div class=\"toolbar\">
        <input id=\"q\" type=\"search\" placeholder=\"搜索成就名称/描述\" />
    <label class=\"pill\"><input id=\"onlyTodo\" type=\"checkbox\" /> 仅未完成</label>
        <button id=\"exportBtn\" type=\"button\">导出</button>
        <button id=\"importBtn\" type=\"button\">导入</button>
        <input id=\"importFile\" type=\"file\" accept=\"application/json\" style=\"display:none\" />
    <span class=\"muted small\">完成状态保存在浏览器 localStorage</span>
  </div>

  <div id=\"app\"></div>

<script>
const DATA = {dataset_json};
const STORAGE_KEY = 'ww_achievement_completed_v1';
const OPEN_CAT_KEY = 'ww_achievement_open_categories_v1';
const OPEN_GRP_KEY = 'ww_achievement_open_groups_v1';
const EXPORT_KEY = 'ww_achievement_export_v1';

function loadCompleted() {{
  try {{
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw);
    return new Set(Array.isArray(arr) ? arr : []);
  }} catch {{
    return new Set();
  }}
}}

function saveCompleted(set) {{
  localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(set)));
}}

function loadOpenSet(key) {{
    try {{
        const raw = localStorage.getItem(key);
        if (!raw) return new Set();
        const arr = JSON.parse(raw);
        return new Set(Array.isArray(arr) ? arr.map(String) : []);
    }} catch {{
        return new Set();
    }}
}}

function saveOpenSet(key, set) {{
    localStorage.setItem(key, JSON.stringify(Array.from(set)));
}}

function exportProgress() {{
    const payload = {{
        schema: EXPORT_KEY,
        locale: DATA.locale,
        exportedAt: new Date().toISOString(),
        completed: Array.from(loadCompleted()),
        openCategories: Array.from(loadOpenSet(OPEN_CAT_KEY)),
        openGroups: Array.from(loadOpenSet(OPEN_GRP_KEY)),
    }};

    const blob = new Blob([JSON.stringify(payload, null, 2)], {{ type: 'application/json' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ww_achievement_progress.json';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}}

async function importProgressFromFile(file) {{
    const text = await file.text();
    let payload;
    try {{
        payload = JSON.parse(text);
    }} catch {{
        alert('导入失败：不是有效的 JSON 文件');
        return;
    }}

    if (!payload || payload.schema !== EXPORT_KEY) {{
        alert('导入失败：文件格式不匹配');
        return;
    }}

    const completed = Array.isArray(payload.completed) ? payload.completed : [];
    const openCategories = Array.isArray(payload.openCategories) ? payload.openCategories : [];
    const openGroups = Array.isArray(payload.openGroups) ? payload.openGroups : [];

    localStorage.setItem(STORAGE_KEY, JSON.stringify(completed));
    localStorage.setItem(OPEN_CAT_KEY, JSON.stringify(openCategories.map(String)));
    localStorage.setItem(OPEN_GRP_KEY, JSON.stringify(openGroups.map(String)));
    render();
}}

function textIncludes(hay, needle) {{
  if (!needle) return true;
  return (hay || '').toLowerCase().includes(needle);
}}

function computeCounts(categories, completed) {{
  let total = 0;
  let done = 0;
  for (const cat of categories) {{
    for (const grp of cat.groups) {{
      for (const a of grp.achievements) {{
        total++;
        if (completed.has(a.id)) done++;
      }}
    }}
  }}
  return {{total, done}};
}}

function computeNodeCounts(cat, completed) {{
    let total = 0;
    let done = 0;
    for (const grp of cat.groups) {{
        for (const a of grp.achievements) {{
            total++;
            if (completed.has(a.id)) done++;
        }}
    }}
    return {{total, done}};
}}

function computeGroupCounts(grp, completed) {{
    let total = 0;
    let done = 0;
    for (const a of grp.achievements) {{
        total++;
        if (completed.has(a.id)) done++;
    }}
    return {{total, done}};
}}

function render() {{
  const completed = loadCompleted();
    const openCats = loadOpenSet(OPEN_CAT_KEY);
    const openGrps = loadOpenSet(OPEN_GRP_KEY);
  const q = (document.getElementById('q').value || '').trim().toLowerCase();
  const onlyTodo = document.getElementById('onlyTodo').checked;

  const counts = computeCounts(DATA.categories, completed);
    document.getElementById('overall').textContent = '已完成 ' + counts.done + '/' + counts.total;

  const app = document.getElementById('app');
  app.innerHTML = '';

    const rootUl = document.createElement('ul');
    rootUl.className = 'tree';
    app.appendChild(rootUl);

    for (const cat of DATA.categories) {{
        // If searching, only show categories with matches.
        let catHasAny = false;
        for (const grp of cat.groups) {{
            for (const a of grp.achievements) {{
                const isDone = completed.has(a.id);
                const match = textIncludes(a.name, q) || textIncludes(a.desc, q);
                if (match && !(onlyTodo && isDone)) {{
                    catHasAny = true;
                    break;
                }}
            }}
            if (catHasAny) break;
        }}
        if (q && !catHasAny) continue;

        const liCat = document.createElement('li');
        const catDetails = document.createElement('details');
        const catId = String(cat.id);
        catDetails.open = q ? true : openCats.has(catId);
        catDetails.addEventListener('toggle', () => {{
            const set = loadOpenSet(OPEN_CAT_KEY);
            if (catDetails.open) set.add(catId); else set.delete(catId);
            saveOpenSet(OPEN_CAT_KEY, set);
        }});

        const catSummary = document.createElement('summary');
        catSummary.className = 'counter';
        const catCounts = computeNodeCounts(cat, completed);
        catSummary.textContent = cat.name + '  (' + catCounts.done + '/' + catCounts.total + ')';
        catDetails.appendChild(catSummary);

        const catNode = document.createElement('div');
        catNode.className = 'node';

        for (const grp of cat.groups) {{
            // If searching, only show groups with matches.
            let grpHasAny = false;
            for (const a of grp.achievements) {{
                const isDone = completed.has(a.id);
                const match = textIncludes(a.name, q) || textIncludes(a.desc, q);
                if (match && !(onlyTodo && isDone)) {{
                    grpHasAny = true;
                    break;
                }}
            }}
            if (q && !grpHasAny) continue;

            const grpDetails = document.createElement('details');
            const grpId = String(grp.id);
            grpDetails.open = q ? true : openGrps.has(grpId);
            grpDetails.addEventListener('toggle', () => {{
                const set = loadOpenSet(OPEN_GRP_KEY);
                if (grpDetails.open) set.add(grpId); else set.delete(grpId);
                saveOpenSet(OPEN_GRP_KEY, set);
            }});

            const grpSummary = document.createElement('summary');
            grpSummary.className = 'counter';
            const grpCounts = computeGroupCounts(grp, completed);
            grpSummary.textContent = grp.name + '  (' + grpCounts.done + '/' + grpCounts.total + ')';
            grpDetails.appendChild(grpSummary);

            const ul = document.createElement('ul');
            ul.className = 'ach-list';

            for (const a of grp.achievements) {{
                const isDone = completed.has(a.id);
                const match = textIncludes(a.name, q) || textIncludes(a.desc, q);
                if (!match) continue;
                if (onlyTodo && isDone) continue;

                const li = document.createElement('li');
                li.className = 'ach-item';

                const cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.checked = isDone;
                cb.addEventListener('change', () => {{
                    const set = loadCompleted();
                    if (cb.checked) set.add(a.id); else set.delete(a.id);
                    saveCompleted(set);
                    render();
                }});

                const content = document.createElement('div');
                const title = document.createElement('div');
                title.className = 'ach-title';
                title.textContent = a.name || a.name_key || '';
                const desc = document.createElement('div');
                desc.className = 'ach-desc muted';
                desc.textContent = a.desc || a.desc_key || '';
                content.appendChild(title);
                content.appendChild(desc);

                li.appendChild(cb);
                li.appendChild(content);
                ul.appendChild(li);
            }}

            grpDetails.appendChild(ul);
            catNode.appendChild(grpDetails);
        }}

        catDetails.appendChild(catNode);
        liCat.appendChild(catDetails);
        rootUl.appendChild(liCat);
    }}
}}

document.getElementById('q').addEventListener('input', render);
document.getElementById('onlyTodo').addEventListener('change', render);
document.getElementById('exportBtn').addEventListener('click', exportProgress);
document.getElementById('importBtn').addEventListener('click', () => document.getElementById('importFile').click());
document.getElementById('importFile').addEventListener('change', async (e) => {{
    const file = e.target.files && e.target.files[0];
    // allow selecting the same file again next time
    e.target.value = '';
    if (!file) return;
    await importProgressFromFile(file);
}});
render();
</script>
</body>
</html>"""


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _resolve_path(root: Path, value: str) -> Path:
    p = Path(value)
    if p.is_absolute():
        return p
    if p.exists():
        return p.resolve()
    return (root / p).resolve()


def _validate_multitext_db(path: Path) -> None:
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
        names = {c[1] for c in cols}  # (cid, name, type, notnull, dflt_value, pk)
        if "Id" not in names or "Content" not in names:
            raise SystemExit(f"MultiText schema unexpected (needs Id, Content): {path}")
    finally:
        con.close()


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


def build_dataset(
    locale: str,
    achievements: Sequence[Achievement],
    groups: Sequence[Group],
    categories: Sequence[Category],
    texts: dict[str, str],
) -> dict[str, Any]:
    def t(key: str) -> str:
        if not key:
            return ""
        return texts.get(key, "")

    cat_items: list[dict[str, Any]] = []
    categories_sorted = sorted(categories, key=lambda c: c.id)

    groups_sorted = sorted(groups, key=lambda g: (g.category_id, g.sort, g.id))
    groups_by_category: dict[int, list[Group]] = {}
    for g in groups_sorted:
        groups_by_category.setdefault(g.category_id, []).append(g)

    achievements_sorted = sorted(achievements, key=lambda a: (a.group_id, a.id))
    achievements_by_group: dict[int, list[Achievement]] = {}
    for a in achievements_sorted:
        achievements_by_group.setdefault(a.group_id, []).append(a)

    allowed_category_names_in_order = ["索拉漫行", "长路留迹", "铿锵刃鸣", "诸音声轨"]
    categories_by_name: dict[str, Category] = {}
    for cat in categories_sorted:
        name = t(cat.name_key) or cat.name_key
        if name in allowed_category_names_in_order and name not in categories_by_name:
            categories_by_name[name] = cat

    for cat_name in allowed_category_names_in_order:
        cat = categories_by_name.get(cat_name)
        if not cat:
            continue

        cat_groups = groups_by_category.get(cat.id, [])
        group_items: list[dict[str, Any]] = []
        for g in cat_groups:
            ach_items: list[dict[str, Any]] = []
            for a in achievements_by_group.get(g.id, []):
                ach_items.append(
                    {
                        "id": a.id,
                        "group_id": a.group_id,
                        "level": a.level,
                        "name_key": a.name_key,
                        "desc_key": a.desc_key,
                        "name": t(a.name_key),
                        "desc": t(a.desc_key),
                    }
                )

            group_items.append(
                {
                    "id": g.id,
                    "category_id": g.category_id,
                    "sort": g.sort,
                    "name_key": g.name_key,
                    "name": t(g.name_key) or g.name_key,
                    "achievements": ach_items,
                }
            )

        cat_items.append(
            {
                "id": cat.id,
                "name_key": cat.name_key,
                "name": cat_name,
                "groups": group_items,
            }
        )

    return {"locale": locale, "categories": cat_items}


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
        _validate_multitext_db(p)

    achievements, groups, categories = load_from_config_db(config_db)
    wanted = collect_wanted_text_ids(achievements, groups, categories)
    texts = load_multitext_from_dbs(multitext_dbs, wanted)

    dataset = build_dataset(args.locale, achievements, groups, categories, texts)

    ensure_parent_dir(out_path)
    out_path.write_text(render_html(dataset), encoding="utf-8")
    logger.info("Wrote %s", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
