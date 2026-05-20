#!/usr/bin/env python3
"""练习解析 JSON 结构：每题每选项均有 verdict + reason。"""

from __future__ import annotations

from typing import Any

# grammar_exercise_analysis.json
# {
#   "n1-l01-g01": {
#     "rule": "接续与注意摘要",
#     "questions": {
#       "1": {
#         "answer": "b",
#         "options": {
#           "a": {"verdict": "wrong", "reason": "…"},
#           "b": {"verdict": "correct", "reason": "…"},
#           "c": {"verdict": "wrong", "reason": "…"}
#         }
#       }
#     }
#   }
# }


def empty_question(answer: str = "") -> dict[str, Any]:
    return {"answer": answer, "options": {}}


def validate_entry(entry: dict[str, Any], qids: list[str]) -> list[str]:
    errs: list[str] = []
    qs = entry.get("questions") or {}
    for q in qids:
        if q not in qs:
            errs.append(f"missing Q{q}")
            continue
        qd = qs[q]
        ans = qd.get("answer", "")
        opts = qd.get("options") or {}
        for letter in ("a", "b", "c"):
            if letter not in opts:
                errs.append(f"Q{q} missing opt {letter}")
            elif not opts[letter].get("reason"):
                errs.append(f"Q{q} opt {letter} empty reason")
        if ans and opts.get(ans, {}).get("verdict") != "correct":
            errs.append(f"Q{q} answer {ans} not marked correct")
    return errs
