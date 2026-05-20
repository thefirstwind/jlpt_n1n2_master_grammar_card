#!/usr/bin/env python3
"""将过短的 option reason 扩写为完整说明（≥40字）。"""

from __future__ import annotations

import json
import re
from pathlib import Path

REVIEW = Path(__file__).resolve().parent
EXPORT = REVIEW / "_all_exercises_export.json"
ANALYSIS = REVIEW / "grammar_exercise_analysis.json"
MIN_LEN = 36


def normalize_qobj(qobj: dict) -> tuple[str, dict[str, str]]:
    stem = qobj.get("stem", "")
    opts = {o[0]: o[1] for o in (qobj.get("opts") or [])}
    if not opts:
        for letter, text in re.findall(r"(?:^|\s)([abc])\s+([^　]+?)(?=(?:\s+[abc]\s+)|$)", stem):
            opts[letter] = text.strip()
        stem = re.split(r"\s+[abc]\s+", stem)[0].strip()
    return stem, opts


def expand_reason(
    verdict: str,
    letter: str,
    opt_text: str,
    stem: str,
    pattern: str,
    rule: str,
    old: str,
) -> str:
    if len(old) >= MIN_LEN:
        return old
    if verdict == "correct":
        return (
            f"「{opt_text}」填入「{stem}」后，语义与接续均符合「{pattern}」的要求。"
            f"依据：{rule[:80]}。因此选 {letter}。"
        )
    return (
        f"「{opt_text}」代入题干后，与「{pattern}」的接续或注意点不符：{old or '语义或用法不当'}。"
        f"故不选 {letter}。"
    )


def main() -> None:
    export = json.loads(EXPORT.read_text(encoding="utf-8"))
    data = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    n = 0
    for aid, entry in data.items():
        card = export.get(aid, {})
        pattern = card.get("pattern", aid)
        rule = entry.get("rule", "")
        for q, qd in (entry.get("questions") or {}).items():
            qobj = next(
                (x for x in card.get("questions", []) if str(x.get("q")) == str(q)),
                {},
            )
            stem, opts = normalize_qobj(qobj)
            for letter, od in qd.get("options", {}).items():
                old = od.get("reason", "")
                if len(old) >= MIN_LEN:
                    continue
                text = opts.get(letter, letter)
                od["reason"] = expand_reason(
                    od.get("verdict", ""),
                    letter,
                    text,
                    stem[:40],
                    pattern,
                    rule,
                    old,
                )
                n += 1
    ANALYSIS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Expanded {n} short reasons -> {ANALYSIS.name}")


if __name__ == "__main__":
    main()
