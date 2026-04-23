"""Render a single-file offline HTML achievement tracker page."""

from __future__ import annotations

import json
from typing import Any


def render_html(dataset: dict[str, Any]) -> str:
    dataset_json = json.dumps(dataset, ensure_ascii=False).replace("</", r"<\/")

    # Single-file offline HTML with enhanced UI.
    return f"""<!doctype html>
<html lang=\"zh-CN\" data-theme=\"auto\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>鸣潮 成就统计</title>
  <style>
    /* === Theme variables === */
    :root,
    [data-theme=\"light\"] {{
      --bg: #f5f5f7;
      --text: #1d1d1f;
      --text-muted: #6e6e73;
      --card-bg: #ffffff;
      --card-hover: #fafafa;
      --border: rgba(0,0,0,.08);
      --summary-bg: #eef0f4;
      --summary-hover: #e2e5eb;
      --accent: #3b82f6;
      --accent-light: #dbeafe;
      --progress-bg: #e5e7eb;
      --progress-fill: #3b82f6;
      --progress-full: #22c55e;
      --mark-bg: #fef08a;
      --mark-text: #1d1d1f;
      --btn-bg: #ffffff;
      --btn-hover: #f0f0f2;
      --btn-border: rgba(0,0,0,.15);
      --input-bg: #ffffff;
      --input-border: rgba(0,0,0,.12);
      --done-opacity: 0.45;
      color-scheme: light;
    }}
    [data-theme=\"dark\"] {{
      --bg: #1a1a2e;
      --text: #e4e4e7;
      --text-muted: #9ca3af;
      --card-bg: #242440;
      --card-hover: #2a2a4a;
      --border: rgba(255,255,255,.08);
      --summary-bg: #2d2d50;
      --summary-hover: #363660;
      --accent: #60a5fa;
      --accent-light: rgba(96,165,250,.15);
      --progress-bg: #374151;
      --progress-fill: #60a5fa;
      --progress-full: #4ade80;
      --mark-bg: #854d0e;
      --mark-text: #fef08a;
      --btn-bg: #2d2d50;
      --btn-hover: #363660;
      --btn-border: rgba(255,255,255,.12);
      --input-bg: #242440;
      --input-border: rgba(255,255,255,.12);
      --done-opacity: 0.35;
      color-scheme: dark;
    }}
    @media (prefers-color-scheme: dark) {{
      [data-theme=\"auto\"] {{
        --bg: #1a1a2e;
        --text: #e4e4e7;
        --text-muted: #9ca3af;
        --card-bg: #242440;
        --card-hover: #2a2a4a;
        --border: rgba(255,255,255,.08);
        --summary-bg: #2d2d50;
        --summary-hover: #363660;
        --accent: #60a5fa;
        --accent-light: rgba(96,165,250,.15);
        --progress-bg: #374151;
        --progress-fill: #60a5fa;
        --progress-full: #4ade80;
        --mark-bg: #854d0e;
        --mark-text: #fef08a;
        --btn-bg: #2d2d50;
        --btn-hover: #363660;
        --btn-border: rgba(255,255,255,.12);
        --input-bg: #242440;
        --input-border: rgba(255,255,255,.12);
        --done-opacity: 0.35;
        color-scheme: dark;
      }}
    }}

    /* === Base === */
    * {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial,
                   'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
      margin: 0; padding: 24px 16px;
      background: var(--bg); color: var(--text);
      line-height: 1.6;
      transition: background .2s, color .2s;
    }}
    .container {{ max-width: 820px; margin: 0 auto; }}

    /* === Header === */
    header {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 16px; }}
    header h2 {{ margin: 0; font-size: 22px; font-weight: 700; }}
    .overall-wrap {{ display: flex; align-items: center; gap: 12px; flex: 1; min-width: 200px; }}
    .overall-text {{ font-variant-numeric: tabular-nums; color: var(--text-muted); font-size: 14px; white-space: nowrap; }}

    /* === Progress bars === */
    .progress-bar {{
      flex: 1; height: 8px; min-width: 80px;
      background: var(--progress-bg); border-radius: 4px; overflow: hidden;
    }}
    .progress-bar-inner {{
      height: 100%; border-radius: 4px;
      background: var(--progress-fill);
      transition: width .3s ease, background .3s ease;
    }}
    .progress-bar-inner.full {{ background: var(--progress-full); }}
    .summary-progress {{
      display: inline-block; width: 80px; height: 6px;
      background: var(--progress-bg); border-radius: 3px; overflow: hidden;
      margin-left: 8px; vertical-align: middle;
    }}
    .summary-progress-inner {{
      height: 100%; border-radius: 3px;
      background: var(--progress-fill);
      transition: width .3s ease, background .3s ease;
    }}
    .summary-progress-inner.full {{ background: var(--progress-full); }}

    /* === Toolbar === */
    .toolbar {{
      display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
      padding: 12px 16px; margin-bottom: 16px;
      background: var(--card-bg); border: 1px solid var(--border);
      border-radius: 12px;
    }}
    input[type=\"search\"] {{
      flex: 1; min-width: 180px; padding: 8px 14px;
      border: 1px solid var(--input-border); border-radius: 8px;
      background: var(--input-bg); color: var(--text);
      font-size: 14px; outline: none;
      transition: border-color .15s;
    }}
    input[type=\"search\"]:focus {{ border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-light); }}
    input[type=\"search\"]::placeholder {{ color: var(--text-muted); }}

    .pill {{
      display: inline-flex; align-items: center; gap: 4px;
      padding: 6px 12px; border: 1px solid var(--btn-border); border-radius: 999px;
      background: var(--btn-bg); color: var(--text); font-size: 13px;
      cursor: pointer; user-select: none; transition: background .15s;
    }}
    .pill:hover {{ background: var(--btn-hover); }}
    .pill input[type=\"checkbox\"] {{ margin: 0; }}

    .btn {{
      padding: 6px 14px; border: 1px solid var(--btn-border); border-radius: 8px;
      background: var(--btn-bg); color: var(--text); font-size: 13px;
      cursor: pointer; transition: background .15s;
    }}
    .btn:hover {{ background: var(--btn-hover); }}
    .btn-icon {{
      padding: 6px 8px; border: 1px solid var(--btn-border); border-radius: 8px;
      background: var(--btn-bg); color: var(--text); font-size: 16px;
      cursor: pointer; transition: background .15s; line-height: 1;
    }}
    .btn-icon:hover {{ background: var(--btn-hover); }}

    .toolbar-hint {{ color: var(--text-muted); font-size: 12px; }}

    /* === Tree === */
    .tree {{ list-style: none; padding: 0; margin: 0; }}
    .tree > li {{ margin-bottom: 12px; }}

    details {{ margin: 0; }}
    summary {{
      cursor: pointer; user-select: none; list-style: none;
      padding: 10px 14px; border-radius: 10px;
      background: var(--summary-bg); font-weight: 600; font-size: 15px;
      display: flex; align-items: center; gap: 8px;
      transition: background .15s;
    }}
    summary:hover {{ background: var(--summary-hover); }}
    summary::-webkit-details-marker {{ display: none; }}
    summary::before {{
      content: '\\25B8'; display: inline-block; width: 1em; text-align: center;
      transition: transform .15s;
    }}
    details[open] > summary::before {{ transform: rotate(90deg); }}
    .summary-text {{ flex: 1; }}
    .summary-count {{ font-size: 13px; font-weight: 400; color: var(--text-muted); white-space: nowrap; }}

    .node {{ margin-left: 16px; margin-top: 8px; }}
    .node details {{ margin-bottom: 6px; }}
    .node summary {{ font-size: 14px; padding: 8px 12px; border-radius: 8px; }}

    /* === Achievement list === */
    .ach-list {{ list-style: none; padding: 6px 0 6px 12px; margin: 0; }}
    .ach-item {{
      display: grid; grid-template-columns: 24px 1fr; gap: 10px;
      padding: 10px 12px; margin: 4px 0;
      border-radius: 8px; background: var(--card-bg);
      border: 1px solid var(--border);
      transition: background .15s, opacity .2s;
    }}
    .ach-item:hover {{ background: var(--card-hover); }}
    .ach-item input[type=\"checkbox\"] {{
      width: 18px; height: 18px; margin-top: 2px;
      accent-color: var(--accent); cursor: pointer;
    }}
    .ach-title {{ font-weight: 600; font-size: 14px; }}
    .ach-desc {{ font-size: 13px; color: var(--text-muted); white-space: pre-wrap; margin-top: 2px; }}

    /* === Done state === */
    .ach-item.done {{ opacity: var(--done-opacity); }}
    .ach-item.done .ach-title {{ text-decoration: line-through; }}

    /* === Search highlight === */
    mark {{
      background: var(--mark-bg); color: var(--mark-text);
      border-radius: 2px; padding: 0 1px;
    }}

    /* === Mobile === */
    @media (max-width: 600px) {{
      body {{ padding: 12px 8px; }}
      .toolbar {{ padding: 10px 10px; gap: 6px; }}
      input[type=\"search\"] {{ min-width: 0; width: 100%; }}
      summary {{ padding: 8px 10px; font-size: 14px; }}
      .node {{ margin-left: 10px; }}
      .ach-item {{ padding: 8px 8px; gap: 8px; }}
      .ach-list {{ padding-left: 4px; }}
      .summary-progress {{ width: 60px; }}
    }}
  </style>
</head>
<body>
  <div class=\"container\">
  <header>
    <h2>成就统计</h2>
    <div class=\"overall-wrap\">
      <span id=\"overall\" class=\"overall-text\"></span>
      <div class=\"progress-bar\"><div id=\"overallBar\" class=\"progress-bar-inner\"></div></div>
    </div>
    <button id=\"themeBtn\" class=\"btn-icon\" type=\"button\" title=\"切换主题\"></button>
  </header>

  <div class=\"toolbar\">
    <input id=\"q\" type=\"search\" placeholder=\"搜索成就名称/描述...\" />
    <label class=\"pill\"><input id=\"onlyTodo\" type=\"checkbox\" /> 仅未完成</label>
    <button id=\"exportBtn\" class=\"btn\" type=\"button\">导出</button>
    <button id=\"importBtn\" class=\"btn\" type=\"button\">导入</button>
    <input id=\"importFile\" type=\"file\" accept=\"application/json\" style=\"display:none\" />
    <span class=\"toolbar-hint\">进度保存在浏览器本地</span>
  </div>

  <div id=\"app\"></div>
  </div>

<script>
const DATA = {dataset_json};
const STORAGE_KEY = 'ww_achievement_completed_v1';
const OPEN_CAT_KEY = 'ww_achievement_open_categories_v1';
const OPEN_GRP_KEY = 'ww_achievement_open_groups_v1';
const EXPORT_KEY = 'ww_achievement_export_v1';
const THEME_KEY = 'ww_achievement_theme_v1';

/* === Theme toggle === */
const THEME_ICONS = {{ auto: '\u2600\uFE0F/\U0001F319', light: '\u2600\uFE0F', dark: '\U0001F319' }};
const THEME_CYCLE = ['auto', 'light', 'dark'];

function getTheme() {{
  return localStorage.getItem(THEME_KEY) || 'auto';
}}

function applyTheme(theme) {{
  document.documentElement.setAttribute('data-theme', theme);
  document.getElementById('themeBtn').textContent = THEME_ICONS[theme] || THEME_ICONS.auto;
  localStorage.setItem(THEME_KEY, theme);
}}

function cycleTheme() {{
  const cur = getTheme();
  const idx = THEME_CYCLE.indexOf(cur);
  const next = THEME_CYCLE[(idx + 1) % THEME_CYCLE.length];
  applyTheme(next);
}}

applyTheme(getTheme());
document.getElementById('themeBtn').addEventListener('click', cycleTheme);

/* === Storage helpers === */
function loadCompleted() {{
  try {{
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw);
    return new Set(Array.isArray(arr) ? arr.map(Number).filter(n => !isNaN(n)) : []);
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

/* === Export / Import === */
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
        alert('\u5bfc\u5165\u5931\u8d25\uff1a\u4e0d\u662f\u6709\u6548\u7684 JSON \u6587\u4ef6');
        return;
    }}

    if (!payload || payload.schema !== EXPORT_KEY) {{
        alert('\u5bfc\u5165\u5931\u8d25\uff1a\u6587\u4ef6\u683c\u5f0f\u4e0d\u5339\u914d');
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

/* === Search & count helpers === */
function textIncludes(hay, needle) {{
  if (!needle) return true;
  return (hay || '').toLowerCase().includes(needle);
}}

function highlightText(text, needle) {{
  if (!needle || !text) return document.createTextNode(text || '');
  const lower = text.toLowerCase();
  const frag = document.createDocumentFragment();
  let start = 0;
  while (start < text.length) {{
    const idx = lower.indexOf(needle, start);
    if (idx === -1) {{
      frag.appendChild(document.createTextNode(text.slice(start)));
      break;
    }}
    if (idx > start) frag.appendChild(document.createTextNode(text.slice(start, idx)));
    const mark = document.createElement('mark');
    mark.textContent = text.slice(idx, idx + needle.length);
    frag.appendChild(mark);
    start = idx + needle.length;
  }}
  return frag;
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

function makeProgressSpan(done, total) {{
    const wrap = document.createElement('span');
    wrap.className = 'summary-progress';
    const inner = document.createElement('span');
    inner.className = 'summary-progress-inner';
    const pct = total > 0 ? (done / total * 100) : 0;
    inner.style.width = pct + '%';
    if (done === total && total > 0) inner.classList.add('full');
    wrap.appendChild(inner);
    return wrap;
}}

/* === Main render === */
function render() {{
  const completed = loadCompleted();
    const openCats = loadOpenSet(OPEN_CAT_KEY);
    const openGrps = loadOpenSet(OPEN_GRP_KEY);
  const q = (document.getElementById('q').value || '').trim().toLowerCase();
  const onlyTodo = document.getElementById('onlyTodo').checked;

  const counts = computeCounts(DATA.categories, completed);
    document.getElementById('overall').textContent = '\u5df2\u5b8c\u6210 ' + counts.done + ' / ' + counts.total;
    const overallBar = document.getElementById('overallBar');
    const overallPct = counts.total > 0 ? (counts.done / counts.total * 100) : 0;
    overallBar.style.width = overallPct + '%';
    overallBar.className = 'progress-bar-inner' + (counts.done === counts.total && counts.total > 0 ? ' full' : '');

  const app = document.getElementById('app');
  app.innerHTML = '';

    const rootUl = document.createElement('ul');
    rootUl.className = 'tree';
    app.appendChild(rootUl);

    for (const cat of DATA.categories) {{
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
        if ((q || onlyTodo) && !catHasAny) continue;

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
        const catCounts = computeNodeCounts(cat, completed);

        const catText = document.createElement('span');
        catText.className = 'summary-text';
        catText.textContent = cat.name;
        const catCount = document.createElement('span');
        catCount.className = 'summary-count';
        catCount.textContent = catCounts.done + '/' + catCounts.total;
        catSummary.appendChild(catText);
        catSummary.appendChild(catCount);
        catSummary.appendChild(makeProgressSpan(catCounts.done, catCounts.total));
        catDetails.appendChild(catSummary);

        const catNode = document.createElement('div');
        catNode.className = 'node';

        for (const grp of cat.groups) {{
            let grpHasAny = false;
            for (const a of grp.achievements) {{
                const isDone = completed.has(a.id);
                const match = textIncludes(a.name, q) || textIncludes(a.desc, q);
                if (match && !(onlyTodo && isDone)) {{
                    grpHasAny = true;
                    break;
                }}
            }}
            if ((q || onlyTodo) && !grpHasAny) continue;

            const grpDetails = document.createElement('details');
            const grpId = String(grp.id);
            grpDetails.open = q ? true : openGrps.has(grpId);
            grpDetails.addEventListener('toggle', () => {{
                const set = loadOpenSet(OPEN_GRP_KEY);
                if (grpDetails.open) set.add(grpId); else set.delete(grpId);
                saveOpenSet(OPEN_GRP_KEY, set);
            }});

            const grpSummary = document.createElement('summary');
            const grpCounts = computeGroupCounts(grp, completed);

            const grpText = document.createElement('span');
            grpText.className = 'summary-text';
            grpText.textContent = grp.name;
            const grpCount = document.createElement('span');
            grpCount.className = 'summary-count';
            grpCount.textContent = grpCounts.done + '/' + grpCounts.total;
            grpSummary.appendChild(grpText);
            grpSummary.appendChild(grpCount);
            grpSummary.appendChild(makeProgressSpan(grpCounts.done, grpCounts.total));
            grpDetails.appendChild(grpSummary);

            const ul = document.createElement('ul');
            ul.className = 'ach-list';

            for (const a of grp.achievements) {{
                const isDone = completed.has(a.id);
                const match = textIncludes(a.name, q) || textIncludes(a.desc, q);
                if (!match) continue;
                if (onlyTodo && isDone) continue;

                const li = document.createElement('li');
                li.className = 'ach-item' + (isDone ? ' done' : '');

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
                title.appendChild(highlightText(a.name || a.name_key || '', q));
                const desc = document.createElement('div');
                desc.className = 'ach-desc';
                desc.appendChild(highlightText(a.desc || a.desc_key || '', q));
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
    e.target.value = '';
    if (!file) return;
    await importProgressFromFile(file);
}});
render();
</script>
</body>
</html>"""
