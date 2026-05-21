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
PATTERN_KEYS = (
    ("が早いか", "immediate"),
    ("や否や", "immediate"),
    ("や、", "immediate"),
    ("なり", "immediate"),
    ("そばから", "repeat"),
    ("てからというもの", "continuation"),
    ("にあって", "special_circumstance"),
    ("べく", "purpose"),
    ("んがため", "purpose"),
    ("をもって", "means"),
    ("ばこそ", "causal_emphasis"),
    ("とあって", "special_cause"),
    ("ならでは", "uniqueness"),
    ("にとどまらず", "scope_expand"),
    ("はおろか", "hierarchy"),
    ("もさることながら", "hierarchy"),
    ("（よ）うとしている", "intention"),
    ("ようとしている", "intention"),
    ("次第", "immediate_condition"),
    ("てからでないと", "prereq"),
    ("てからでなければ", "prereq"),
    ("からして", "basis_impression"),
    ("にわたって", "span"),
    ("にわたる", "span"),
    ("だけ", "limit_only"),
    ("はさておき", "aside"),
    ("わけがない", "impossible"),
    ("どころではない", "far_from"),
    ("どころか", "far_from"),
    ("というものではない", "not_absolute"),
    ("わけではない", "not_absolute"),
    ("ものか", "strong_negation"),
    ("において", "place_time_field"),
    ("における", "place_time_field"),
    ("に対して", "contrast_object"),
    ("にこたえて", "response"),
    ("に基づいて", "basis"),
    ("に沿って", "along"),
    ("のもとで", "under"),
    ("ものの", "concession"),
    ("ながら（も）", "concession"),
    ("ながらも", "concession"),
    ("といっても", "qualification"),
    ("からといって", "no_direct_reason"),
    ("ないことには", "prereq_neg"),
    ("おかげだ", "gratitude"),
    ("おかげで", "gratitude"),
    ("せいだ", "blame"),
    ("せいで", "blame"),
    ("にしても", "either_way"),
    ("にしろ", "either_way"),
    ("にせよ", "either_way"),
    ("としても", "even_if"),
    ("ことだし", "reason_to_act"),
    ("ことだから", "reason_to_expect"),
    ("を抜きにしては", "indispensable"),
    ("とは", "definition"),
    ("といえば", "association"),
    ("となると", "turning_point"),
    ("としたら", "assumption"),
    ("とすれば", "assumption"),
    ("とすると", "assumption"),
    ("となったら", "assumption"),
    ("となれば", "assumption"),
    ("にもかかわらず", "concession_strong"),
    ("ものなら", "hypothetical"),
    ("あまり", "excess"),
    ("あまりの", "excess"),
)


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


def detect_key(pattern: str, body: str) -> str:
    source = f"{pattern} {body}"
    for needle, key in PATTERN_KEYS:
        if needle in source:
            return key
    return "generic"


def pick_variant(*parts: str, size: int = 3) -> int:
    return sum(ord(ch) for part in parts for ch in part) % size


def immediate_reason(text: str, is_correct: bool) -> str:
    idx = pick_variant(text, "immediate", "ok" if is_correct else "ng")
    if is_correct:
        options = [
            "后项写成紧接着发生的事实，镜头感很强，正好符合“刚……就……”这一类语法的时间压缩效果。",
            "这里不是普通的先后顺序，而是两个动作几乎贴在一起发生，时间间隔被压到最短，这正是该语法的关键。",
            "它把“前一动作结束”和“后一动作发生”压成一个连续镜头，因此语感上就是“一……就……”的快速切换。",
        ]
        return options[idx]
    if VOLITION.search(text):
        options = [
            "这一类语法要求后项接已发生的事实，不接意志、请求或命令；此项把后项改成主观推动，语感立刻偏掉。",
            "后项一旦变成愿望、请求或命令，就不再是“已经发生的事实”，和这种语法要求的客观性冲突。",
            "该结构看重的是动作的客观连发，而不是说话人临时起意；这个选项一带主观推动，节奏就变了。",
        ]
        return options[idx]
    options = [
        "此项不是“前一动作一结束，后一动作立刻跟上”的事实叙述，紧接关系不够硬。",
        "它只是一般的前后相继，没有把“几乎同时发生”的压缩感做出来，因此不够贴合。",
        "句子里看不到那种动作刚落地、后项立刻弹出来的节奏，所以不如正确项自然。",
    ]
    return options[idx]


