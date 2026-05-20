#!/usr/bin/env python3
"""生成 N1/N2 语法复习用单页 HTML（索引 + 全文解析，浏览器内跳转）。"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

REVIEW_DIR = Path(__file__).resolve().parent
BASE = REVIEW_DIR.parent
if str(REVIEW_DIR) not in sys.path:
    sys.path.insert(0, str(REVIEW_DIR))

from gojuon_sort import gojuon_sort_key

OUT_HTML = REVIEW_DIR / "index.html"
IMPORTANCE_JSON = BASE / "jlpt_grammar_importance.json"
IMPORTANCE_FALLBACK = BASE / "n1_grammar_importance.json"
UI_CSS = REVIEW_DIR / "grammar_review_ui.css"
UI_JS = REVIEW_DIR / "grammar_review_ui.js"
SYNC_JS = REVIEW_DIR / "grammar_review_sync.js"
SYNC_CONFIG = REVIEW_DIR / "sync_config.js"
SYNC_BUILTIN = REVIEW_DIR / "sync_config.builtin.js"
SYNC_ENV = REVIEW_DIR / ".env"

SPAN_PAT = re.compile(r'^<span id="([a-z0-9\-]+)"></span>\s*$')
H4_PAT = re.compile(r'^<h4 id="([a-z0-9\-]+)">(.+)</h4>\s*$')
EX_BLOCK_START = re.compile(r"^\*\*【(\d+)】")
EX_BRACKET = re.compile(r"^\[(\d+)\]\s*$")
EX_BARE_NUM = re.compile(r"^([1-9]|10)\s*$")
EX_MIXED = re.compile(
    r"^(?:\*\*)?【?\d+[〜～\-]\d+】?|\[\d+[〜～\-]\d+\]|\d+[〜～\-]\d+"
)
QUESTION_LINE = re.compile(r"^\*\*\d+\*\*")
REF_LESSON = re.compile(r"→\s*(\d+)\s*[课課]\s*[-－]\s*(\d+)")


def skip_in_grammar_body(s: str) -> bool:
    if not s:
        return False
    if s.startswith("![") or s.startswith("## Page"):
        return True
    if s.startswith("### 校对文本"):
        return True
    if s.startswith("【復習】"):
        return True
    if re.match(r"^[IVX]+\s+", s):  # I ことがらを説明する☆
        return True
    return False


def is_exercise_marker(s: str, lines: list[str], i: int) -> bool:
    if EX_MIXED.match(s):
        return True
    if EX_BLOCK_START.match(s) or EX_BRACKET.match(s):
        return True
    if EX_BARE_NUM.match(s):
        for j in range(i + 1, min(i + 5, len(lines))):
            if QUESTION_LINE.match(lines[j].strip()):
                return True
    return False


def exercise_marker_num(s: str) -> int | None:
    m = EX_BLOCK_START.match(s) or EX_BRACKET.match(s) or EX_BARE_NUM.match(s)
    return int(m.group(1)) if m else None


EX_SECTION_HDR = re.compile(r"^\*\*【\d+】")
QUESTION_NUM = re.compile(r"^\*\*(\d+)\*\*\s*(.*)$")
INLINE_OPTS = re.compile(r"\s+([a-c])\s+")


def _inline_md(s: str) -> str:
    s = html.escape(s)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)


def split_inline_options(rest: str) -> tuple[str, list[tuple[str, str]]] | None:
    """N2 同行选项：题干 a … b … c …"""
    parts = INLINE_OPTS.split(rest.strip())
    if len(parts) < 7:
        return None
    stem = _inline_md(parts[0])
    opts = [(parts[i], _inline_md(parts[i + 1])) for i in range(1, len(parts), 2)]
    return stem, opts


def body_fragment_to_html(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    out: list[str] = []
    in_ul = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            if in_ul:
                out.append("</ul>")
                in_ul = False
            continue
        escaped = html.escape(line)
        if re.match(r"^\*\*(意味|例句|接续|注意)[：:]", line):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(f"<p class='field-label'>{_inline_md(line)}</p>")
            continue
        line = _inline_md(line)
        if line.strip().startswith("- "):
            if not in_ul:
                out.append('<ul class="options">')
                in_ul = True
            out.append(f"<li>{line[2:]}</li>")
        elif re.match(r"^[①②③④⑤⑥⑦⑧⑨⑩]", line):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(f'<p class="example">{line}</p>')
        else:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(f"<p>{line}</p>")
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


def exercise_fragment_to_html(text: str) -> str:
    lines = [ln.rstrip() for ln in text.splitlines()]
    items: list[str] = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if not s or EX_SECTION_HDR.match(s):
            i += 1
            continue
        qm = QUESTION_NUM.match(s)
        if qm:
            num, rest = qm.group(1), qm.group(2)
            split = split_inline_options(rest) if rest else None
            if split:
                stem, opts = split
                opt_html = "".join(
                    f'<li><span class="opt">{letter}</span> {text}</li>'
                    for letter, text in opts
                )
                items.append(
                    '<div class="exercise-item">'
                    f'<p class="exercise-q"><span class="q-num">{num}</span> {stem}</p>'
                    f'<ul class="options">{opt_html}</ul></div>'
                )
                i += 1
                continue
            stem = _inline_md(rest) if rest else ""
            opt_lines: list[str] = []
            i += 1
            while i < len(lines) and lines[i].strip().startswith("- "):
                raw = lines[i].strip()[2:]
                om = re.match(r"^([a-c])\s+(.*)$", raw, re.DOTALL)
                if om:
                    opt_lines.append(
                        f'<li><span class="opt">{om.group(1)}</span> {_inline_md(om.group(2))}</li>'
                    )
                else:
                    opt_lines.append(f"<li>{_inline_md(raw)}</li>")
                i += 1
            opts_block = f'<ul class="options">{"".join(opt_lines)}</ul>' if opt_lines else ""
            items.append(
                '<div class="exercise-item">'
                f'<p class="exercise-q"><span class="q-num">{num}</span> {stem}</p>'
                f"{opts_block}</div>"
            )
            continue
        i += 1
    return "\n".join(items)


def extract_bodies(md_path: Path) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    lines = md_path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        sm = SPAN_PAT.match(lines[i].strip())
        if not sm or i + 1 >= len(lines):
            i += 1
            continue
        h4m = H4_PAT.match(lines[i + 1].strip())
        if not h4m or h4m.group(1) != sm.group(1):
            i += 1
            continue
        aid = sm.group(1)
        title = html.escape(h4m.group(2).strip())
        body: list[str] = []
        i += 2
        while i < len(lines):
            s = lines[i].strip()
            if SPAN_PAT.match(s) or is_exercise_marker(s, lines, i):
                break
            if skip_in_grammar_body(s):
                i += 1
                continue
            body.append(lines[i])
            i += 1
        result[aid] = {"title": title, "html": body_fragment_to_html("\n".join(body))}
    return result


def extract_exercises(md_path: Path) -> dict[int, str]:
    """提取课后练习：【1】/[1]/裸数字 1 均对应第 N 语法；跳过【1〜6】等综合题。"""
    lines = md_path.read_text(encoding="utf-8").splitlines()
    by_num: dict[int, list[str]] = {}
    current: int | None = None
    in_mixed = False

    for i, line in enumerate(lines):
        s = line.strip()
        if EX_MIXED.match(s):
            current = None
            in_mixed = True
            continue
        num = exercise_marker_num(s)
        if num is not None and is_exercise_marker(s, lines, i):
            in_mixed = False
            current = num
            by_num.setdefault(current, [])
            continue
        if in_mixed or current is None:
            continue
        if SPAN_PAT.match(s) or H4_PAT.match(s):
            current = None
            continue
        if s.startswith("## Page") or s.startswith("![") or s.startswith("### 校对文本"):
            continue
        by_num[current].append(line)

    return {n: exercise_fragment_to_html("\n".join(chunk)) for n, chunk in by_num.items()}


def is_stub_body(body: dict[str, str]) -> bool:
    plain = re.sub(r"<[^>]+>", "", body.get("html", ""))
    return len(plain) < 350 or ("例句" not in plain and "①" not in plain)


def resolve_exercise_key(pt: dict, bodies: dict[str, dict[str, str]]) -> tuple[str, int]:
    """跨课参见（→24課-2）且正文为 stub 时，到引用课次取【N】练习。"""
    refs = REF_LESSON.findall(pt["pattern"])
    if refs and is_stub_body(bodies.get(pt["anchor_id"], {})):
        lesson, gnum = int(refs[0][0]), int(refs[0][1])
        level = pt["level"]
        ref_rel = f"{level}_实力养成篇_MD_校对版/{level}_实力养成篇_第{lesson:02d}课.md"
        return ref_rel, gnum
    return pt["md_rel"], pt["grammar_num"]


def load_points() -> list[dict]:
    data = json.loads((BASE / "grammar_index.json").read_text(encoding="utf-8"))
    return data["merged"]


def load_importance() -> dict[str, dict]:
    path = IMPORTANCE_JSON if IMPORTANCE_JSON.exists() else IMPORTANCE_FALLBACK
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("by_anchor", {})


LESSON_HEADING_PAT = re.compile(r"(\d+)\s*課\s*　?\s*(.+?)\s*$")


def extract_lesson_titles() -> dict[str, dict[int, str]]:
    """从校对版课文提取日语课名，如 1課 → 時間関係。"""
    titles: dict[str, dict[int, str]] = {"N1": {}, "N2": {}}
    for level in ("N1", "N2"):
        md_dir = BASE / f"{level}_实力养成篇_MD_校对版"
        if not md_dir.is_dir():
            continue
        for md in sorted(md_dir.glob(f"{level}_实力养成篇_第*.md")):
            if "問題" in md.name:
                continue
            lm = re.search(r"第(\d+)课", md.name)
            if not lm:
                continue
            lesson = int(lm.group(1))
            for line in md.read_text(encoding="utf-8").splitlines()[:45]:
                m = LESSON_HEADING_PAT.search(line.strip())
                if m and int(m.group(1)) == lesson:
                    titles[level][lesson] = m.group(2).strip()
                    break
    return titles


def lesson_label(level: str, lesson: int, titles: dict[str, dict[int, str]]) -> str:
    t = titles.get(level, {}).get(lesson, "")
    if t:
        return f"第{lesson}課 {t}"
    return f"第{lesson}課"


def lesson_filter_options_html(titles: dict[str, dict[int, str]]) -> str:
    parts = ['<option value="ALL">全部课次</option>']
    for level in ("N1", "N2"):
        opts: list[str] = []
        for n in sorted(titles.get(level, {})):
            label = html.escape(lesson_label(level, n, titles))
            opts.append(f'<option value="{level}:{n}">{label}</option>')
        if opts:
            parts.append(f'<optgroup label="{level}">{"".join(opts)}</optgroup>')
    return "\n".join(parts)


def stars_html(stars: int, info: dict | None, level: str) -> str:
    """1–5 星：55% 本地 N1 真题 + 45% 网上分档综合评定。"""
    qc = int((info or {}).get("question_hits") or (info or {}).get("question_count") or 0)
    ec = int((info or {}).get("exam_count") or 0)
    comb = (info or {}).get("combined_score")
    sl = (info or {}).get("stars_local")
    se = (info or {}).get("stars_external")
    book = f"书中{level}"
    if stars <= 0:
        tip = f"{book}：综合评定偏低（本地真题与外部资料均未突出）"
        return f'<span class="stars none" title="{html.escape(tip)}">☆☆☆☆☆</span>'
    filled = "★" * stars
    empty = "☆" * (5 - stars)
    comb_s = f"{comb:.2f}" if isinstance(comb, (int, float)) else "—"
    tip = (
        f"{book} · 综合★{stars}（分{comb_s}）= 本地真题★{sl} + 外部★{se}；"
        f"N1真题约{qc}题次/{ec}套"
    )
    return (
        f'<span class="stars s{stars}" title="{html.escape(tip)}">'
        f"{filled}<span class=\"dim\">{empty}</span></span>"
    )


def review_bar_html(aid: str) -> str:
    return (
        f'<div class="review-bar" data-aid="{aid}">'
        f'<button type="button" class="rv-btn" data-review="hard" title="不熟悉">不熟</button>'
        f'<button type="button" class="rv-btn" data-review="good" title="熟悉">熟悉</button>'
        "</div>"
    )


def cards_html(
    points: list[dict],
    bodies: dict[str, dict[str, str]],
    lesson_exercises: dict[tuple[str, int], str],
    importance: dict[str, dict],
    lesson_titles: dict[str, dict[int, str]],
) -> str:
    parts: list[str] = []
    for p in points:
        aid = p["anchor_id"]
        lvl = p["level"]
        lesson = p["lesson"]
        gnum = p["grammar_num"]
        badge = "n1" if lvl == "N1" else "n2"
        body = bodies.get(aid, {})
        title = body.get("title") or html.escape(f"{gnum} {p['pattern']}")
        content = body.get("html") or '<p class="muted">（正文未提取）</p>'
        ex_html = lesson_exercises.get((p["md_rel"], gnum), "")
        ex_block = ""
        if ex_html:
            ex_block = f'<section class="exercises"><h3>练习题（【{gnum}】）</h3>{ex_html}</section>'
        imp = importance.get(aid, {})
        stars = int(imp.get("stars") or 0)
        star_block = stars_html(stars, imp, lvl)
        pat_lower = html.escape(p["pattern"].lower())
        ll = html.escape(lesson_label(lvl, lesson, lesson_titles))
        pages = ", ".join(str(x) for x in p.get("book_pages") or []) or "—"
        pages_block = f'<p class="book-pages">书中页码：{html.escape(pages)}</p>'
        parts.append(
            f'<article class="grammar-card" id="{aid}" data-aid="{aid}" '
            f'data-level="{lvl}" data-lesson="{lesson}" data-pattern="{pat_lower}" '
            f'data-stars="{stars}">'
            f'<header><span class="badge {badge}">{lvl}</span>'
            f'<span class="lesson">{ll} · 第 {gnum} 项</span>'
            f'<span class="importance">{star_block}</span>'
            f"{review_bar_html(aid)}"
            f"<h2>{title}</h2>{pages_block}</header>"
            f'<div class="body">{content}</div>{ex_block}</article>'
        )
    return "\n".join(parts)


def _load_dotenv_simple(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _sync_config_js_content() -> str:
    for path in (SYNC_BUILTIN, SYNC_CONFIG):
        if path.exists():
            return path.read_text(encoding="utf-8")
    env = _load_dotenv_simple(SYNC_ENV)
    url = env.get("SUPABASE_URL", "").strip()
    key = env.get("SUPABASE_ANON_KEY", "").strip()
    if url and key:
        cfg = {
            "type": "supabase",
            "url": url.rstrip("/"),
            "anonKey": key,
            "table": env.get("GRAMMAR_SYNC_TABLE", "grammar_review_sync"),
        }
        return "window.GRAMMAR_SYNC_CONFIG = " + json.dumps(cfg, ensure_ascii=False) + ";\n"
    base = env.get("GRAMMAR_SYNC_BASE_URL", "").strip()
    if base:
        cfg = {"type": "http", "baseUrl": base.rstrip("/")}
        return "window.GRAMMAR_SYNC_CONFIG = " + json.dumps(cfg, ensure_ascii=False) + ";\n"
    return "window.GRAMMAR_SYNC_CONFIG = null;\n"


def build_html(
    points: list[dict],
    bodies: dict[str, dict[str, str]],
    lesson_exercises: dict[tuple[str, int], str],
    importance: dict[str, dict],
    lesson_titles: dict[str, dict[int, str]],
) -> str:
    points = sorted(points, key=lambda x: (gojuon_sort_key(x["pattern"]), x["level"]))
    n1 = sum(1 for p in points if p["level"] == "N1")
    n2 = sum(1 for p in points if p["level"] == "N2")
    lesson_titles_json = json.dumps(lesson_titles, ensure_ascii=False)
    lesson_options = lesson_filter_options_html(lesson_titles)

    rows: list[str] = []
    for seq, p in enumerate(points, start=1):
        aid = p["anchor_id"]
        pat = html.escape(p["pattern"])
        lvl = p["level"]
        lesson = p["lesson"]
        badge = "n1" if lvl == "N1" else "n2"
        imp = importance.get(aid, {})
        stars = int(imp.get("stars") or 0)
        star_cell = stars_html(stars, imp, lvl)
        rows.append(
            f'<tr data-level="{lvl}" data-lesson="{lesson}" data-pattern="{pat.lower()}" '
            f'data-label="{pat}" data-aid="{aid}" data-stars="{stars}" data-review="new">'
            f'<td class="idx-num">{seq}</td>'
            f'<td class="idx-lvl"><span class="badge {badge}">{lvl}</span></td>'
            f'<td class="pass-col"></td>'
            f'<td class="stars-col">{star_cell}</td>'
            f'<td class="idx-pat">{pat}</td>'
            f'<td class="idx-lesson"><a class="go" href="#" data-aid="{aid}">{lesson}</a></td></tr>'
        )

    cards = cards_html(points, bodies, lesson_exercises, importance, lesson_titles)
    ui_css = UI_CSS.read_text(encoding="utf-8") if UI_CSS.exists() else ""
    ui_js = UI_JS.read_text(encoding="utf-8") if UI_JS.exists() else ""
    sync_js = SYNC_JS.read_text(encoding="utf-8") if SYNC_JS.exists() else ""
    sync_config_js = _sync_config_js_content()

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JLPT新完全掌握语法 N1/N2 · 复习</title>
<style>
:root {{
  --bg: #f6f5f2; --card: #fff; --text: #1a1a1a; --muted: #666;
  --border: #e2ddd4; --n1: #2563eb; --n2: #059669; --accent: #b45309;
}}
* {{ box-sizing: border-box; }}
html, body {{
  height: 100%;
  margin: 0;
  overflow: hidden;
}}
body {{
  display: flex;
  flex-direction: column;
  font-family: "Hiragino Sans", "Yu Gothic UI", "PingFang SC", sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.65;
}}
.toolbar {{
  position: relative;
  flex-shrink: 0;
  z-index: 100;
  background: rgba(246,245,242,.95); backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
  padding: .75rem 1rem;
}}
body.toolbar-collapsed .toolbar {{
  padding: 0;
  border-bottom: none;
  background: transparent;
  backdrop-filter: none;
  min-height: 0;
}}
body.toolbar-collapsed .toolbar-body {{ display: none !important; }}
body.toolbar-collapsed .toolbar-toggle {{
  position: fixed;
  top: max(.35rem, env(safe-area-inset-top, 0px));
  right: max(.35rem, env(safe-area-inset-right, 0px));
  z-index: 120;
  padding: .4rem .65rem;
  font-size: .8rem;
  background: var(--card);
  box-shadow: 0 2px 10px rgba(0,0,0,.12);
  border-radius: 8px;
}}
body.toolbar-expanded .toolbar {{
  padding: .5rem .75rem .45rem;
}}
body.toolbar-expanded .toolbar-body {{ display: block; }}
.toolbar-toggle {{
  flex-shrink: 0;
  padding: .28rem .55rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--card);
  color: var(--muted);
  cursor: pointer;
  font-size: .78rem;
  line-height: 1.2;
}}
body.toolbar-expanded .toolbar-toggle {{
  position: absolute;
  top: .45rem;
  right: max(.6rem, env(safe-area-inset-right, 0px));
  z-index: 2;
}}
body.toolbar-expanded .toolbar-body {{ padding-right: 3rem; }}
.toolbar-toggle:hover {{ color: var(--text); border-color: #c5c9d2; }}
.toolbar-row {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: .4rem .55rem;
}}
.toolbar-row + .toolbar-row {{
  margin-top: .4rem;
  padding-top: .4rem;
  border-top: 1px solid var(--border);
}}
.toolbar-row-head {{
  justify-content: space-between;
  border-top: none !important;
  margin-top: 0 !important;
  padding-top: 0 !important;
}}
.toolbar-title {{
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  display: flex;
  align-items: baseline;
  gap: .5rem;
  flex-wrap: wrap;
  min-width: 0;
}}
.toolbar-title .title-sub {{
  font-size: .75rem;
  font-weight: 500;
  color: var(--muted);
}}
.toolbar-group {{
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: .35rem;
}}
.toolbar-group-label {{
  font-size: .72rem;
  color: var(--muted);
  white-space: nowrap;
  margin-right: .1rem;
}}
.toolbar-group-search {{
  flex: 1 1 12rem;
  min-width: 10rem;
  max-width: 100%;
}}
.toolbar-group-search #q {{
  width: 100%;
  padding: .38rem .55rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: .88rem;
}}
.btn-segment {{
  display: inline-flex;
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  background: var(--card);
}}
.btn-segment .filter-btn {{
  border: none;
  border-radius: 0;
  border-right: 1px solid var(--border);
  margin: 0;
  padding: .32rem .55rem;
  font-size: .8rem;
}}
.btn-segment .filter-btn:last-child {{ border-right: none; }}
.toolbar-group-review {{
  margin-left: auto;
}}
.btn-segment .review-filter-btn[data-review-filter="hard"].active {{
  background: #dc2626;
  color: #fff;
  border-color: #b91c1c;
}}
.btn-segment .review-filter-btn[data-review-filter="good"].active {{
  background: #16a34a;
  color: #fff;
  border-color: #15803d;
}}
.btn-segment .review-filter-btn[data-review-filter="new"].active {{
  background: #78716c;
  color: #fff;
  border-color: #57534e;
}}
.filter-btn {{
  padding: .32rem .55rem; border: 1px solid var(--border); border-radius: 6px;
  background: var(--card); cursor: pointer; font-size: .8rem;
}}
.filter-btn.active {{ background: var(--text); color: #fff; border-color: var(--text); }}
#btn-review {{
  background: var(--accent); color: #fff; border-color: var(--accent);
}}
.lesson-select {{
  padding: .32rem .45rem; border: 1px solid var(--border); border-radius: 6px;
  background: var(--card); font-size: .8rem; max-width: min(280px, 100%);
}}
#lesson-heading {{
  display: flex; align-items: center; gap: .5rem; flex-wrap: wrap;
  margin: 0 0 1rem; padding: .65rem 1rem;
  background: linear-gradient(135deg, #faf9f7 0%, #f0ede6 100%);
  border: 1px solid var(--border); border-radius: 10px;
  font-size: 1.05rem; font-weight: 700; line-height: 1.4;
}}
#lesson-heading[hidden] {{ display: none !important; }}
.layout {{
  flex: 1;
  min-height: 0;
  display: grid; grid-template-columns: minmax(280px, 38%) 1fr;
  gap: 0; max-width: 1400px; width: 100%; margin: 0 auto;
}}
/* 平板 / 手机：全屏 flex，布局随横竖屏切换 */
@media (max-width: 1100px), (hover: none) and (pointer: coarse) {{
  html, body {{ height: 100%; overflow: hidden; }}
  body {{ display: flex; flex-direction: column; }}
  .toolbar-row-head {{ flex-direction: column; align-items: stretch; }}
  .sync-toolbar {{ align-items: flex-start; max-width: 100%; }}
  .sync-toolbar-row {{ justify-content: flex-start; flex-wrap: wrap; }}
  .sync-status {{ text-align: left; max-width: 100%; }}
  .layout {{ flex: 1; min-height: 0; max-width: none; }}
  .lesson-select {{ max-width: 100%; }}
}}
/* 平板竖屏：筛选区纵向铺开 */
@media (max-width: 1100px) and (orientation: portrait),
       (hover: none) and (pointer: coarse) and (orientation: portrait) {{
  .toolbar-group-search {{ flex: 1 1 100%; min-width: 0; }}
  .toolbar-row-main,
  .toolbar-row-actions {{ align-items: stretch; }}
  .toolbar-group-review {{ margin-left: 0; width: 100%; justify-content: flex-start; }}
}}
/* 竖屏：索引在上、正文在下 */
@media (max-width: 1100px) and (orientation: portrait),
       (hover: none) and (pointer: coarse) and (orientation: portrait) {{
  .layout {{
    display: grid;
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }}
  .index-panel {{
    max-height: min(42vh, 380px);
    height: auto;
    border-right: none;
    border-bottom: 1px solid var(--border);
  }}
  .index-scroll {{ max-height: min(36vh, 320px); }}
  .content-panel {{
    min-height: 0;
    overflow-y: auto;
    padding: .75rem .85rem 2rem;
  }}
}}
/* 横屏：索引在左、正文在右 */
@media (max-width: 1100px) and (orientation: landscape),
       (hover: none) and (pointer: coarse) and (orientation: landscape) {{
  .layout {{
    display: grid;
    grid-template-columns: minmax(200px, 36%) 1fr;
    grid-template-rows: 1fr;
  }}
  .index-panel {{
    max-height: none;
    height: 100%;
    border-right: 1px solid var(--border);
    border-bottom: none;
  }}
  .index-scroll {{
    flex: 1;
    min-height: 0;
    max-height: none;
  }}
  .content-panel {{
    min-height: 0;
    height: 100%;
    overflow-y: auto;
    padding: .75rem 1rem 2rem;
  }}
}}
/* 平板横屏：页头紧凑两行（筛选 + 操作） */
@media (hover: none) and (pointer: coarse) and (orientation: landscape),
       (max-height: 560px) and (orientation: landscape) {{
  body.toolbar-expanded .toolbar {{
    padding: .3rem .5rem .32rem;
  }}
  body.toolbar-expanded .toolbar-body {{
    padding-right: 2.7rem;
  }}
  body.toolbar-expanded .toolbar-row {{
    margin-top: 0 !important;
    padding-top: 0 !important;
    border-top: none !important;
  }}
  body.toolbar-expanded .toolbar-row + .toolbar-row {{
    margin-top: .28rem;
    padding-top: .28rem;
    border-top: 1px solid var(--border);
  }}
  .toolbar-row-head {{
    flex-direction: row !important;
    align-items: center !important;
    gap: .4rem .5rem;
    border: none !important;
    margin: 0 !important;
    padding: 0 !important;
  }}
  .toolbar-title .title-sub {{ display: none; }}
  .toolbar-title {{ font-size: .88rem; }}
  .sync-toolbar {{
    flex-direction: row;
    align-items: center;
    gap: .3rem;
    max-width: none;
    margin-left: auto;
  }}
  .sync-toolbar-row {{ flex-wrap: nowrap; }}
  .sync-input {{ width: 6.2rem; font-size: .76rem; padding: .24rem .4rem; }}
  #sync-now {{ font-size: .76rem; padding: .24rem .45rem; }}
  .sync-status {{
    max-width: 8.5rem;
    font-size: .62rem;
    text-align: right;
    display: block;
  }}
  .toolbar-row-main {{
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto auto;
    grid-template-rows: auto auto;
    gap: .25rem .35rem;
    align-items: center;
  }}
  .toolbar-group-search {{ grid-column: 1 / -1; min-width: 0; }}
  .toolbar-group-level {{ grid-column: 1; }}
  .toolbar-group-familiarity {{ grid-column: 2 / -1; justify-self: end; }}
  .toolbar-group-label {{ display: none; }}
  .toolbar-group-level .lesson-select {{
    max-width: 7.5rem;
    font-size: .74rem;
    padding: .22rem .3rem;
  }}
  .toolbar-row-actions {{
    display: flex;
    flex-wrap: nowrap;
    align-items: center;
    gap: .28rem;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
  }}
  .toolbar-row-actions::-webkit-scrollbar {{ display: none; }}
  .toolbar-group-pass {{ flex-shrink: 0; }}
  .pass-progress {{
    flex-shrink: 0;
    white-space: nowrap;
    font-size: .68rem;
    gap: .35rem;
  }}
  .pass-incomplete-toggle,
  .pass-clear-btn {{ flex-shrink: 0; font-size: .72rem; white-space: nowrap; }}
  .toolbar-group-review {{
    margin-left: auto;
    flex-shrink: 0;
  }}
  .review-stats {{ font-size: .68rem; }}
  .btn-segment .filter-btn,
  .btn-segment .pass-btn {{
    padding: .24rem .4rem;
    font-size: .73rem;
  }}
  #btn-review {{ padding: .24rem .5rem; }}
}}
.index-panel {{
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border); background: var(--card);
  min-height: 0;
  height: 100%;
  overflow: hidden;
}}
.index-panel h2 {{
  flex-shrink: 0;
  margin: 0; padding: .55rem 1rem; font-size: .88rem;
  border-bottom: 1px solid var(--border); background: #faf9f7;
}}
.index-panel .index-hint {{
  flex-shrink: 0;
  margin: 0; padding: 0.2rem 1rem 0.45rem;
  font-size: 0.72rem; color: var(--muted);
  border-bottom: 1px solid var(--border); background: #faf9f7;
}}
.index-scroll {{
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  scrollbar-gutter: stable;
  overflow-anchor: none;
  outline: none;
}}
#idx tbody {{ overflow-anchor: none; }}
.index-scroll:focus-visible {{
  box-shadow: inset 0 0 0 2px rgba(180, 83, 9, 0.35);
}}
.index-scroll::-webkit-scrollbar {{ width: 11px; }}
.index-scroll::-webkit-scrollbar-track {{ background: #f0ede6; }}
.index-scroll::-webkit-scrollbar-thumb {{
  background: #b8b0a4; border-radius: 6px; border: 2px solid #f0ede6;
}}
.index-scroll::-webkit-scrollbar-thumb:hover {{ background: #9a9288; }}
#idx {{ width: 100%; border-collapse: collapse; font-size: .82rem; }}
#idx th, #idx td {{
  padding: .48rem .55rem; border-bottom: 1px solid var(--border);
  text-align: left; vertical-align: middle;
}}
#idx th {{
  background: #faf9f7; position: sticky; top: 0; z-index: 1;
  box-shadow: 0 1px 0 var(--border);
}}
#idx tbody tr {{ scroll-margin-block: 6px; }}
.idx-num {{
  width: 2rem; text-align: right; white-space: nowrap;
  color: var(--muted); font-variant-numeric: tabular-nums; font-size: .78rem;
}}
.idx-lvl, .idx-lesson {{ white-space: nowrap; text-align: center; }}
.idx-lvl {{ width: 2.5rem; }}
.idx-lesson {{ width: 2.2rem; padding-left: .2rem; padding-right: .2rem; }}
.idx-lesson a.go {{ font-weight: 600; }}
.idx-pat {{ word-break: break-all; }}
.stars-col {{ white-space: nowrap; }}
.stars {{ font-size: .72rem; letter-spacing: -.02em; color: #c47a0a; }}
.stars .dim {{ color: #d4cfc4; }}
.stars.na, .stars.none {{ color: var(--muted); font-size: .7rem; }}
.grammar-card header .importance {{
  float: right; margin-left: .5rem; font-size: .85rem;
}}
.grammar-card header::after {{
  content: ""; display: table; clear: both;
}}
tr {{ cursor: pointer; }}
tr:hover {{ background: #f0ede6; }}
tr.active {{ background: #e8f0fe; }}
tr.hidden {{ display: none; }}
.badge {{
  display: inline-block; padding: .1rem .4rem; border-radius: 4px;
  font-size: .72rem; font-weight: 600; color: #fff;
}}
.badge.n1 {{ background: var(--n1); }}
.badge.n2 {{ background: var(--n2); }}
a.go {{ color: var(--accent); text-decoration: none; font-weight: 500; }}
a.go:hover {{ text-decoration: underline; }}
.content-panel {{
  min-height: 0;
  height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  scroll-behavior: auto;
  padding: 1rem 1.25rem 3rem;
}}
.grammar-card {{
  background: var(--card); border: 1px solid var(--border); border-radius: 10px;
  padding: 1rem 1.15rem; margin-bottom: 1.25rem; scroll-margin-top: 1rem;
}}
.grammar-card.is-current {{
  box-shadow: 0 0 0 2px rgba(180, 83, 9, 0.4);
  border-color: #d4a574;
}}
.grammar-card:target {{ box-shadow: none; }}
.grammar-card header {{
  margin-bottom: .75rem; padding-bottom: .5rem; border-bottom: 1px dashed var(--border);
}}
.grammar-card h2 {{ margin: .35rem 0 0; font-size: 1.15rem; }}
.grammar-card .lesson {{ font-size: .78rem; color: var(--muted); margin-left: .5rem; }}
.grammar-card .book-pages {{
  margin: .35rem 0 0; font-size: .78rem; color: var(--muted); clear: both;
}}
.grammar-card .body p {{ margin: .35rem 0; line-height: 1.55; }}
.grammar-card .body .field-label {{
  margin: .65rem 0 .25rem; font-weight: 600; color: var(--text);
}}
.grammar-card .example {{ margin: .25rem 0 .25rem .5rem; line-height: 1.55; }}
.grammar-card .exercises {{
  margin-top: 1.1rem; padding-top: .85rem; border-top: 1px solid var(--border);
}}
.grammar-card .exercises h3 {{
  margin: 0 0 .75rem; font-size: .9rem; color: var(--accent);
}}
.grammar-card .exercise-item {{
  margin-bottom: 1rem; padding-bottom: .85rem;
  border-bottom: 1px dashed #ebe6dd;
}}
.grammar-card .exercise-item:last-child {{
  margin-bottom: 0; padding-bottom: 0; border-bottom: none;
}}
.grammar-card .exercise-q {{
  margin: 0 0 .45rem; line-height: 1.6; font-size: .95rem;
}}
.grammar-card .q-num {{
  display: inline-block; min-width: 1.4rem; margin-right: .15rem;
  font-weight: 700; color: var(--accent);
}}
.grammar-card .options {{
  margin: 0; padding: 0 0 0 1.1rem; list-style: none;
}}
.grammar-card .options li {{
  margin: .35rem 0; padding: .2rem 0 .2rem .15rem; line-height: 1.55;
}}
.grammar-card .opt {{
  display: inline-block; min-width: 1.1rem; margin-right: .35rem;
  font-weight: 600; color: var(--muted);
}}
.muted {{ color: var(--muted); }}
#top-btn {{
  position: fixed; right: 1rem; bottom: 1rem; padding: .5rem .85rem;
  border: none; border-radius: 8px; background: var(--text); color: #fff;
  cursor: pointer; font-size: .85rem;
}}
{ui_css}
</style>
</head>
<body class="toolbar-collapsed">
<header class="toolbar">
  <button type="button" class="toolbar-toggle" id="btn-toolbar-toggle" title="展开筛选与设置" aria-expanded="false">展开</button>
  <div class="toolbar-body" id="toolbar-body">
    <div class="toolbar-row toolbar-row-head">
      <h1 class="toolbar-title" title="重要度★＝真题55%+网评45%（悬停★可见）">
        JLPT新完全掌握语法 N1/N2
        <span class="title-sub">{len(points)} 条 · N1 {n1} · N2 {n2}</span>
      </h1>
      <div class="sync-toolbar" id="sync-toolbar" hidden>
        <div class="sync-toolbar-row">
          <input type="email" id="sync-email" class="sync-input" placeholder="同步邮箱" autocomplete="email" title="电脑与平板填同一邮箱">
          <button type="button" class="filter-btn" id="sync-now">同步</button>
        </div>
        <span id="sync-status" class="sync-status" title=""></span>
      </div>
    </div>
    <div class="toolbar-row toolbar-row-main">
      <div class="toolbar-group toolbar-group-search">
        <input type="search" id="q" placeholder="搜索语法…" autocomplete="off">
      </div>
      <div class="toolbar-group toolbar-group-level">
        <span class="toolbar-group-label">级别</span>
        <div class="btn-segment" role="group" aria-label="级别筛选">
          <button type="button" class="filter-btn active" data-level="ALL">全部</button>
          <button type="button" class="filter-btn" data-level="N1">N1</button>
          <button type="button" class="filter-btn" data-level="N2">N2</button>
        </div>
        <select id="lesson-filter" class="lesson-select" title="按课次筛选">
{lesson_options}
        </select>
      </div>
      <div class="toolbar-group toolbar-group-familiarity">
        <span class="toolbar-group-label">熟悉度</span>
        <div class="btn-segment" role="group" aria-label="按当前遍熟悉度筛选列表">
          <button type="button" class="filter-btn review-filter-btn active" data-review-filter="ALL">全部</button>
          <button type="button" class="filter-btn review-filter-btn" data-review-filter="new">未评</button>
          <button type="button" class="filter-btn review-filter-btn" data-review-filter="hard">不熟</button>
          <button type="button" class="filter-btn review-filter-btn" data-review-filter="good">熟悉</button>
        </div>
      </div>
    </div>
    <div class="toolbar-row toolbar-row-actions pass-toolbar">
      <div class="toolbar-group toolbar-group-pass">
        <span class="toolbar-group-label">遍次</span>
        <div class="btn-segment" role="group" aria-label="当前复习遍次">
          <button type="button" class="pass-btn active" data-pass="1">第1遍</button>
          <button type="button" class="pass-btn" data-pass="2">第2遍</button>
          <button type="button" class="pass-btn" data-pass="3">第3遍</button>
        </div>
      </div>
      <span id="pass-progress" class="pass-progress"></span>
      <label class="pass-incomplete-toggle" title="卡片复习只出本遍未完成"><input type="checkbox" id="pass-incomplete" checked> 仅未完成</label>
      <button type="button" class="pass-clear-btn" data-clear-pass title="清除当前遍全部记录">清除本遍</button>
      <div class="toolbar-group toolbar-group-review">
        <span id="review-stats" class="review-stats"></span>
        <label class="review-shuffle-toggle" title="卡片复习打乱顺序"><input type="checkbox" id="review-shuffle" checked> 乱序</label>
        <button type="button" class="filter-btn" id="btn-review">卡片复习</button>
        <button type="button" class="filter-btn" id="btn-review-weak">待复习</button>
      </div>
    </div>
    </div>
  </div>
</header>
<main class="layout">
  <aside class="index-panel" id="index-panel">
    <h2 id="index-title">五十音索引</h2>
    <p class="index-hint">滚轮 / 触控板在此翻阅 · ↑↓ 或 J/K 移动 · Enter 打开</p>
    <div class="index-scroll" id="index-scroll" tabindex="0" aria-label="语法索引列表">
      <table id="idx">
        <thead><tr><th>序</th><th>级别</th><th title="三个方格=第1/2/3遍：白框未评、绿✓熟悉、红×不熟；橙框=当前遍">遍</th><th>重要度</th><th>语法</th><th>课</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    </div>
  </aside>
  <section class="content-panel" id="grammar-list">
    <div id="lesson-heading" hidden></div>
{cards}
  </section>
</main>
<button type="button" id="top-btn" title="回到顶部">↑ 顶部</button>
<div id="review-overlay" role="dialog" aria-modal="true">
  <div class="review-panel">
    <div class="review-top">
      <span>卡片复习</span>
      <span id="rv-progress" class="review-progress"></span>
      <div class="review-top-actions">
        <button type="button" id="rv-undo" disabled title="回到上一张（Z）">撤销</button>
        <button type="button" id="rv-flip">显示解析</button>
        <button type="button" id="rv-clear-card" class="rv-clear-card" title="清除本条在第N遍的记录">清除本条</button>
        <button type="button" id="review-close" title="关闭 (Esc)">×</button>
      </div>
    </div>
    <div class="flip-card">
      <div class="flip-inner" id="flip-inner">
        <div class="flip-face flip-front">
          <p class="review-meta" id="rv-front-meta"></p>
          <h3 class="review-front-pattern" id="rv-front-pattern"></h3>
          <p class="review-hint">点击显示解析 · 空格 / Enter · 1 不熟 · 2 熟悉</p>
        </div>
        <div class="flip-face flip-back">
          <div id="rv-back-body" class="body"></div>
        </div>
      </div>
    </div>
    <div class="review-actions">
      <button type="button" id="rv-hard">不熟悉</button>
      <button type="button" id="rv-good">熟悉</button>
    </div>
  </div>
</div>
<script>
const LESSON_TITLES = {lesson_titles_json};
</script>
<script>
(function() {{
  const q = document.getElementById('q');
  const rows = [...document.querySelectorAll('#idx tbody tr')];
  const lessonFilterEl = document.getElementById('lesson-filter');
  const lessonHeading = document.getElementById('lesson-heading');
  const indexTitle = document.getElementById('index-title');
  const contentPanel = document.getElementById('grammar-list');
  const indexScroll = document.getElementById('index-scroll');
  const indexPanel = document.getElementById('index-panel');
  let listFocusIndex = -1;
  let levelFilter = 'ALL';
  let lessonFilter = 'ALL';

  function lessonDisplay(level, num) {{
    const t = (LESSON_TITLES[level] || {{}})[String(num)] || (LESSON_TITLES[level] || {{}})[num] || '';
    return t ? `第${{num}}課 ${{t}}` : `第${{num}}課`;
  }}

  function updateLessonHeading() {{
    if (!lessonHeading) return;
    if (lessonFilter === 'ALL') {{
      lessonHeading.hidden = true;
      if (indexTitle) indexTitle.textContent = '五十音索引';
      return;
    }}
    const [level, num] = lessonFilter.split(':');
    const label = lessonDisplay(level, num);
    const badge = level === 'N1' ? 'n1' : 'n2';
    lessonHeading.innerHTML = `<span class="badge ${{badge}}">${{level}}</span><span>${{label}}</span>`;
    lessonHeading.hidden = false;
    if (indexTitle) indexTitle.textContent = `${{level}} · ${{label}}`;
  }}

  function syncLessonWithLevel() {{
    if (lessonFilter === 'ALL' || levelFilter === 'ALL') return;
    const lv = lessonFilter.split(':')[0];
    if (lv !== levelFilter) {{
      lessonFilter = 'ALL';
      if (lessonFilterEl) lessonFilterEl.value = 'ALL';
      updateLessonHeading();
    }}
  }}

  function applyFilter() {{
    const term = (q.value || '').trim().toLowerCase();
    rows.forEach(tr => {{
      const lv = tr.dataset.level;
      const les = tr.dataset.lesson || '';
      const pat = tr.dataset.pattern || '';
      const aid = tr.dataset.aid || '';
      const card = document.getElementById(aid);
      const okLevel = levelFilter === 'ALL' || lv === levelFilter;
      const okLesson = lessonFilter === 'ALL' || `${{lv}}:${{les}}` === lessonFilter;
      const okSearch = !term || pat.includes(term) || aid.includes(term);
      const okReview = typeof window.__grammarReviewMatchFilter === 'function'
        ? window.__grammarReviewMatchFilter(aid) : true;
      const show = okLevel && okLesson && okSearch && okReview;
      tr.classList.toggle('hidden', !show);
      if (card) card.style.display = show ? '' : 'none';
    }});
  }}

  q.addEventListener('input', applyFilter);
  if (lessonFilterEl) {{
    lessonFilterEl.addEventListener('change', () => {{
      lessonFilter = lessonFilterEl.value;
      const lv = lessonFilter.split(':')[0];
      if (lessonFilter !== 'ALL' && levelFilter !== 'ALL' && lv !== levelFilter) {{
        document.querySelectorAll('.filter-btn[data-level]').forEach(b => {{
          b.classList.toggle('active', b.dataset.level === lv);
        }});
        levelFilter = lv;
      }} else if (lessonFilter !== 'ALL' && levelFilter === 'ALL') {{
        document.querySelectorAll('.filter-btn[data-level]').forEach(b => {{
          b.classList.toggle('active', b.dataset.level === lv);
        }});
        levelFilter = lv;
      }}
      updateLessonHeading();
      applyFilter();
    }});
  }}
  document.querySelectorAll('.filter-btn[data-level]').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('.filter-btn[data-level]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      levelFilter = btn.dataset.level;
      syncLessonWithLevel();
      updateLessonHeading();
      applyFilter();
    }});
  }});
  updateLessonHeading();

  function visibleRows() {{
    return rows.filter(r => !r.classList.contains('hidden'));
  }}

  function scrollInPanel(panel, el, gap) {{
    if (!panel || !el) return;
    const panelRect = panel.getBoundingClientRect();
    const elRect = el.getBoundingClientRect();
    const top = panel.scrollTop + (elRect.top - panelRect.top) - (gap || 0);
    panel.scrollTop = Math.max(0, top);
  }}

  function isVisibleInPanel(panel, el, pad) {{
    if (!panel || !el) return true;
    const p = pad || 8;
    const pr = panel.getBoundingClientRect();
    const er = el.getBoundingClientRect();
    return er.top >= pr.top + p && er.bottom <= pr.bottom - p;
  }}

  function syncListFocusIndex(tr) {{
    const vis = visibleRows();
    listFocusIndex = tr ? vis.indexOf(tr) : -1;
  }}

  function focusListRow(index, opts) {{
    const vis = visibleRows();
    if (!vis.length) return null;
    const i = Math.max(0, Math.min(index, vis.length - 1));
    const tr = vis[i];
    listFocusIndex = i;
    rows.forEach(r => r.classList.toggle('active', r === tr));
    if (!isVisibleInPanel(indexScroll, tr)) {{
      scrollInPanel(indexScroll, tr, 8);
    }}
    return tr;
  }}

  function lockIndexScrollTop() {{
    return indexScroll ? indexScroll.scrollTop : 0;
  }}

  function restoreIndexScrollTop(top) {{
    if (!indexScroll) return;
    indexScroll.scrollTop = top;
    requestAnimationFrame(() => {{ indexScroll.scrollTop = top; }});
  }}

  function goTo(id, opts) {{
    const o = opts || {{}};
    const el = document.getElementById(id);
    if (!el) return;
    const indexTop = lockIndexScrollTop();
    const activeRow = rows.find(r => r.dataset.aid === id);
    rows.forEach(r => r.classList.toggle('active', r.dataset.aid === id));
    document.querySelectorAll('.grammar-card').forEach(c => {{
      c.classList.toggle('is-current', c.id === id);
    }});
    syncListFocusIndex(activeRow || null);
    if (contentPanel) {{
      if (!isVisibleInPanel(contentPanel, el, 24)) {{
        scrollInPanel(contentPanel, el, 20);
      }}
    }} else {{
      el.scrollIntoView({{ block: 'start', behavior: 'auto' }});
    }}
    if (typeof window.__grammarReviewSavePlace === 'function') {{
      window.__grammarReviewSavePlace(id);
    }}
    if (o.resume) {{
      if (activeRow && indexScroll) scrollInPanel(indexScroll, activeRow, 8);
      if (contentPanel) scrollInPanel(contentPanel, el, 20);
      history.replaceState(null, '', '#' + encodeURIComponent(id));
      return;
    }}
    if (o.fromClick) {{
      restoreIndexScrollTop(indexTop);
      history.replaceState(null, '', '#' + encodeURIComponent(id));
      restoreIndexScrollTop(indexTop);
      setTimeout(() => restoreIndexScrollTop(indexTop), 0);
      return;
    }}
    if (activeRow && indexScroll && o.scrollList) {{
      if (!isVisibleInPanel(indexScroll, activeRow)) {{
        scrollInPanel(indexScroll, activeRow, 8);
      }}
    }}
    history.replaceState(null, '', '#' + encodeURIComponent(id));
  }}

  if (indexScroll) {{
    indexScroll.addEventListener('wheel', (e) => {{
      const max = indexScroll.scrollHeight - indexScroll.clientHeight;
      if (max <= 0) return;
      const dy = e.deltaY;
      if (!dy) return;
      const atTop = indexScroll.scrollTop <= 0;
      const atBottom = indexScroll.scrollTop >= max - 1;
      if ((dy < 0 && atTop) || (dy > 0 && atBottom)) {{
        e.preventDefault();
        return;
      }}
      e.preventDefault();
      indexScroll.scrollTop += dy;
    }}, {{ passive: false }});

    indexScroll.addEventListener('keydown', (e) => {{
      if (e.key === 'ArrowDown' || e.key === 'j') {{
        e.preventDefault();
        focusListRow(listFocusIndex < 0 ? 0 : listFocusIndex + 1);
      }} else if (e.key === 'ArrowUp' || e.key === 'k') {{
        e.preventDefault();
        focusListRow(listFocusIndex < 0 ? 0 : listFocusIndex - 1);
      }} else if (e.key === 'Enter') {{
        const vis = visibleRows();
        const tr = vis[listFocusIndex >= 0 ? listFocusIndex : 0];
        if (tr) {{ e.preventDefault(); goTo(tr.dataset.aid, {{ fromClick: true }}); }}
      }}
    }});
  }}

  window.__applyGrammarFilter = applyFilter;
  window.__grammarGoTo = goTo;
  window.__grammarLockIndexScroll = lockIndexScrollTop;
  window.__grammarRestoreIndexScroll = restoreIndexScrollTop;

  document.querySelector('#idx tbody').addEventListener('click', e => {{
    const tr = e.target.closest('tr');
    if (!tr || tr.classList.contains('hidden')) return;
    e.preventDefault();
    goTo(tr.dataset.aid, {{ fromClick: true }});
  }});

  document.getElementById('top-btn').onclick = () => {{
    if (contentPanel) contentPanel.scrollTop = 0;
    else window.scrollTo(0, 0);
  }};
}})();
</script>
<script>
{sync_config_js}
</script>
<script>
{ui_js}
</script>
<script>
{sync_js}
</script>
</body>
</html>"""


