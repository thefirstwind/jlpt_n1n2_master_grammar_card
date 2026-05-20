#!/usr/bin/env python3
"""
从 _all_exercises_export.json + 答案独立生成每题解析（不读旧 analysis）。
每选项给出 verdict + 详细 reason（含为何不选）。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REVIEW = Path(__file__).resolve().parent
EXPORT = REVIEW / "_all_exercises_export.json"
ANSWERS = REVIEW / "grammar_exercise_answers_expert.json"
OUT = REVIEW / "grammar_exercise_analysis.json"
PARTS = REVIEW / "analysis_parts"

VOLITION = re.compile(
    r"ください|ほうがいい|ましょう|よう[。、]?$|なさい|したい|してほしい|しよう|べき|飛び出そう|集合"
)
STEM_OPTS = re.compile(r"(?:^|\s)([abc])\s+([^　]+?)(?=(?:\s+[abc]\s+)|$)")


def normalize_qobj(qobj: dict) -> tuple[str, list[tuple[str, str]]]:
    stem = qobj.get("stem", "")
    opts = qobj.get("opts") or []
    if opts:
        return stem, [(o[0], o[1]) for o in opts]
    pairs = STEM_OPTS.findall(stem)
    if pairs:
        base = re.split(r"\s+[abc]\s+", stem)[0].strip()
        return base, [(a, b.strip()) for a, b in pairs]
    return stem, []


def extract_rule(body: str) -> str:
    parts = []
    if "接续：" in body:
        parts.append(body.split("接续：")[1].split("注意：")[0].strip().replace("\n", " "))
    if "注意：" in body:
        parts.append(body.split("注意：")[1].strip().replace("\n", " ")[:200])
    return "；".join(p for p in parts if p)


def check_volition_block(body: str) -> bool:
    return bool(re.search(r"意志|働きかけ|要求听话人", body))


def analyze_option(
    body: str,
    pattern: str,
    stem: str,
    letter: str,
    text: str,
    correct: str,
) -> tuple[str, str]:
    is_correct = letter == correct
    verdict = "correct" if is_correct else "wrong"
    reasons: list[str] = []

    if check_volition_block(body):
        if VOLITION.search(text):
            reasons.append("该语法点要求后项不接意志、请求或命令，此项含意志/请求表达，故不选。")
        elif is_correct:
            reasons.append("后项为客观事实或状态叙述，符合「不接意志·働きかけ」的限制。")

    if "が早いか" in pattern or "や" in pattern:
        if "（　）" in stem and stem.index("（　）") < stem.find("が早いか") if "が早いか" in stem else 999:
            if text.endswith("て") or text.endswith("ている"):
                reasons.append("空格在「が早いか/や」之前，需动词辞書形或た形，て形不能接在此位置。")
            elif re.search(r"[^い]る$|う$|く$|ぐ$|す$|つ$|ぬ$|ぶ$|む$", text) and is_correct:
                reasons.append("辞書形（或た形）可接在瞬间动作之后，与接续一致。")
        if re.search(r"が早いか、$|や、$|や否や、$", stem):
            if VOLITION.search(text):
                reasons.append("后项槽位不能接意志、希望或命令，只能接已发生的事实。")

    if "なり" in pattern and "三人称" in body:
        if re.match(r"^(わたし|わたしたち|私)", text):
            reasons.append("「なり」主语通常为三人称且前后主语一致，第一人称不宜放在主语空格。")

    if "をおいて" in pattern:
        if "だけ" in text:
            reasons.append("「をおいてほかにない」已表唯一性，再加「だけ」语义重复。")
        if is_correct and "ほかに" in stem:
            reasons.append("与「ほかにない/ほかにあるまい」搭配，表示除此以外没有/几乎没有。")

    if "ならでは" in pattern and is_correct:
        reasons.append("能体现「只有…才具备」的独特性，与ならでは的评価语气一致。")

    if "にとどまらず" in pattern and is_correct:
        reasons.append("前项为较小范围，后项（或在后项槽位）应扩大到更广范围，形成对比。")

    if "はおろか" in pattern:
        if "さえ" in text or "もない" in text:
            if is_correct:
                reasons.append("「はおろか」后项常用「さえ/まで」等强调程度更高。")

    if "てからというもの" in pattern:
        if "ている" in text or "毎日" in text or "いつも" in text:
            if is_correct:
                reasons.append("后项表变化后持续的状态，符合「てからというもの」。")
        if re.search(r"買った|始めた|した$", text) and not is_correct:
            reasons.append("一次性动作不能体现「之后一直……」的持续义。")

    if "そばから" in body:
        if is_correct and ("どんどん" in text or "聞いた" in text or "買った" in text):
            reasons.append("体现刚做完又反复发生，符合「そばから」的循环义。")

    if is_correct and not reasons:
        reasons.append(f"代入题干后语义、接续与「{pattern}」的用法一致，故为正确答案。")
    if not is_correct and not reasons:
        reasons.append("代入后要么接续不当，要么与题干逻辑或本语法点的注意点不符，故排除。")

    return verdict, " ".join(reasons)


def generate_for_export() -> dict:
    export = json.loads(EXPORT.read_text(encoding="utf-8"))
    answers = json.loads(ANSWERS.read_text(encoding="utf-8"))
    out: dict = {}

    for aid, card in sorted(export.items()):
        pattern = card.get("pattern", "")
        body = card.get("body", "")
        rule = extract_rule(body)
        out[aid] = {"rule": rule, "questions": {}}
        ans_map = answers.get(aid, {})

        for qobj in card["questions"]:
            q = str(qobj["q"])
            stem, opts = normalize_qobj(qobj)
            correct = ans_map.get(q, "").lower()
            if not opts:
                continue
            qentry = {"answer": correct, "options": {}}
            for letter, text in opts:
                verdict, reason = analyze_option(
                    body, pattern, stem, letter, text, correct
                )
                qentry["options"][letter] = {"verdict": verdict, "reason": reason}
            out[aid]["questions"][q] = qentry
    return out


def merge_parts(base: dict) -> dict:
    if not PARTS.is_dir():
        return base
    for path in sorted(PARTS.glob("*.json")):
        part = json.loads(path.read_text(encoding="utf-8"))
        for aid, entry in part.items():
            if aid not in base:
                base[aid] = entry
                continue
            base[aid]["rule"] = entry.get("rule") or base[aid].get("rule", "")
            for q, qd in (entry.get("questions") or {}).items():
                # 人工块优先：选项 reason 更长则采用
                if q not in base[aid]["questions"]:
                    base[aid]["questions"][q] = qd
                else:
                    for opt, od in qd.get("options", {}).items():
                        old = base[aid]["questions"][q]["options"].get(opt, {})
                        new_r = od.get("reason", "")
                        old_r = old.get("reason", "")
                        if len(new_r) > len(old_r) or (
                            len(new_r) >= 8 and "故排除" not in new_r
                        ):
                            base[aid]["questions"][q]["options"][opt] = od
                    if qd.get("answer"):
                        base[aid]["questions"][q]["answer"] = qd["answer"]
    return base


def main() -> None:
    base = generate_for_export()
    merged = merge_parts(base)
    OUT.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    n = sum(len(v.get("questions", {})) for v in merged.values())
    print(f"Wrote {OUT.name}: {len(merged)} anchors, {n} questions")


if __name__ == "__main__":
    main()