def repeat_reason(text: str, is_correct: bool) -> str:
    idx = pick_variant(text, "repeat", "ok" if is_correct else "ng")
    if is_correct:
        options = [
            "句子把“刚发生”与“又一次发生/立刻被重复”叠在一起，正是“そばから”那种反复、徒劳、来不及稳定下来的感觉。",
            "它抓到的是“做完马上又被打回原点”的循环感，这比单纯连续动作更能体现そばから的语气。",
            "这里的重点不是一次完成，而是完成后马上又被新的变化覆盖，所以读起来有明显的反复感。",
        ]
        return options[idx]
    options = [
        "这里需要的是“刚……又……／一做完就被反复打断”的循环感，这个选项只是在说普通动作，反复义不够。",
        "它没有表现出“刚处理完就又出状况”的循环链条，因此只能算一般动作，撑不起そばから的味道。",
        "如果没有“刚做完又马上被推翻”的感觉，就不是这个语法真正想要的重复义。",
    ]
    return options[idx]


def continuation_reason(text: str, is_correct: bool) -> str:
    idx = pick_variant(text, "continuation", "ok" if is_correct else "ng")
    if is_correct:
        options = [
            "前项只是变化的起点，后项却写成持续到现在的状态，因此能自然读成“自从……之后一直……”而不是单次事件。",
            "这个句子真正强调的是“从那个时点开始，后面一直都这样”，重点在延续而不是完成一次动作。",
            "前项把状态切开一个新阶段，后项则把新阶段的影响拖到现在，这就是からというもの最典型的连续感。",
        ]
        return options[idx]
    if re.search(r"買った|始めた|した|行った|会った", text):
        options = [
            "这个选项只是一次性动作，不能承接出“之后一直如此”的持续状态。",
            "它停留在一个点状事件上，而不是把事件后的状态拉成一条长线，所以不合用。",
            "从语义上看，它更像“做过一次”，不是“从此以后持续改变”，因此落不到这个句型里。",
        ]
        return options[idx]
    options = [
        "它没有把“变化之后延续下去”的轨迹写出来，更像一个孤立结果。",
        "句子缺少“之后一直如此”的延续方向，只剩下单点发生的事实。",
        "这里看不到后项持续化的痕迹，所以不能读成从过去一路延伸到现在的状态。",
    ]
    return options[idx]


def special_circumstance_reason(text: str, is_correct: bool) -> str:
    idx = pick_variant(text, "special_circumstance", "ok" if is_correct else "ng")
    if is_correct:
        options = [
            "这里的重点不是普通场景，而是“处在某种特殊立场、局面或逆境中仍然如此”的反差感，语气因此更有戏剧性。",
            "前项先把人放进一个不寻常的境地，后项再接正常动作或结果，于是形成“在这种情况下居然还……”的效果。",
            "它把环境的特殊性摆在前面，再让后项顺势发生，所以整句会有一种“情势一变，结果也跟着变”的张力。",
        ]
        return options[idx]
    options = [
        "这个选项只是普通处境，不足以制造“在这种特殊情境下竟然还……”的反差。",
        "它没有把场景推到特殊状态，因此语气只剩一般背景说明，缺少にあって要求的反差重量。",
        "如果只是日常环境，就很难读出“特殊局面中的特别反应”，所以不够贴切。",
    ]
    return options[idx]


