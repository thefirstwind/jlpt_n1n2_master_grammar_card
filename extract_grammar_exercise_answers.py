#!/usr/bin/env python3
"""OCR 实力养成篇课后练习答案页，生成 grammar_exercise_answers.json。"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import fitz
from PIL import Image, ImageOps
import pytesseract

BASE = Path(__file__).resolve().parent.parent
REVIEW_DIR = Path(__file__).resolve().parent
OUT_JSON = REVIEW_DIR / "grammar_exercise_answers.json"
OCR_CACHE = REVIEW_DIR / "grammar_exercise_answers_ocr.txt"
INDEX_JSON = BASE / "grammar_index.json"

N1_PDF = BASE / "新完全掌握日语能力考试.N1级.语法.pdf"
N2_PDF = BASE / "新完全掌握日语能力考试.N2级.语法.pdf"
N1_PAGES = range(196, 211)
N2_PAGES = range(309, 338)

CIRC_NUM = "①②③④⑤⑥⑦⑧⑨⑩"
DIG_TO_OPT = {"1": "a", "2": "b", "3": "c", "4": "d"}

PRACTICE_PAT = re.compile(
    r"練\s*[習暂暫]\s*[\]\[]*0*(\d+)|\[\s*練\s*[習暂暫]\s*(\d+)\s*\]",
    re.I,
)
LESSON_PAT = re.compile(
    r"\|\s*(\d{1,2})\s*(?:課|朝|電|昌|部)\s*\|"
    r"|^(\d{1,2})\s*課\s*\|"
    r"|第\s*(\d{1,2})\s*課"
    r"|\|\s*(\d{1,2})\s*(?:昌|朝|電)\s*$"
    r"|(\d{1,2})\s*課\s*\|"
)
SKIP_LINE = re.compile(
    r"解析|正解|正秦|答案|【|洋文|表文|玉文|詳文|逃項|輝項|部\s*文|文章の文法"
)


def ocr_pdf(pdf: Path, pages: range, tag: str) -> str:
    doc = fitz.open(pdf)
    chunks: list[str] = []
    for p in pages:
        if p < 1 or p > doc.page_count:
            continue
        pix = doc[p - 1].get_pixmap(dpi=280, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        gray = ImageOps.autocontrast(img.convert("L"))
        t = pytesseract.image_to_string(gray, lang="jpn", config="--psm 6")
        chunks.append(f"---{tag} {p}---\n{t}")
    doc.close()
    return "\n".join(chunks)


def ensure_ocr_cache() -> tuple[str, str]:
    if OCR_CACHE.exists():
        raw = OCR_CACHE.read_text(encoding="utf-8")
    else:
        raw = ocr_pdf(N1_PDF, N1_PAGES, "N1") + "\n" + ocr_pdf(N2_PDF, N2_PAGES, "N2")
        OCR_CACHE.write_text(raw, encoding="utf-8")
    n1_parts = re.findall(r"---N1 \d+---\n(.*?)(?=---N1 \d+---|---N2 |\Z)", raw, re.S)
    n2_parts = re.findall(r"---N2 \d+---\n(.*?)(?=---N2 \d+---|\Z)", raw, re.S)
    return "\n".join(n1_parts), "\n".join(n2_parts)


def load_lesson_grammar_slots() -> dict[str, list[tuple[int, int]]]:
    """level -> [(lesson, grammar_num), …] 按课内语法序号排序。"""
    data = json.loads(INDEX_JSON.read_text(encoding="utf-8"))["merged"]
    out: dict[str, list[tuple[int, int]]] = {"N1": [], "N2": []}
    seen: dict[str, set[tuple[int, int]]] = {"N1": set(), "N2": set()}
    for p in data:
        lvl = p["level"]
        key = (p["lesson"], p["grammar_num"])
        if key in seen[lvl]:
            continue
        seen[lvl].add(key)
        out[lvl].append(key)
    for lvl in out:
        out[lvl].sort()
    return out


def _merge_answers(
    result: dict[str, dict[str, str]], aid: str, ans: dict[str, str]
) -> None:
    prev = result.get(aid, {})
    merged = {**prev, **ans}
    if len(merged) > len(prev):
        result[aid] = merged


def extract_answers_from_line(line: str) -> dict[str, str] | None:
    if SKIP_LINE.search(line):
        return None
    norm = line.replace("。", ".").replace("，", ",")

    pairs = re.findall(
        r"(?<![0-9])([1-9]|10)\s*[\.\．、\s]*([abcABC])(?![a-zA-Z])",
        norm,
    )
    if len(pairs) >= 2:
        return {q: a.lower() for q, a in pairs}

    circ = re.findall(r"([①②③④⑤⑥⑦⑧⑨⑩])\s*([abcABC])", norm)
    if len(circ) >= 2:
        return {str(CIRC_NUM.index(s) + 1): a.lower() for s, a in circ}

    bracket = re.findall(r"\[([1-9]|10)\]\s*([1-4])", norm)
    if len(bracket) >= 2:
        return {q: DIG_TO_OPT[d] for q, d in bracket}

    loose = re.findall(r"(?:^|[^\[])\[?([1-9]|10)\]?\s+([1-4])(?=\s|$|\[)", norm)
    if len(loose) >= 2:
        return {q: DIG_TO_OPT[d] for q, d in loose}

    return None


def collect_answer_blobs(text: str) -> list[tuple[int, dict[str, str]]]:
    """按 OCR 行序收集 (lesson_hint, answers)；lesson_hint=0 表示未标明课次。"""
    blobs: list[tuple[int, dict[str, str]]] = []
    lesson = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("---"):
            continue
        lm = LESSON_PAT.search(line)
        if lm:
            lesson = int(next(g for g in lm.groups() if g))
        if SKIP_LINE.search(line) and not PRACTICE_PAT.search(line):
            if "解析" in line or "逃項" in line:
                continue
        ans = extract_answers_from_line(line)
        if ans:
            blobs.append((lesson, ans))
    return blobs


def parse_level_blocks(text: str, level: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        lesson_m = LESSON_PAT.search(line)
        if not lesson_m:
            i += 1
            continue
        lesson = int(next(g for g in lesson_m.groups() if g))
        gnum = 0
        i += 1
        while i < len(lines):
            line = lines[i]
            if LESSON_PAT.search(line):
                break
            pm = PRACTICE_PAT.search(line)
            if pm:
                gnum = int(next(g for g in pm.groups() if g))
            ans = extract_answers_from_line(line)
            if ans:
                if gnum == 0:
                    gnum = 1
                aid = f"{level.lower()}-l{lesson:02d}-g{gnum:02d}"
                _merge_answers(result, aid, ans)
                if not pm:
                    gnum += 1
            i += 1
    return result


def align_blobs_to_index(
    blobs: list[tuple[int, dict[str, str]]],
    slots: list[tuple[int, int]],
    level: str,
) -> dict[str, dict[str, str]]:
    """将 OCR 答案块按课次提示 + 索引顺序对齐到各语法点。"""
    result: dict[str, dict[str, str]] = {}
    by_lesson: dict[int, list[dict[str, str]]] = defaultdict(list)
    orphan: list[dict[str, str]] = []
    for les, ans in blobs:
        if les > 0:
            by_lesson[les].append(ans)
        else:
            orphan.append(ans)

    # 课次明确的：按该课语法点数量依次分配答案块
    lesson_gnums: dict[int, list[int]] = defaultdict(list)
    for les, gnum in slots:
        lesson_gnums[les].append(gnum)

    for les in sorted(lesson_gnums):
        gnums = sorted(lesson_gnums[les])
        blist = by_lesson.get(les, [])
        for i, gnum in enumerate(gnums):
            if i >= len(blist):
                break
            aid = f"{level.lower()}-l{les:02d}-g{gnum:02d}"
            _merge_answers(result, aid, blist[i])

    # 未标课次的块 + 仍缺答案的课：按索引顺序填坑
    assigned = set(result)
    need: list[tuple[int, int]] = []
    for les, gnum in slots:
        aid = f"{level.lower()}-l{les:02d}-g{gnum:02d}"
        if aid not in assigned:
            need.append((les, gnum))
    pool = orphan + [a for les in sorted(by_lesson) if les not in lesson_gnums for a in by_lesson[les]]
    # 上面不对 - 只应用 orphan 填 need
    for (les, gnum), ans in zip(need, orphan):
        aid = f"{level.lower()}-l{les:02d}-g{gnum:02d}"
        _merge_answers(result, aid, ans)

    return result


def parse_level(
    text: str, level: str, slots: list[tuple[int, int]]
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    blobs = collect_answer_blobs(text)
    for part in (parse_level_blocks,):
        for aid, ans in part(text, level).items():
            _merge_answers(result, aid, ans)
    for aid, ans in align_blobs_to_index(blobs, slots, level).items():
        _merge_answers(result, aid, ans)
    return result


def main() -> None:
    n1_text, n2_text = ensure_ocr_cache()
    lesson_slots = load_lesson_grammar_slots()
    merged: dict[str, dict[str, str]] = {}
    merged.update(parse_level(n1_text, "N1", lesson_slots["N1"]))
    merged.update(parse_level(n2_text, "N2", lesson_slots["N2"]))
    OUT_JSON.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    with_5 = sum(1 for v in merged.values() if len(v) >= 5)
    total_q = sum(len(v) for v in merged.values())
    print(
        f"Wrote {len(merged)} grammar sets, {total_q} question keys "
        f"({with_5} sets with 5+ answers) -> {OUT_JSON.name}"
    )


if __name__ == "__main__":
    main()
