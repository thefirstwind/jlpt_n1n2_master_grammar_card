#!/usr/bin/env python3
"""将 answers_fresh/*_analysis.md 转为 grammar_exercise_analysis.json（可合并多文件）。"""

from __future__ import annotations

import json
import re
from pathlib import Path

REVIEW = Path(__file__).resolve().parent
FRESH = REVIEW / "answers_fresh"
OUT = REVIEW / "grammar_exercise_analysis.json"
ANSWERS = REVIEW / "grammar_exercise_answers_expert.json"

ANCHOR_RE = re.compile(r"^##\s+(n[12]-l\d{2}-g\d{2})\s+")
Q_RE = re.compile(r"^###\s+Q(\d+)\s+")
RULE_RE = re.compile(r"^\*\*规则\*\*[：:]\s*(.+)$")
ANS_RE = re.compile(r"^\*\*答案[：:]\s*([abc])\*\*$")
TABLE_ROW = re.compile(
    r"^\|\s*\*{0,2}([abc])\s+(.+?)\*{0,2}\s*\|\s*(.+?)\s*\|?\s*$"
)


def parse_md(text: str) -> dict:
    result: dict = {}
    cur_anchor: str | None = None
    cur_q: str | None = None
    in_table = False

    for raw in text.splitlines():
        line = raw.strip()
        m = ANCHOR_RE.match(line)
        if m:
            cur_anchor = m.group(1)
            result[cur_anchor] = {"rule": "", "questions": {}}
            cur_q = None
            in_table = False
            continue
        if not cur_anchor:
            continue
        rm = RULE_RE.match(line)
        if rm:
            result[cur_anchor]["rule"] = rm.group(1).strip()
            continue
        qm = Q_RE.match(line)
        if qm:
            cur_q = qm.group(1)
            result[cur_anchor]["questions"][cur_q] = {
                "answer": "",
                "options": {},
            }
            in_table = False
            continue
        if cur_q and line.startswith("|") and "选项" in line:
            in_table = True
            continue
        if cur_q and in_table and line.startswith("|") and not line.startswith("|---"):
            row = TABLE_ROW.match(line)
            if not row:
                continue
            letter, text_opt, reason = row.group(1), row.group(2).strip(), row.group(3).strip()
            text_opt = re.sub(r"^\*\*|\*\*$", "", text_opt).strip()
            verdict = "correct" if reason.startswith("**") or "符合" in reason or "正确" in reason else "wrong"
            if "**" in row.group(2):
                verdict = "correct"
            reason = re.sub(r"^\*\*|\*\*$", "", reason).strip()
            result[cur_anchor]["questions"][cur_q]["options"][letter] = {
                "verdict": verdict,
                "reason": reason,
            }
            continue
        am = ANS_RE.match(line)
        if am and cur_q:
            result[cur_anchor]["questions"][cur_q]["answer"] = am.group(1)
            in_table = False

    # 以 answer 为准标记 correct
    if ANSWERS.exists():
        ans_all = json.loads(ANSWERS.read_text(encoding="utf-8"))
        for aid, entry in result.items():
            for q, qd in entry.get("questions", {}).items():
                letter = ans_all.get(aid, {}).get(q) or qd.get("answer")
                if letter:
                    qd["answer"] = letter
                for opt, od in qd.get("options", {}).items():
                    od["verdict"] = "correct" if opt == letter else "wrong"
    return result


def main() -> None:
    merged: dict = {}
    for path in sorted(FRESH.glob("*_analysis.md")):
        chunk = parse_md(path.read_text(encoding="utf-8"))
        for aid, entry in chunk.items():
            merged.setdefault(aid, {"rule": "", "questions": {}})
            if entry.get("rule"):
                merged[aid]["rule"] = entry["rule"]
            merged[aid]["questions"].update(entry.get("questions") or {})

    # 用答案文件补全 answer 字段
    if ANSWERS.exists():
        ans_all = json.loads(ANSWERS.read_text(encoding="utf-8"))
        for aid, qs in ans_all.items():
            if aid not in merged:
                merged[aid] = {"rule": "", "questions": {}}
            for q, letter in qs.items():
                merged[aid]["questions"].setdefault(
                    str(q), {"answer": letter, "options": {}}
                )
                merged[aid]["questions"][str(q)]["answer"] = letter

    OUT.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    n_q = sum(len(v.get("questions", {})) for v in merged.values())
    print(f"Wrote {OUT.name}: {len(merged)} anchors, {n_q} questions with analysis")


if __name__ == "__main__":
    main()
