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

PATTERN_HINTS = (
    ("が早いか", "“刚……就……”的瞬间接续"),
    ("や否や", "“一……马上……”的紧接关系"),
    ("なり", "动作一发生就立刻进入下一动作"),
    ("そばから", "刚做完又不断反复"),
    ("てからというもの", "变化之后一直持续下去"),
    ("にあって", "处于特殊局面/逆境中"),
    ("べく", "为了实现某个目的"),
    ("んがため", "为达成重大目的"),
    ("をもって", "以……为手段/凭借……"),
    ("ばこそ", "正因为……才……"),
    ("とあって", "因特殊情况而自然出现结果"),
    ("ならでは", "只有……才有的独特性"),
    ("にとどまらず", "从一个范围扩展到更大范围"),
    ("はおろか", "从轻到重的层级推进"),
    ("であれ", "无论哪一种情况都成立"),
    ("であろうと", "无论哪一种情况都成立"),
    ("といい", "从一个对象的两个方面作评价"),
    ("といわず", "不分部位或范围地全面覆盖"),
    ("いかん", "取决于前项条件"),
    ("をものともせず", "不畏困难或逆境"),
    ("をよそに", "对周围状况不理会"),
    ("に際して", "在正式场合或特定时点"),
    ("にあたって", "在重要时点或开始之前"),
    ("たとたん", "一发生立刻引出结果"),
    ("かないかのうちに", "几乎同时发生"),
    ("最中", "正在进行中的当下"),
    ("うちに", "趁状态尚未变化"),
    ("ばかりだ", "只朝一个方向恶化"),
    ("一方だ", "只朝一个方向发展"),
    ("上（に）", "在既有基础上再叠加"),
    ("に応じて", "随着条件变化而变化"),
    ("につれて", "随着前项变化而变化"),
    ("に伴って", "伴随前项变化而变化"),
    ("に関して", "关于某个话题"),
    ("によって", "原因/手段/被动来源"),
    ("につき", "正式说明理由或比例"),
    ("際（に）", "在特定时点或场合"),
    ("際に", "在特定时点或场合"),
    ("ようとしている", "动作正要发生"),
    ("つつ", "一边……一边……"),
    ("上（で）", "在前项基础上再往下走"),
    ("以来", "从某时点起延续至今"),
    ("にかけては", "在某方面特别擅长"),
    ("に限る", "限定条件下最合适"),
    ("限り", "只要/在……范围内"),
    ("に限らず", "不只局限于"),
    ("のみならず", "不只……而且……"),
    ("ばかりか", "不只是前项，连后项也……"),
    ("はもとより", "前项不用说，后项也……"),
    ("をめぐって", "围绕某议题展开"),
    ("ならいざしらず", "前项姑且不论，后项才是重点"),
    ("と思うと", "前项一发生后项立刻接上"),
    ("と思ったら", "前项一发生后项立刻接上"),
    ("てはじめて", "直到做了前项才出现后项"),
    ("をはじめとして", "以一个代表带出同类"),
    ("を通じて", "通过某种媒介/在整个期间"),
    ("を通して", "通过某种媒介/在整个期间"),
    ("に対して", "与前项形成对照或对象关系"),
    ("にこたえて", "回应前项的期待/要求"),
    ("をもとに", "以……为依据/基础"),
    ("をもとにして", "以……为依据/基础"),
    ("に基づいて", "以事实/规则为依据"),
    ("に沿って", "沿着标准/方针进行"),
    ("のもとで", "在某种影响或指导之下"),
    ("向けだ", "面向某类对象"),
    ("次第だ", "根据前项决定后项"),
    ("次第では", "根据前项变化，结果也会变化"),
    ("につけて", "每当……就……"),
    ("というか", "与其说A不如说B"),
    ("といった", "列举同类事物"),
    ("を問わず", "不问条件一律成立"),
    ("にかかわらず", "不受前项影响"),
    ("にかかわりなく", "不受前项影响"),
    ("もかまわず", "不顾前项继续"),
    ("はともかく", "前项先搁置，后项更重要"),
)


def pick_variant(*parts: str, size: int = 3) -> int:
    return sum(ord(ch) for part in parts for ch in part) % size


