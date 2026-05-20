#!/usr/bin/env python3
"""三专家多数决合并练习答案。"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

REVIEW_DIR = Path(__file__).resolve().parent
EXPORT = REVIEW_DIR / "_all_exercises_export.json"
EXPERT_A = REVIEW_DIR / "_expert_A_snapshot.json"
OUT = REVIEW_DIR / "grammar_exercise_answers_expert.json"
DISPUTES = REVIEW_DIR / "grammar_exercise_answer_disputes.json"


def load_glob(pattern: str) -> dict[str, dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for path in sorted(REVIEW_DIR.glob(pattern)):
        data = json.loads(path.read_text(encoding="utf-8"))
        for aid, answers in data.items():
            if aid not in merged:
                merged[aid] = {}
            for q, a in answers.items():
                merged[aid][str(q)] = str(a).lower()
    return merged


def main() -> None:
    expert_a = json.loads(EXPERT_A.read_text(encoding="utf-8")) if EXPERT_A.exists() else {}
    expert_b = load_glob("_reanswer_B_*.json")
    expert_c = load_glob("_reanswer_C_*.json")
    export = json.loads(EXPORT.read_text(encoding="utf-8"))

    final: dict[str, dict[str, str]] = {}
    disputes: list[dict] = []
    stats = {"unanimous": 0, "majority": 0, "split3": 0, "missing_b": 0, "missing_c": 0}

    for aid, card in export.items():
        final[aid] = {}
        for qobj in card["questions"]:
            q = str(qobj["q"])
            votes = {
                "A": expert_a.get(aid, {}).get(q),
                "B": expert_b.get(aid, {}).get(q),
                "C": expert_c.get(aid, {}).get(q),
            }
            if not votes["B"]:
                stats["missing_b"] += 1
            if not votes["C"]:
                stats["missing_c"] += 1
            present = {k: v for k, v in votes.items() if v in ("a", "b", "c")}
            if len(present) < 2:
                # 不足两票：用已有票或 A
                pick = votes["A"] or votes["B"] or votes["C"]
                if pick:
                    final[aid][q] = pick
                continue
            counts = Counter(present.values())
            winner, n = counts.most_common(1)[0]
            if n == 3:
                stats["unanimous"] += 1
            elif n == 2:
                stats["majority"] += 1
            else:
                stats["split3"] += 1
                disputes.append(
                    {
                        "anchor_id": aid,
                        "pattern": card.get("pattern", ""),
                        "q": q,
                        "stem": qobj.get("stem", ""),
                        "votes": votes,
                    }
                )
            final[aid][q] = winner

    # 三人分歧：取 B（第二专家）作为合议 tie-break，并记入 disputes
    for d in disputes:
        aid, q = d["anchor_id"], d["q"]
        tie = expert_b.get(aid, {}).get(q) or expert_a.get(aid, {}).get(q)
        if tie:
            final[aid][q] = tie

    OUT.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    DISPUTES.write_text(
        json.dumps(disputes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    n_final = sum(len(v) for v in final.values())
    print(
        f"Consensus: {len(final)} cards, {n_final} answers | "
        f"unanimous {stats['unanimous']}, majority {stats['majority']}, "
        f"3-way split {stats['split3']} (tie-break B) | "
        f"missing B {stats['missing_b']}, missing C {stats['missing_c']}"
    )
    print(f"Disputes logged: {len(disputes)} -> {DISPUTES.name}")


if __name__ == "__main__":
    main()