def purpose_reason(text: str, is_correct: bool) -> str:
    idx = pick_variant(text, "purpose", "ok" if is_correct else "ng")
    if is_correct:
        options = [
            "它把前项解释成“为了达成某个目的而采取的动作”，前后主语也保持一致，所以读起来是一个完整的目的链。",
            "句子不是在讲随便做了什么，而是在讲“带着目的去做”，这正是べく/んがため一类语法的核心。",
            "前项和后项被目的关系拴在一起，意思是“为了……所以去……”，逻辑链条是连贯的。",
        ]
        return options[idx]
    if VOLITION.search(text):
        options = [
            "后项要承接的是说话人/主语为实现目的所做的动作，而不是把结果写成请求、愿望或劝诱。",
            "这里要的是“我/他去做了什么”，不是“请你做”“希望做”这种面向他人的表达。",
            "目的句的后项必须是实现目的的行动本身，换成愿望或命令，方向就错了。",
        ]
        return options[idx]
    options = [
        "虽然看似相关，但它没有写出“为了……而去做”的目的方向。",
        "这个选项只有内容，没有目的性，读不出“为此而采取行动”的结构。",
        "它缺少主动追求目标的语气，因此和目的语法的核心不合。",
    ]
    return options[idx]


def means_reason(text: str, is_correct: bool) -> str:
    idx = pick_variant(text, "means", "ok" if is_correct else "ng")
    if is_correct:
        options = [
            "这里的「をもって」不是单纯“带着/拿着”，而是“以……为手段/凭借……”，选项正好把这种方法论意味写出来。",
            "它对应的是“拿什么来完成这件事”，所以带有明显的工具性或凭借性。",
            "句子把动作的依据和方式摆出来了，这正是「をもって」更偏书面、正式的手段义。",
        ]
        return options[idx]
    options = [
        "它把应该表达“手段、资格或凭借”的位置，换成了普通名词或事物本身，手段义不成立。",
        "这个词只是在陈述对象，并没有说“凭这个去做”，所以达不到をもって的语法功能。",
        "少了“以此作为依据/方法”的感觉，这里就不像正式的手段表达。",
    ]
    return options[idx]


def causal_emphasis_reason(text: str, is_correct: bool) -> str:
    idx = pick_variant(text, "causal_emphasis", "ok" if is_correct else "ng")
    if is_correct:
        options = [
            "这个句子不是普通因果，而是“正因为……所以……”的强调式理由，语气里带着先抬高前项、再推出后项的反转感。",
            "这里不是在平淡地说明原因，而是在把原因加粗，突出“恰恰因为如此，后面才成立”的力度。",
            "前项被强调到足以反推后项，这种“理由先被顶起来”的感觉，正是ばこその精髓。",
        ]
        return options[idx]
    options = [
        "它只是平铺直叙的原因说明，没有把“正因为如此才……”的强调效果拉出来。",
        "句子只是在交代背景，没有形成“因为这个缘故所以更显得……”的语气重心。",
        "如果没有把前项当成强理由来抬高，ばこそ的反转力就不成立。",
    ]
    return options[idx]


def special_cause_reason(text: str, is_correct: bool) -> str:
    idx = pick_variant(text, "special_cause", "ok" if is_correct else "ng")
    if is_correct:
        options = [
            "前项带有特殊场合色彩，因此后项会出现很自然、几乎带必然性的反应，这正是「とあって」最核心的语感。",
            "它先给出一个带“特别事件”色彩的条件，再让后项顺理成章发生，所以整个句子像是自然而然地推出结果。",
            "这种结构的妙处在于：不是普通原因，而是“正逢某个特别场面”，于是结果显得更理所当然。",
        ]
        return options[idx]
    options = [
        "这个选项说的是一般情况，不足以触发“因为处在特殊场合，所以出现相应反应”的语气。",
        "它没有把条件写成特殊局面，后项也就少了那种带有现场感的自然反应。",
        "如果只是普通背景，就很难读出とあって那种“情势一到，动作自动发生”的味道。",
    ]
    return options[idx]


