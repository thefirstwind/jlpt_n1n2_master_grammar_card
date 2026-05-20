#!/usr/bin/env python3
"""合并 answers_fresh/*.json → grammar_exercise_answers_expert.json"""

from __future__ import annotations

import json
from pathlib import Path

REVIEW = Path(__file__).resolve().parent.parent
FRESH = Path(__file__).resolve().parent
EXPORT = REVIEW / "_all_exercises_export.json"
OUT = REVIEW / "grammar_exercise_answers_expert.json"
OUT2 = REVIEW / "grammar_exercise_answers.json"


def main() -> None:
    export = json.loads(EXPORT.read_text(encoding="utf-8"))
    merged: dict[str, dict[str, str]] = {}
    skip = {"merge_fresh_answers.py"}
    for path in sorted(FRESH.glob("*.json")):
        if path.name in skip:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for aid, ans in data.items():
            merged.setdefault(aid, {}).update({str(q): str(a).lower() for q, a in ans.items()})

    missing = []
    for aid, card in export.items():
        for qobj in card["questions"]:
            q = str(qobj["q"])
            if merged.get(aid, {}).get(q) is None:
                missing.append(f"{aid}#{q}")

    if missing:
        raise SystemExit(f"Incomplete: {len(missing)} missing, e.g. {missing[:8]}")

    OUT.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT2.write_text(OUT.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Merged {len(merged)} cards, {sum(len(v) for v in merged.values())} answers")


if __name__ == "__main__":
    main()