def main() -> None:
    points = load_points()
    bodies: dict[str, dict[str, str]] = {}
    lesson_exercises: dict[tuple[str, int], str] = {}
    body_cache: dict[Path, dict[str, dict[str, str]]] = {}
    ex_cache: dict[Path, dict[int, str]] = {}

    for p in points:
        md_path = BASE / p["md_rel"]
        if md_path not in body_cache:
            body_cache[md_path] = extract_bodies(md_path)
        if md_path not in ex_cache:
            ex_cache[md_path] = extract_exercises(md_path)
        aid = p["anchor_id"]
        if aid in body_cache[md_path]:
            bodies[aid] = body_cache[md_path][aid]
        ex_rel, ex_gnum = resolve_exercise_key(p, bodies)
        ex_md = BASE / ex_rel
        if ex_md not in ex_cache:
            ex_cache[ex_md] = extract_exercises(ex_md)
        if ex_gnum in ex_cache[ex_md]:
            lesson_exercises[(p["md_rel"], p["grammar_num"])] = ex_cache[ex_md][ex_gnum]

    importance = load_importance()
    if not importance:
        print("Note: run compute_jlpt_importance.py to generate star ratings")
    lesson_titles = extract_lesson_titles()
    html_out = build_html(points, bodies, lesson_exercises, importance, lesson_titles)
    OUT_HTML.write_text(html_out, encoding="utf-8")
    missing = sum(1 for p in points if p["anchor_id"] not in bodies)
    with_ex = sum(1 for p in points if (p["md_rel"], p["grammar_num"]) in lesson_exercises)
    print(
        f"Wrote: {OUT_HTML.name} ({len(html_out) // 1024} KB, {len(points)} entries, "
        f"{missing} missing body, {with_ex} with exercises)"
    )


if __name__ == "__main__":
    main()