def uniqueness_reason(text: str, is_correct: bool) -> str:
    idx = pick_variant(text, "uniqueness", "ok" if is_correct else "ng")
    if is_correct:
        options = [
            "它强调的是“只有这种东西/这种场合才有的独特风味或价值”，不是泛泛的褒义，而是专属感。",
            "这里的重点是“非它不可”，也就是只有这个对象才成立的特别之处。",
            "句子把评价落在不可替代性上，所以有明显的专属优势感，这才是ならでは。",
        ]
        return options[idx]
    options = [
        "这里缺少“只有……才有”的独占意味，换成别的事物也同样成立，就不算ならでは。",
        "如果任何对象都能成立，就只是普通褒义，不是该语法要求的独特性。",
        "它没有把对象限定成“只有这个才有的特色”，因此不够专属。",
    ]
    return options[idx]


def scope_expand_reason(text: str, is_correct: bool) -> str:
    idx = pick_variant(text, "scope_expand", "ok" if is_correct else "ng")
    if is_correct:
        options = [
            "前项只是一个起点，后项则顺势扩到更大的范围，形成“岂止……连……”式的范围推进。",
            "句子不是停在原点，而是把评价/事实从小范围一路推向更广的范围，这就是にとどまらず的骨架。",
            "它先说一个较小的范围，再把视野打开，范围越说越大，这种外扩感非常明显。",
        ]
        return options[idx]
    options = [
        "这个选项没有把范围往外推，只停留在原来的层面，和“にとどまらず”的扩展感不合。",
        "它没有从一个范围滑向另一个更大的范围，只是原地打转，因此不成立。",
        "少了“超出前项”的推进，句子就还停在局部，不像にとどまらず。",
    ]
    return options[idx]


def hierarchy_reason(text: str, is_correct: bool) -> str:
    idx = pick_variant(text, "hierarchy", "ok" if is_correct else "ng")
    if is_correct:
        options = [
            "句子用了从轻到重的层级推进，先说“不用说前者，连后者都……”，层次递进非常清楚。",
            "它把前后项目做了强弱分层，所以读起来有“连更轻的都这样，更不用说更重的了”的顺序感。",
            "这里最关键的是程度对比：前面已经很高了，后面更高，于是形成明显的层级递进。",
        ]
        return options[idx]
    options = [
        "它没有做强弱层级的对照，只是并列或一般补充，因此撑不起“岂止……更不用说……”的重量。",
        "如果只是并排罗列，而不是由轻到重推进，就读不出这类语法的层次感。",
        "少了“更不用说后者”的升级关系，句子的层级就散掉了。",
    ]
    return options[idx]


def generic_reason(text: str, pattern: str, is_correct: bool) -> str:
    idx = pick_variant(text, pattern, "generic", "ok" if is_correct else "ng")
    if is_correct:
        options = [
            "把这个词组代入后，接续、语义重心和题干逻辑都对上了，所以它不是“碰巧能放进去”，而是把句子的关系顺着接通了。",
            "它一放进去就能把题干的关系顺顺地连起来，说明这里不只是形式对了，连说话的落点也对了。",
            "从接续到语义再到句子整体走向都能闭合，所以它是最自然的答案。",
        ]
        return options[idx]
    if any(k in pattern for k in ("限", "だけ", "にわた", "に限らず", "のみならず", "ばかりか", "はおろか")):
        options = [
            "它没有把范围真正收拢或外推到题干要的边界上，读起来还是留着别的可能性。",
            "这个选项看上去相关，但范围控制不够准，句子没有被压到题干想要的那个限度。",
            "它只是把边界摆出来，没有把可选空间压成题干需要的那一种。",
        ]
        return options[idx]
    if any(k in pattern for k in ("わけ", "ものか", "ないことには", "からといって", "というものではない")):
        options = [
            "它没有把逻辑关系说到位，语气不是收回判断，就是把前提和结论连得太死。",
            "这个选项的判断方向和题干要的保留、转折或否定力度不一致。",
            "句子里缺少题干那种“先让一步，再把判断收紧”的力道。",
        ]
        return options[idx]
    if any(k in pattern for k in ("なり", "や否や", "が早いか", "たとたん", "と思うと", "と思ったら")):
        options = [
            "它没有把动作压成前后紧贴的连发节拍，时间轴还是散开的。",
            "这个选项只是在说普通先后，不足以撑起题干要的瞬时连锁感。",
            "句子的重心没有落到“前一拍刚落下，后一拍马上接上”的节奏上。",
        ]
        return options[idx]
    options = [
        "它虽然可能看起来沾边，但代入后不是接续别扭，就是语义重心偏离，不能把题干想表达的关系完整落地。",
        "表面上像能放进去，实际上句子一读就散，说明和题干要的关系并不对拍。",
        "这个选项只是把词面接上了，没把句子的骨架接稳，所以只能算干扰项。",
    ]
    return options[idx]


