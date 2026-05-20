#!/usr/bin/env python3
"""按课文「注意」等硬规则校验并修正练习答案；优先采专家 B 当 A/C 违反规则时。"""

from __future__ import annotations

import json
import re
from pathlib import Path

REVIEW_DIR = Path(__file__).resolve().parent
EXPORT = REVIEW_DIR / "_all_exercises_export.json"
ANSWERS = REVIEW_DIR / "grammar_exercise_answers_expert.json"
REPORT = REVIEW_DIR / "grammar_exercise_answer_fixes.json"

# 后项禁止：意志・请求・建议
VOLITION_RE = re.compile(
    r"ください|ほうがいい|ましょう|よう[。、]?$|なさい|したい|してほしい|しよう|べき"
)
# 后项禁止：働きかけ
SOLICIT_RE = re.compile(r"ください|なさい|ましょう|よう[。、]?$|べきだ|しなければ")


def opt_text(card: dict, qobj: dict, letter: str) -> str:
    for k, t in qobj.get("opts", []):
        if k == letter:
            return t
    return ""


def rule_no_volition_after(card: dict, qobj: dict, letter: str) -> bool | None:
    """True=该选项可用；False=违反「不接意志/请求」；None=本规则不适用。"""
    body = card.get("body", "")
    if not re.search(r"意志|要求听话人|働きかけ", body):
        return None
    text = opt_text(card, qobj, letter)
    if not text:
        return None
    if VOLITION_RE.search(text) or SOLICIT_RE.search(text):
        return False
    return True


def rule_no_good_result(card: dict, qobj: dict, letter: str) -> bool | None:
    body = card.get("body", "")
    if "いい結果" not in body and "良くない結果" not in body:
        return None
    text = opt_text(card, qobj, letter)
    if not text:
        return None
    # あげく等：后项不宜是正面成功（粗略：成功/うれしい/よかった）
    if re.search(r"成功|うれし|喜ん|解決|治っ|直っ", text):
        return False
    return True


def rule_formal_motte(card: dict, qobj: dict, letter: str) -> bool | None:
    body = card.get("body", "")
    if "をもって" not in card.get("pattern", "") and "をもって" not in body:
        return None
    stem = qobj.get("stem", "")
    text = opt_text(card, qobj, letter)
    if "以上" in stem and "をも" in stem:
        return letter == "a" or "以上" in text
    return None


def rule_nari_third_person(card: dict, qobj: dict, letter: str) -> bool | None:
    if "なり" not in card.get("pattern", ""):
        return None
    body = card.get("body", "")
    if "三人称" not in body:
        return None
    text = opt_text(card, qobj, letter)
    stem = qobj.get("stem", "")
    if "（　）" in stem and stem.strip().startswith("（"):
        # 主语在空格里：わたし/わたしたち 一般排除
        if re.match(r"^(わたし|わたしたち|私)", text):
            return False
    return True


RULES = [
    rule_no_volition_after,
    rule_no_good_result,
    rule_formal_motte,
    rule_nari_third_person,
]


def score_option(card: dict, qobj: dict, letter: str) -> int:
    """越高越合法；负分表示明确违反某条规则。"""
    score = 0
    for rule in RULES:
        r = rule(card, qobj, letter)
        if r is False:
            score -= 10
        elif r is True:
            score += 1
    return score


def load_expert_b() -> dict[str, dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for path in sorted(REVIEW_DIR.glob("_reanswer_B_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for aid, ans in data.items():
            merged.setdefault(aid, {}).update(
                {str(q): str(a).lower() for q, a in ans.items()}
            )
    return merged


def pick_best(
    card: dict, qobj: dict, current: str, expert_b: str | None
) -> tuple[str, str]:
    letters = [o[0] for o in qobj.get("opts", []) if o and o[0]]
    if not letters:
        return current, "no_opts"
    scored = [(letter, score_option(card, qobj, letter)) for letter in letters]
    max_s = max(s for _, s in scored)
    if max_s < 0:
        # 全部违规：取最高分的
        best = max(scored, key=lambda x: x[1])[0]
        return best, "all_bad_pick_least_bad"

    valid = [letter for letter, s in scored if s >= 0]
    if len(valid) == 1:
        return valid[0], "only_one_valid"

    if expert_b and expert_b in valid:
        cur_score = score_option(card, qobj, current) if current in letters else -99
        b_score = score_option(card, qobj, expert_b)
        if b_score > cur_score:
            return expert_b, "prefer_B_passes_rules"

    if current in valid:
        return current, "keep"

    return valid[0], "pick_first_valid"


def main() -> None:
    export = json.loads(EXPORT.read_text(encoding="utf-8"))
    answers = json.loads(ANSWERS.read_text(encoding="utf-8"))
    expert_b = load_expert_b()
    fixes: list[dict] = []

    for aid, card in export.items():
        if aid not in answers:
            answers[aid] = {}
        for qobj in card["questions"]:
            q = str(qobj["q"])
            cur = answers[aid].get(q)
            b = expert_b.get(aid, {}).get(q)
            if not cur:
                continue
            new, reason = pick_best(card, qobj, cur, b)
            if new != cur:
                fixes.append(
                    {
                        "anchor_id": aid,
                        "pattern": card.get("pattern", ""),
                        "q": q,
                        "was": cur,
                        "now": new,
                        "expert_b": b,
                        "reason": reason,
                        "stem": qobj.get("stem", "")[:80],
                    }
                )
                answers[aid][q] = new

    ANSWERS.write_text(json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT.write_text(json.dumps(fixes, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Fixed {len(fixes)} answers -> {ANSWERS.name}")
    print(f"Report: {REPORT.name}")
    for f in fixes[:15]:
        print(f"  {f['anchor_id']} Q{f['q']}: {f['was']}->{f['now']} ({f['reason']})")


if __name__ == "__main__":
    main()
