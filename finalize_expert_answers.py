#!/usr/bin/env python3
"""合并 _reanswer_out → 应用人工复核修正 → 规则校验 → 写入 expert/json。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

REVIEW_DIR = Path(__file__).resolve().parent
EXPORT = REVIEW_DIR / "_all_exercises_export.json"
OUT = REVIEW_DIR / "grammar_exercise_answers_expert.json"
ANSWERS_COPY = REVIEW_DIR / "grammar_exercise_answers.json"

# 独立语法分析后确认的答案（覆盖 OCR/旧批次）
VERIFIED: dict[str, dict[str, str]] = {
    "n1-l01-g01": {"1": "b", "2": "a", "3": "c"},
    "n1-l01-g02": {"1": "b", "2": "b", "3": "c"},
    "n1-l01-g03": {"1": "c", "2": "b", "3": "c"},
    "n1-l01-g04": {"1": "a", "2": "b", "3": "b"},
    "n1-l01-g05": {"1": "b", "2": "a", "3": "c"},
    "n1-l01-g06": {"1": "b", "2": "a", "3": "c"},
    "n1-l02-g01": {"1": "a", "2": "c", "3": "b", "4": "a", "5": "b"},
    "n1-l02-g02": {"1": "c", "2": "a", "3": "b"},
    "n1-l02-g03": {"1": "a", "2": "b", "3": "c"},
    "n1-l02-g04": {"1": "a", "2": "b", "3": "c", "4": "b"},
    "n1-l02-g05": {"1": "c", "2": "c", "3": "b"},
    "n1-l03-g01": {"1": "c", "2": "a", "3": "b"},
    "n1-l03-g02": {"1": "a", "2": "a", "3": "c"},
    "n1-l03-g03": {"1": "b", "2": "a", "3": "c"},
    "n1-l03-g04": {"1": "b", "2": "a", "3": "b"},
    "n1-l03-g05": {"1": "b", "2": "a"},
}


def load_out_batches() -> dict[str, dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for path in sorted(REVIEW_DIR.glob("_reanswer_out_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for aid, ans in data.items():
            merged.setdefault(aid, {})
            merged[aid].update({str(q): str(a).lower() for q, a in ans.items()})
    return merged


def main() -> None:
    export = json.loads(EXPORT.read_text(encoding="utf-8"))
    if OUT.exists():
        answers = json.loads(OUT.read_text(encoding="utf-8"))
        answers = {k: {str(q): str(a).lower() for q, a in v.items()} for k, v in answers.items()}
    else:
        answers = load_out_batches()
    changes: list[str] = []

    for aid, fixes in VERIFIED.items():
        answers.setdefault(aid, {})
        for q, letter in fixes.items():
            old = answers[aid].get(q)
            answers[aid][q] = letter
            if old != letter:
                changes.append(f"{aid} Q{q}: {old} -> {letter}")

    # 确保每题都有答案
    missing = []
    for aid, card in export.items():
        answers.setdefault(aid, {})
        for qobj in card["questions"]:
            q = str(qobj["q"])
            if q not in answers[aid]:
                missing.append(f"{aid}#{q}")
    if missing:
        raise SystemExit(f"Missing {len(missing)} answers, e.g. {missing[:5]}")

    OUT.write_text(json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(OUT, ANSWERS_COPY)
    print(f"Wrote {OUT.name}: {sum(len(v) for v in answers.values())} answers")
    print(f"Verified overrides: {len(changes)}")
    for line in changes[:20]:
        print(f"  {line}")


if __name__ == "__main__":
    main()