SPECIAL_REASON_MAP = {
    "intention": ("动作正要发生的临界感", "它不是单纯的未来预测，而是动作临近启动、已经带出“马上就要发生”的临界感。", "它要么只是普通预测，要么只是陈述结果，没有进入“动作正要发生”的门槛。"),
    "immediate_condition": ("前项一成立后项立刻触发", "这里重心在“某个前提一成立，后项就跟着触发”，不是单纯时间先后，而是条件一到立刻成立。", "这个选项没有把前项写成触发条件，因此读不出“随着状态一变，结果立刻决定”的意思。"),
    "prereq": ("先做前项才轮到后项", "它把前项当成必须先完成的前提，后项只能在此之后成立，整个逻辑是明显的门槛关系。", "它没有体现“先做完前项才轮到后项”的顺序约束。"),
    "basis_impression": ("从一处先看出整体倾向", "这里的关键不是内容本身，而是从该部分先看出整体倾向，属于“从一个切入口判断全局”的用法。", "它没有形成“从某一点先看出全貌”的评价路径。"),
    "span": ("跨越一段范围的连续覆盖", "句子把范围明确拉长，读成“跨越一段时间/区间/领域”的连续覆盖。", "它只是一个点状时间或地点，没有展开成连续的一段。"),
    "limit_only": ("只剩唯一可选范围", "这个选项把条件收得很死，只留下题干要的那一个落点，因此很贴合“只有……/仅……”的限定语气。", "它还留着别的可能性，没有把可选空间压成唯一答案。"),
    "aside": ("把次要部分先搁开", "这里先把次要部分搁开，主句转而强调更重要的内容，层次关系很清楚。", "它没有真正把前项放到一边，也没有形成“先不谈这个，先谈那个”的对照结构。"),
    "impossible": ("强烈否定，几乎封死可能", "句子把可能性直接封死，语气是强烈的否定判断，带有“绝不可能”那种断然感。", "这个选项只是能力不足或条件不足，不足以推出“绝无可能”的断言。"),
    "far_from": ("连更轻的都不是", "这里不是普通比较，而是把原本的话题拉得更远，形成“连……都不是，更不用说……”的强烈反差。", "它没有形成从轻到重、从近到远的升级。"),
    "not_absolute": ("收回绝对化判断", "它是在收回绝对化判断，意思是“并不是说一定如此”，语气有明显的保留和修正。", "它反而把保留语气说死了，和原结构想留出的余地相反。"),
    "strong_negation": ("强烈的否定反问", "这里是很强的否定反问，带有“怎么可能”的情绪，和普通否定不是一个层级。", "它只是一般否定，情绪力度不够。"),
    "place_time_field": ("场所、领域、时点框架", "它把事情放在某个场所、领域或时点上讨论，语域明显更正式、更抽象。", "它没有落到那个场所/领域/时点的框架里。"),
    "contrast_object": ("对照/对象关系", "这里明显是在把两类对象并列对照，后项与前项形成面向关系，而不是普通说明。", "它没有把对象拉成对照关系。"),
    "response": ("回应期待/要求", "句子是对外界期待、呼声或要求的回应，后项带有“顺着对方需要去做”的味道。", "它没有把外界期待当作触发点。"),
    "basis": ("依据、基础、材料", "后项明显建立在前项材料、事实或规则之上，属于“有依据地推出”的表达。", "它没有把前项当依据来推导后项。"),
    "along": ("顺着标准或路线推进", "这里是顺着既定标准或路线来推进，动作不是随便发生，而是沿着规范展开。", "它没有顺着标准或路线走。"),
    "under": ("在……之下进行", "句子强调的是在某种影响、指导或支配之下进行的行为，层级关系很明确。", "它没有体现‘在……之下’的支配/影响关系。"),
    "concession": ("前项让步后项转折", "前项先承认一个看似不利或相反的事实，后项再转出真正结论，因此有明显的“虽然……但是……”转折感。", "它没有把前项当成让步条件，后项也没有出现反转。"),
    "qualification": ("先承认后限定", "这里先承认前项成立，再补上一个限定说明，意思不是完全推翻，而是把判断收窄到更准确的范围。", "它没有做“先承认、再限定”的修正，所以语气还是太直。"),
    "no_direct_reason": ("前项不是直接理由", "句子明确在说“不能简单从前项推出后项”，所以前项只是背景，不是直接理由。", "这个选项把前项和后项直接连成因果，违反了“不能简单从A推到B”的逻辑。"),
    "gratitude": ("多亏了……", "这里是在把结果归功于某种助力，语气是正向的“多亏了……才……”。", "它没有呈现“因为帮忙而产生好结果”的感激导向。"),
    "blame": ("都怪……", "这里是在把不好的结果归咎于某种原因，语气明显带有负向的“都怪……”。", "它没有表现出“由于这个原因导致坏结果”的责难导向。"),
    "either_way": ("无论哪一边都成立", "它是在把两种备选情况并排起来，不管哪边都能得到同样的结论。", "它没有形成“无论A还是B都一样”的并列选择感。"),
    "even_if": ("即使……也……", "这里是在承认前项仍不影响后项，属于“即使如此，结果也一样”的让步。", "它没有体现让步下仍维持结论的感觉。"),
    "reason_to_act": ("既然如此那就行动", "这里是把前项当成促使行动的契机，因此后项带有“既然如此，那就……”的自然推进。", "它没有把前项变成推动行动的理由。"),
    "reason_to_expect": ("按常理会这样", "这里是借前项的特征推出后项的自然预期，属于“按常理会这样”的判断。", "它没有形成基于性格/常识的预测。"),
    "indispensable": ("离不开……", "句子强调的是把某项因素拿掉就不成立，因此它是必要条件而不是可有可无的背景。", "它没有表现“少了它就不行”的排他性。"),
    "definition": ("定义/解释", "它是在给前项做定义或解释，像是在说“所谓……就是……”。", "它没有形成定义式说明，只是一般说明。"),
    "association": ("借关键词展开联想", "句子是借一个熟悉的关键词把相关话题带出来，属于联想式展开。", "它没有围绕那个关键词展开联想，只是一般陈述。"),
    "turning_point": ("话题/条件一转折", "这里是话锋一转、条件一换，后项就跟着变化，语气有很强的条件跳转感。", "它没有形成“换了条件就换了判断”的转折点。"),
    "hypothetical": ("假设极端场景", "句子是在构造一个假设极端，暗示只要前项成立，后项就会强烈反应。", "它没有把前项设成假设场景，因此读不出那种“如果……就……”的夸张感。"),
    "excess": ("程度过头", "这里突出的是程度过度、情绪过满或数量过多，重点在“超过正常限度”。", "它没有表现“过度”或“太过”的感觉。"),
}