def rewrite_generic(old: str, verdict: str, opt_text: str, stem: str, pattern: str, rule: str) -> str:
    hint = next((h for p, h in PATTERN_HINTS if p in pattern), "")
    generic_markers = (
        "不合本语法点或语境",
        "这个选项没有把题干想要的关系讲完整",
        "语感不合",
        "语义或用法不当",
        "代入后要么接续不当",
        "表面上像能放进去",
        "句子里看不到那种动作刚落地",
        "句意一读就松",
        "逻辑并不合拍",
        "没有抓住",
        "真正强调的语感",
        "要求的语感不合",
        "代入后只是一般陈述",
        "不如正确项自然",
        "没有建立",
        "没有体现",
        "没有形成",
        "只是把词面接上了",
        "没把句子的骨架接稳",
    )
    if not any(m in old for m in generic_markers):
        return old
    base = f"「{opt_text}」"
    if verdict == "correct":
        return f"{base}放进题干后，接续和语义都能闭合，正好贴合「{pattern}」强调的{hint or '语感'}。规则摘要可见：{rule[:70]}。"
    if "每种情况" in pattern or "であれ" in pattern or "であろうと" in pattern:
        return f"{base}只是单一陈述，没能写出“无论哪一种情况都成立”的并列共通关系，所以与「{pattern}」不合。"
    if "といい" in pattern:
        return f"{base}更像普通事实或条件说明，没有把同一对象的两个侧面并列评价出来，所以不合「{pattern}」的用法。"
    if "といわず" in pattern:
        return f"{base}没有形成“从这里到那里都……”的全面覆盖感，范围还停留在局部，所以不合「{pattern}」。"
    if "いかん" in pattern:
        return f"{base}没有体现“结果取决于前项条件”的可变关系，而是单纯陈述事实，所以不合「{pattern}」。"
    if "をものともせず" in pattern:
        return f"{base}不是障碍、逆境或困难本身，无法承接“顶着困难也不在乎”的反向克服感。"
    if "をよそに" in pattern:
        return f"{base}不是可被“无视”的外部状况，句子也没有表现出“周围如何都不管”的态度。"
    if "に際して" in pattern or "にあたって" in pattern:
        return f"{base}没有把动作放在“正式时点/开始前夕”这个场景里，因而不够像「{pattern}」的典型语境。"
    if "たとたん" in pattern or "かないかのうちに" in pattern:
        return f"{base}没有把两个动作压到几乎无间隔地连起来，所以缺少「{pattern}」要求的瞬时连发感。"
    if "最中" in pattern:
        return f"{base}不是“进行中的当下”本身，无法和正在发生的动作同步，所以不合「{pattern}」。"
    if "うちに" in pattern:
        return f"{base}没有体现“趁状态尚未改变时先做”的时间窗口感，所以不合「{pattern}」。"
    if "ばかりだ" in pattern or "一方だ" in pattern:
        return f"{base}没有呈现单向推进或单向恶化的趋势，只是静态描述，因此不合「{pattern}」。"
    if "上（に）" in pattern:
        return f"{base}没有在原有基础上再叠加一层结果，少了“既……又……”的累加味道。"
    if "に応じて" in pattern or "につれて" in pattern or "に伴って" in pattern:
        return f"{base}没有写出“随着前项变化而变化”的联动关系，只是单独事件，所以不合「{pattern}」。"
    if "に関して" in pattern:
        return f"{base}不是在说明“关于某事”的话题范围，因此和「{pattern}」的讨论对象不一致。"
    if "によって" in pattern:
        return f"{base}没有落在「原因 / 手段 / 被动来源」这些典型功能上，所以语法角色不对。"
    if "につき" in pattern:
        return f"{base}没有形成正式通知里“由于……所以……”的书面说明口气，因此不合「{pattern}」。"
    if "際" in pattern:
        return f"{base}没有把动作放到“某个特定时点/场合”里来讲，只是普通陈述，因此不合「{pattern}」的场景限定。"
    if "ようとしている" in pattern:
        return f"{base}没有表现“动作正要发生”的临界感，只是一般结果或状态，所以不够像「{pattern}」。"
    if "つつ" in pattern:
        return f"{base}没有同时保留两个动作并行推进的感觉，只是单线叙述，因此不合「{pattern}」的同步感。"
    if "上（で）" in pattern:
        return f"{base}没有建立“先做前项，再以此为前提往下走”的步骤关系，所以不合「{pattern}」。"
    if "以来" in pattern:
        return f"{base}没有把时间轴拉成“从某时点开始一路持续到现在”的长线，所以不合「{pattern}」。"
    if "にかけては" in pattern:
        return f"{base}没有突出“在某一方面特别拿手/特别强”的评价重心，因此不合「{pattern}」。"
    if "に限る" in pattern:
        return f"{base}没有表现“在这种条件下最合适/最值得选”的限定判断，所以不合「{pattern}」。"
    if "限り" in pattern:
        return f"{base}没有把条件范围限定住，句意也不是“只要在这个范围内就……”的结构，所以不合「{pattern}」。"
    if "に限らず" in pattern:
        return f"{base}没有把范围从一个对象扩展到更多对象，因此不合「{pattern}」的不局限感。"
    if "のみならず" in pattern:
        return f"{base}没有形成“前项不用说，后项也同样成立”的并列推进，因此不合「{pattern}」。"
    if "ばかりか" in pattern:
        return f"{base}没有把程度继续往上推，无法读出“岂止前项，连后项都……”的升级感。"
    if "はもとより" in pattern:
        return f"{base}没有让前后项目形成“前项更不用说，后项也包含在内”的层级包容关系。"
    if "をめぐって" in pattern:
        return f"{base}不是在“围绕某议题展开”的话题中心，因此和「{pattern}」的讨论对象不一致。"
    if "ならいざしらず" in pattern:
        return f"{base}不是“姑且不论的前项”，也没有形成“前项先放一边、后项才是重点”的对比结构。"
    if "と思うと" in pattern or "と思ったら" in pattern:
        return f"{base}没有把两个动作压成“前项一发生，后项立刻弹出”的节拍，因此不合「{pattern}」。"
    if "てはじめて" in pattern:
        return f"{base}没有体现“做了前项之后才第一次出现后项”的发现感，所以不合「{pattern}」。"
    if "をはじめとして" in pattern:
        return f"{base}不是可以作为代表项带出同类的起点，因此不合「{pattern}」的列举展开。"
    if "を通じて" in pattern or "を通して" in pattern:
        return f"{base}没有体现“通过某种媒介”或“贯穿整个期间”的连接关系，因此不合「{pattern}」。"
    if "に対して" in pattern:
        return f"{base}没有形成“相对照 / 面向对象”的关系，句子重心也不在比较两端。"
    if "にこたえて" in pattern:
        return f"{base}没有把外界的期待、呼声或请求当作触发点，因此不合「{pattern}」的回应义。"
    if "をもとに" in pattern:
        return f"{base}没有把后项建立在“依据、基础、材料”之上，所以不合「{pattern}」。"
    if "に基づいて" in pattern:
        return f"{base}没有体现“以事实、规则或资料为依据”的姿态，所以不合「{pattern}」。"
    if "に沿って" in pattern:
        return f"{base}没有表现“顺着方针、标准或路线前进”的方向感，因此不合「{pattern}」。"
    if "のもとで" in pattern:
        return f"{base}不是在“某种影响/指导之下”发生的动作，所以不合「{pattern}」。"
    if "向けだ" in pattern:
        return f"{base}没有把对象限定成“面向某类人或用途”，因此不合「{pattern}」。"
    if "次第だ" in pattern or "次第では" in pattern:
        return f"{base}没有形成“前项一变，后项就随之决定”的条件链，因此不合「{pattern}」。"
    if "につけて" in pattern:
        return f"{base}没有呈现“每当某个契机出现就自然引发后项”的联动，所以不合「{pattern}」。"
    if "というか" in pattern:
        return f"{base}没有把两个说法做出“与其说A不如说B”的修正关系，因此不合「{pattern}」。"
    if "といった" in pattern:
        return f"{base}不是用来带出同类例子的代表项，因此不合「{pattern}」的列举功能。"
    if "を問わず" in pattern:
        return f"{base}没有形成“不问条件一律适用”的全面包容感，所以不合「{pattern}」。"
    if "にかかわ" in pattern:
        return f"{base}没有表现“即使前项变化，后项也不受影响”的独立性，因此不合「{pattern}」。"
    if "もかまわず" in pattern:
        return f"{base}没有体现“顾不上前项仍继续进行”的逆向推进，因此不合「{pattern}」。"
    if "はともかく" in pattern:
        return f"{base}没有把前项先搁置、把后项当重点来讲，所以不合「{pattern}」。"
    if "において" in pattern or "における" in pattern:
        return f"{base}没有落在“在某个场所、领域或时点”这一正式场景里，因此不合「{pattern}」。"
    if "とは" in pattern:
        return f"{base}没有进入“给前项下定义/作解释”的框架，只是把词语碰上了，因此不合「{pattern}」。"
    if "といえば" in pattern:
        return f"{base}没有顺着关键词把联想和话题自然带出来，只停在表层关联上，因此不合「{pattern}」。"
    if "となると" in pattern:
        return f"{base}没有体现“条件一换，判断也跟着转向”的转折感，只是在陈述普通事实，因此不合「{pattern}」。"
    if "ものなら" in pattern or "ようものなら" in pattern:
        return f"{base}没有把前项推成假设极端场景，所以读不出“如果……就……”那种夸张反应，因此不合「{pattern}」。"
    if "ないことには" in pattern:
        return f"{base}没有把前项摆成必须先满足的门槛，所以后项的成立条件没有立住，因此不合「{pattern}」。"
    if "おかげで" in pattern or "せいで" in pattern:
        return f"{base}没有把结果明确归到“多亏了……”或“都怪……”的因果方向上，因此不合「{pattern}」。"
    if "というものではない" in pattern or "わけではない" in pattern:
        return f"{base}没有把话说成“并非绝对如此”的保留判断，语气还是偏硬，因此不合「{pattern}」。"
    if "ものか" in pattern:
        return f"{base}没有撑起那种带情绪的强烈否定反问，只剩一般否定，因此不合「{pattern}」。"
    if "ものの" in pattern or "ながら" in pattern:
        return f"{base}没有先让步、再把后项转回真正结论，所以不合「{pattern}」的转折味。"
    return f"{base}只是把词面接上了，没把「{pattern}」要的{hint or '语感'}真正扣住。"


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
    if len(old) >= MIN_LEN and not any(
        m in old
        for m in (
            "不合本语法点或语境",
            "这个选项没有把题干想要的关系讲完整",
            "语感不合",
            "语义或用法不当",
            "代入后要么接续不当",
        )
    ):
        return re.sub(r"([。！？])\1+", r"\1", old)
    hint = next((h for p, h in PATTERN_HINTS if p in pattern), "")
    idx = pick_variant(verdict, letter, opt_text, stem, pattern)
    if verdict == "correct":
        templates = [
            f"「{opt_text}」填入「{stem}」后，语义与接续都能成立，特别是贴合「{pattern}」强调的{hint or '语感'}。结合规则摘要：{rule[:80]}。因此选 {letter}。",
            f"把「{opt_text}」放进题干后，整句的逻辑顺畅闭合，和「{pattern}」的{hint or '语感'}非常一致。规则摘要也支持这一判断：{rule[:80]}。因此选 {letter}。",
            f"这一项代入后，不但接续没问题，句子表达的重点也正好落在「{pattern}」所要的{hint or '语感'}上。结合规则摘要：{rule[:80]}。因此选 {letter}。",
        ]
        return templates[idx]
    reason = rewrite_generic(old or "语义或用法不当", verdict, opt_text, stem, pattern, rule)
    templates = [
        f"「{opt_text}」代入题干后，与「{pattern}」要求的{hint or '语感'}不合：{reason}。故不选 {letter}。",
        f"如果把「{opt_text}」放回原句，题干想表达的{hint or '语感'}就断了：{reason}。所以不能选 {letter}。",
        f"这一项虽然看起来相近，但和「{pattern}」真正强调的{hint or '语感'}对不上：{reason}。故排除 {letter}。",
    ]
    return templates[idx]


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
                od["reason"] = re.sub(r"\s+", " ", od["reason"]).strip()
                od["reason"] = re.sub(r"([。！？])\1+", r"\1", od["reason"])
                n += 1
    ANALYSIS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Expanded {n} short reasons -> {ANALYSIS.name}")


if __name__ == "__main__":
    main()
