#!/usr/bin/env python3
"""合并 _reanswer_out_*.json → grammar_exercise_answers_expert.json，并按 anchor_id 校验题数。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REVIEW_DIR = Path(__file__).resolve().parent
BASE = REVIEW_DIR.parent
OUT = REVIEW_DIR / "grammar_exercise_answers_expert.json"
EXPORT = REVIEW_DIR / "_all_exercises_export.json"


def main() -> None:
    merged: dict[str, dict[str, str]] = {}
    for path in sorted(REVIEW_DIR.glob("_reanswer_out_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for aid, answers in data.items():
            if aid not in merged:
                merged[aid] = {}
            for q, a in answers.items():
                merged[aid][str(q)] = str(a).lower()

    if EXPORT.exists():
        export = json.loads(EXPORT.read_text(encoding="utf-8"))
        missing_cards: list[str] = []
        missing_q: list[str] = []
        for aid, card in export.items():
            if aid not in merged:
                missing_cards.append(aid)
                continue
            for q in card["questions"]:
                qn = str(q["q"])
                if qn not in merged[aid]:
                    missing_q.append(f"{aid}#{qn}")
        if missing_cards or missing_q:
            print(f"WARNING: {len(missing_cards)} cards, {len(missing_q)} questions missing")
            if missing_cards[:5]:
                print("  cards:", missing_cards[:10])
            if missing_q[:5]:
                print("  questions:", missing_q[:10])
            sys.exit(1)

    OUT.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    n_q = sum(len(v) for v in merged.values())
    print(f"Wrote {OUT.name}: {len(merged)} cards, {n_q} answers")


if __name__ == "__main__":
    main()