def special_key_reason(key: str, is_correct: bool) -> str:
    _, ok_text, ng_text = SPECIAL_REASON_MAP[key]
    return ok_text if is_correct else ng_text


GENERIC_REASON_MARKERS = (
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


def is_generic_reason(reason: str) -> bool:
    return any(m in reason for m in GENERIC_REASON_MARKERS)


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
    key = detect_key(pattern, body)

    if check_volition_block(body):
        if VOLITION.search(text):
            reasons.append("该语法点要求后项不接意志、请求或命令，此项含意志/请求表达，故不选。")
        elif is_correct:
            reasons.append("后项为客观事实或状态叙述，符合「不接意志·働きかけ」的限制。")

    if key == "immediate":
        reasons.append(immediate_reason(text, is_correct))
        if not is_correct and (text.endswith("て") or text.endswith("ている")):
            reasons.append("空格需要的是辞書形/た形的瞬间接续，て形会把动作拉成进行态，时间衔接就不对了。")
    elif key == "repeat":
        reasons.append(repeat_reason(text, is_correct))
    elif key == "continuation":
        reasons.append(continuation_reason(text, is_correct))
    elif key == "special_circumstance":
        reasons.append(special_circumstance_reason(text, is_correct))
    elif key == "purpose":
        reasons.append(purpose_reason(text, is_correct))
    elif key == "means":
        reasons.append(means_reason(text, is_correct))
    elif key == "causal_emphasis":
        reasons.append(causal_emphasis_reason(text, is_correct))
    elif key == "special_cause":
        reasons.append(special_cause_reason(text, is_correct))
    elif key == "uniqueness":
        reasons.append(uniqueness_reason(text, is_correct))
    elif key == "scope_expand":
        reasons.append(scope_expand_reason(text, is_correct))
    elif key == "hierarchy":
        reasons.append(hierarchy_reason(text, is_correct))
    elif key in SPECIAL_REASON_MAP:
        reasons.append(special_key_reason(key, is_correct))
    elif key == "concession":
        reasons.append(special_key_reason(key, is_correct))
    elif key == "qualification":
        reasons.append(special_key_reason(key, is_correct))
    elif key == "no_direct_reason":
        reasons.append(special_key_reason(key, is_correct))
    elif key == "gratitude":
        reasons.append(special_key_reason(key, is_correct))
    elif key == "blame":
        reasons.append(special_key_reason(key, is_correct))
    elif key == "definition":
        reasons.append(special_key_reason(key, is_correct))
    elif key == "association":
        reasons.append(special_key_reason(key, is_correct))
    elif key == "turning_point":
        reasons.append(special_key_reason(key, is_correct))
    elif key == "hypothetical":
        reasons.append(special_key_reason(key, is_correct))
    elif key == "excess":
        reasons.append(special_key_reason(key, is_correct))

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
        reasons.append(generic_reason(text, pattern, True))
    if not is_correct and not reasons:
        reasons.append(generic_reason(text, pattern, False))

    cleaned: list[str] = []
    for reason in reasons:
        reason = re.sub(r"\s+", " ", reason).strip()
        reason = re.sub(r"([。！？])\1+", r"\1", reason)
        if reason and reason not in cleaned:
            cleaned.append(reason)

    return verdict, " ".join(cleaned)


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
                        old_generic = is_generic_reason(old_r)
                        new_generic = is_generic_reason(new_r)
                        if (
                            old_generic
                            and not new_generic
                            and len(new_r) >= 18
                            or (not old_generic and not new_generic and len(new_r) > len(old_r))
                            or (old_generic and new_generic and len(new_r) > len(old_r))
                            or (
                                len(new_r) >= 18
                                and not new_generic
                                and "故排除" not in new_r
                                and "故不选" not in new_r
                            )
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
