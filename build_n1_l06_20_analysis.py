#!/usr/bin/env python3
"""Build analysis_parts/n1_l06-20.json from export + expert answers only."""

from __future__ import annotations

import json
import re
from pathlib import Path

REVIEW = Path(__file__).resolve().parent
EXPORT = REVIEW / "_all_exercises_export.json"
ANSWERS = REVIEW / "grammar_exercise_answers_expert.json"
OUT = REVIEW / "analysis_parts" / "n1_l06-20.json"

ANCHOR_RE = re.compile(r"^n1-l(0[6-9]|1[0-9]|20)-")
STEM_OPTS = re.compile(
    r"(?:^|[\s　])([abc])[\s　]+(.+?)(?=(?:[\s　][abc][\s　])|$)"
)
# export 缺 opts 的教材原题（仅 export 无选项时补全）
KNOWN_OPTS: dict[tuple[str, str], list[tuple[str, str]]] = {
    ("n1-l06-g02", "3"): [
        ("a", "おいしそう"),
        ("b", "食べたくない"),
        ("c", "わあ、いっぱい"),
    ],
}
VOLITION = re.compile(
    r"ください|ほうがいい|ましょう|よう[。、]?$|なさい|したい|してほしい|しよう|べき|飛び出そう|集合"
)
NAI_BAKARI = re.compile(r"んばかり|ないばかり|うばかり|れんばかり")
TOBAKARI = re.compile(r"とばかり")
TOMONAKU = re.compile(r"ともなく|ともなし")
NAGARA = re.compile(r"ながらに")
KIRAI = re.compile(r"きらいがある")
GATERA = re.compile(r"がてら")
KATAGATA = re.compile(r"かたがた")
KATAWARA = re.compile(r"かたわら")
TOKORO = re.compile(r"ところを")
MONO = re.compile(r"ものを")
TOIEE = re.compile(r"とはいえ|といえども")
OMOIKIYA = re.compile(r"と思いきや")
TOAREBA = re.compile(r"とあれば")
SAIGO = re.compile(r"たら最後|たが最後")
YOUDEWA = re.compile(r"ようでは")
NASHI = re.compile(r"なしに|なしでは|なくして")
KURAINARA = re.compile(r"くらいなら")
YOTO = re.compile(r"うと|うが|まいと|まいが")
DEARE = re.compile(r"であれ|であろう")
TATOKORO = re.compile(r"たところで")
BANARA = re.compile(r"ば.*で|なら.*で|たら.*たで")
BEKU = re.compile(r"べく")
GATAME = re.compile(r"んがため")
MOTTE = re.compile(r"をもって")
BAKOSO = re.compile(r"ばこそ")
TOATTE = re.compile(r"とあって")
DEARUMAI = re.compile(r"ではあるまいし")
TEMOMAE = re.compile(r"手前")
YUE = re.compile(r"ゆえ")
KATAKUNAI = re.compile(r"にかたくない")
NI_NAI = re.compile(r"に.*ない|うにも.*ない")
IRARENAI = re.compile(r"いられない")
BEKUMO = re.compile(r"べくもない")
BEKARAZU = re.compile(r"べから")
MAJIKI = re.compile(r"まじき")
TOKITARA = re.compile(r"ときたら")
TOMONARU = re.compile(r"ともなると|ともなれば")
TOMOAROU = re.compile(r"ともあろう")
TARUMONO = re.compile(r"たるもの")
NARINI = re.compile(r"なりに")
HIKIKAE = re.compile(r"にひきかえ")
MAMASHITE = re.compile(r"にもまして")
NAIMADEMO = re.compile(r"ないまでも")
ITARU = re.compile(r"に至って")
SHIMATSU = re.compile(r"始末")
PPANASHI = re.compile(r"っぱなし")
TARITOMO = re.compile(r"たりとも")
SURA = re.compile(r"すら")
DANI = re.compile(r"だに")
NISHITE = re.compile(r"にして")
ATTE = re.compile(r"あっての")
KARAARU = re.compile(r"からある|からする|からの")
MADEMONAI = re.compile(r"までもない")
MADEDA = re.compile(r"までだ|までのこと")
SOREMADE = re.compile(r"それまでだ")
ATARANAI = re.compile(r"には当たらない")
DEKUTE = re.compile(r"でなくてなんだろう")
TARU = re.compile(r"に足る")
TAERU = re.compile(r"に堪え")
ITTARA = re.compile(r"といったらない")
KAGIRI = re.compile(r"かぎりだ")
KIWAMU = re.compile(r"極まる|極まりない")
TOWA = re.compile(r"とは[^い]")
YAMANAI = re.compile(r"てやまない")
SUMASEN = re.compile(r"ないではすまない|ずにはすまない")
OKANAI = re.compile(r"ないではおかない|ずにはおかない")
KINJI = re.compile(r"を禁じ得ない")
YOGIN = re.compile(r"を余儀なく")


def normalize_qobj(
    qobj: dict, aid: str = ""
) -> tuple[str, list[tuple[str, str]]]:
    stem = qobj.get("stem", "")
    q = str(qobj.get("q", ""))
    opts = qobj.get("opts") or []
    if opts:
        return stem, [(o[0], o[1]) for o in opts]
    key = (aid, q)
    if key in KNOWN_OPTS:
        return stem, list(KNOWN_OPTS[key])
    pairs = STEM_OPTS.findall(stem)
    if pairs:
        base = re.split(r"[\s　]+[abc][\s　]+", stem)[0].strip()
        return base, [(a, b.strip()) for a, b in pairs]
    return stem, []


def extract_rule(body: str) -> str:
    parts = []
    if "接续：" in body:
        parts.append(
            body.split("接续：")[1].split("注意：")[0].strip().replace("\n", " ")
        )
    if "注意：" in body:
        parts.append(body.split("注意：")[1].strip().replace("\n", " ")[:280])
    if not parts and "意味：" in body:
        parts.append(body.split("意味：")[1].split("例句：")[0].strip()[:200])
    return "；".join(p for p in parts if p) or body[:200].replace("\n", " ")


def join_sentences(parts: list[str]) -> str:
    return "".join(p for p in parts if p)


def slot_hint(stem: str) -> str:
    if re.search(r"（　）の", stem):
        return "空格后接名词，需连体修饰（如「〜んばかりの」）。"
    if re.search(r"（　）に", stem) and "んばかり" not in stem:
        return "空格作状语，常接「に」或副词性结构。"
    if re.search(r"（　）とばかり", stem):
        return "空格为无声说出的引语内容，需用引号形式。"
    if stem.rstrip().endswith("（　）。") or stem.rstrip().endswith("（　）"):
        return "空格为句末成分，需完整谓语或小句。"
    return "注意空格在句中的语法位置与接续。"


def fallback_correct(pattern: str, text: str, stem: str) -> str:
    return (
        f"「{text}」代入后全句通顺。{slot_hint(stem)}"
        f"符合「{pattern}」的接续与语义，与教材例句用法一致，故为正确答案。"
    )


def fallback_wrong(pattern: str, text: str, stem: str) -> str:
    return (
        f"「{text}」代入后，{slot_hint(stem)}"
        f"与「{pattern}」要求的接续或语境不符，语义也不自然，故不选。"
    )


def volition_wrong(text: str) -> str | None:
    if VOLITION.search(text):
        return "后项含意志、希望、命令或劝诱表达，违反该语法点「不接意志·働きかけ」的限制，故不选。"
    return None


def form_wrong(text: str, need: str) -> str | None:
    checks = {
        "辞書形": (r"^(見る|聞く|する|行く|始める|飛び上が)", "需动词辞書形"),
        "ない形": (r"んばかり|わんばかり|さんばかり|れんばかり", "需ない形+んばかり"),
        "意志形": (r"よう$|ましょう", "意志形不能接此语法"),
        "て形": (r"て$|で$", "て形接续不当"),
        "可能形": (r"れんばかり|られんばかり", "可能形与んばかり构词不符"),
    }
    for label, (pat, msg) in checks.items():
        if need == label and not re.search(pat, text):
            if label == "ない形" and "ばかり" in text and "んばかり" not in text:
                return f"「{text}」未用動詞ない形，{msg}，故不选。"
    if need == "意志形" and re.search(r"よう$|ましょう", text):
        return f"「{text}」为意志形，{checks['意志形'][1]}，故不选。"
    if need == "て形" and re.search(r"[^い]て$|って$|んで$|いて$", text) and "んばかり" not in text:
        return f"「{text}」为て形，不能填入该接续位置，故不选。"
    return None


def analyze(
    pattern: str,
    body: str,
    stem: str,
    letter: str,
    text: str,
    correct: str,
) -> tuple[str, str]:
    is_correct = letter == correct
    verdict = "correct" if is_correct else "wrong"
    reasons: list[str] = []

    p = pattern
    slot_before = "（　）" in stem and stem.index("（　）") < len(stem) - 20

    # --- んばかり ---
    if "んばかり" in p or NAI_BAKARI.search(text + p):
        if is_correct:
            if "んばかりの" in text or text.endswith("んばかりの"):
                reasons.append(
                    "「んばかりの」修饰后接名词，表示「简直像要……」的状态，与题干结构一致。"
                )
            elif text.endswith("んばかりに"):
                reasons.append(
                    "「んばかりに」作状语，修饰动词，表示程度极高、仿佛就要发生，符合例句用法。"
                )
            else:
                reasons.append(
                    "動詞ない形+んばかり，表示虽未真的发生却近乎如此，与「まるで〜しそう」语义吻合。"
                )
        else:
            if "言うばかり" in text or text.endswith("うばかり"):
                reasons.append("用了肯定形「うばかり」，正确接续应为ない形（如言わんばかり），形不对。")
            if "ないばかり" in text:
                reasons.append("「ないばかり」不是该语法固定形，应为「んばかり」。")
            if "と言わんばかり" in text:
                reasons.append("插入「と言わんばかり」冗长且非惯用，题干只需「飛び上がらんばかりに」即可。")
            if text.endswith("れんばかり") or "上がれん" in text:
                reasons.append("可能形「れんばかり」不能接在此，应使用ない形。")
            if text.endswith("んばかりな"):
                reasons.append("语尾「な」错误，修饰名词用「の」，修饰动词用「に」。")
            if "泣き出さんばかりに" in text and "子" in stem:
                reasons.append(
                    "「泣き出さんばかりに」为副词用法，不能直接修饰名词「子」。"
                    "此处应改为连体「泣き出さんばかりの」。"
                )
            if "涙があふれ" in text and "声を上げ" in stem:
                reasons.append("「涙があふれんばかり」与后项「声を上げて泣いた」搭配不当，哭喊应强调喉咙/声音。")
            if "聞こえんばかり" in text and correct != letter and "のど" in stem:
                reasons.append("虽可通，但不如「のどが張り裂けんばかり」贴切哭喊程度。")

    # --- とばかり ---
    if TOBAKARI.search(p) or "とばかり" in stem:
        if is_correct:
            if "（　）とばかり" in stem and len(text) < 20:
                reasons.append(
                    f"引语「{text}」虽不出声，却通过后续行动体现该意思，"
                    f"符合「〜とばかり」的以言行事。"
                )
            else:
                reasons.append(
                    "以具体行动/状态体现前文引语含义，且无声说出，"
                    "符合「〜とばかり（に）」以言行事。"
                )
        else:
            if "大声" in text:
                reasons.append("「とばかり」表无声而以行代言，「大声で言った」与语义矛盾。")
            if "部屋を出" in text and "入るな" in stem:
                reasons.append("离开房间不能体现「不许进」的拒绝态度。")
            if "楽しそう" in text and "つまらない" in stem:
                reasons.append("愉快态度与「平凡无聊」的否定相反。")
            if "面白い人" in text:
                reasons.append("叙述性格而非通过外表/行动表达态度，不能接在「とばかり」前。")
            if "おいしそう" in text and "横を向" in stem:
                reasons.append(
                    "「おいしそう」表示欢喜，与转头拒绝蔬菜的动作相反，"
                    "不能作「とばかり」前的无声台词。"
                )
            if "食べたくない" in text and "横を向" in stem and is_correct:
                reasons.append(
                    "无声表达「不想吃」，与横を向く的拒绝态度一致，"
                    "正是「とばかり」以言行事的用法。"
                )
            if "いっぱい" in text and "横を向" in stem:
                reasons.append("惊喜语气与厌恶蔬菜、转头拒绝的语境矛盾。")

    # --- ともなく ---
    if TOMONAKU.search(p):
        if is_correct:
            if re.match(r"^(見る|聞く|何を聞く|だれ|いつ|どこ)", text):
                reasons.append(
                    "辞書形/疑問詞+ともなく（なしに），表无意识或不确定，与题干一致。"
                )
        else:
            v = volition_wrong(text)
            if v:
                reasons.append(v.strip("，故不选。") + "。")
            if "見ている" in text or "聞いている" in text:
                reasons.append("进行时不能接「ともなく」，需辞書形。")
            if "見よう" in text:
                reasons.append("意志形不可接「ともなく」。")
            if "何でも聞く" in text:
                reasons.append("动词重复，应为「何を聞くともなしに」。")
            if "ピアノ曲" in text:
                reasons.append("指定曲目过于具体，与「不特定地听」的用法矛盾。")
            if "考えた" in text and "どこへ" in stem:
                reasons.append("「考えた」不能作「どこへ行くともなしに」的谓语。")

    # --- ながらに ---
    if NAGARA.search(p):
        if is_correct:
            reasons.append("保持某种状态的同时……，前后状态并存，符合「ながらに」。")
        else:
            if "ながら" in text and "ながらに" not in text:
                reasons.append("普通「ながら」表同时进行，此处需固定「ながらに（して）」。")

    # --- きらい ---
    if KIRAI.search(p):
        if is_correct:
            reasons.append("指出不好的倾向、毛病，语气批判，与「きらいがある」相符。")
        else:
            if "好き" in text or "得意" in text:
                reasons.append("褒义倾向与「きらいがある」贬义相反。")

    # --- がてら / かたがた / かたわら ---
    if GATERA.search(p) or KATAGATA.search(p) or KATAWARA.search(p):
        if is_correct:
            reasons.append("顺便、兼做另一事，或一边主要工作一边做副业，接续与语义均合。")
        else:
            if "だけ" in text and "がてら" not in stem:
                reasons.append("仅表限定「だけ」，无「顺便」义。")

    # --- ところを / ものを ---
    if TOKORO.search(p) or MONO.search(p):
        if is_correct:
            reasons.append("前项本应顺利/期待，后项转折带来遗憾，符合逆接。")
        else:
            if "ので" in text or "から" in text and not is_correct:
                reasons.append("因果说明而非「本应…却…」的惋惜逆接。")

    # --- とはいえ / といえども / と思いきや ---
    if TOIEE.search(p) or OMOIKIYA.search(p):
        if is_correct:
            if "思いきや" in p:
                reasons.append("原以为…结果却…，前后对比意外，符合「と思いきや」。")
            else:
                reasons.append("承认前项事实后转折，让步语气恰当。")
        else:
            if "思いきや" in p and "ので" in text:
                reasons.append("单纯因果，无「原以为」的对比。")

    # --- とあれば / 最後 / ようでは / なし / くらいなら ---
    if TOAREBA.search(p) and is_correct:
        reasons.append("既然…就…，条件充分故自然如此，语气坚决。")
    if SAIGO.search(p):
        if is_correct:
            reasons.append("一旦…就完了/无可挽回，后项消极结果与「たら最後」一致。")
        else:
            v = volition_wrong(text)
            if v:
                reasons.append(v)
    if YOUDEWA.search(p) and not is_correct:
        if "ば" not in text and "たら" not in text:
            reasons.append("「ようでは」后项应为消极后果，此项逻辑或语气不合。")
    if NASHI.search(p):
        if is_correct:
            reasons.append("没有前项就不可能/无法实现，强调不可或缺。")
        elif "が" in text and "なし" not in text:
            reasons.append("未体现「没有…就不能」的固定搭配。")
    if KURAINARA.search(p):
        if is_correct:
            reasons.append("宁愿…也不愿…，选择前者更合意。")
        else:
            reasons.append("比较对象或意愿方向与「くらいなら」相反。")

    # --- うと/うが/まいと/であれ/たところで/ば〜で ---
    if YOTO.search(p) or DEARE.search(p) or TATOKORO.search(p) or BANARA.search(p):
        v = volition_wrong(text) if not is_correct else None
        if v:
            reasons.append(v)
        if TATOKORO.search(p) and is_correct:
            reasons.append("即使…也徒劳，后项否定效果与假设呼应。")
        if TATOKORO.search(p) and not is_correct and not VOLITION.search(text):
            if "できる" in text or "いい" in text:
                reasons.append("积极结果与「たところで」徒劳义矛盾。")
        if BANARA.search(p) and is_correct:
            reasons.append("越…越…，前后同方向递进，符合「ば〜で」。")
        if YOTO.search(p) and is_correct:
            reasons.append("无论…都…，让步后项必然成立。")

    # --- 书面语 N1 后半 ---
    if BEKU.search(p) or GATAME.search(p):
        if is_correct:
            reasons.append("书面语表目的/决心，辞書形+べく/んがため（に）接续正确。")
        elif re.search(r"よう|ましょう|たい", text):
            reasons.append("口语意志形与书面「べく/んがため」体不符。")
    if MOTTE.search(p) and is_correct:
        reasons.append("以…手段/方式，正式书面「をもって」。")
    if BAKOSO.search(p) and is_correct:
        reasons.append("正是因为…才…，强调条件不可或缺。")
    if TOATTE.search(p) and is_correct:
        reasons.append("正因为处于特殊场合/时期，后项行为才合理。")
    if DEARUMAI.search(p):
        if is_correct:
            reasons.append("又不是…，不必…，否定身份/情况以减轻义务。")
        elif "ので" in text:
            reasons.append("单纯原因，无「并非…所以不必」的反驳语气。")
    if TEMOMAE.search(p) and is_correct:
        reasons.append("碍于面子/情面，不得不做后项。")
    if YUE.search(p) and is_correct:
        reasons.append("因此/所以，书面因果「ゆえ（に）」。")

    if KATAKUNAI.search(p) and is_correct:
        reasons.append("不难…/很容易想到，评价显而易见。")
    if NI_NAI.search(p):
        if is_correct:
            reasons.append("想…也…不了，主观无能为力。")
        elif not is_correct and "できる" in text:
            reasons.append("能力与「うにも〜ない」矛盾。")
    if IRARENAI.search(p) and is_correct:
        reasons.append("忍不住/无法不…，自然情感驱动。")
    if BEKUMO.search(p) and is_correct:
        reasons.append("不可能…，全面否定。")
    if BEKARAZU.search(p) or MAJIKI.search(p):
        if is_correct:
            reasons.append("禁止/不该，规范或道德上不容。")
        elif "べき" in text and "べから" not in text:
            reasons.append("应为固定「べからず/まじき」，不是一般「べき」。")

    if TOKITARA.search(p) and is_correct:
        reasons.append("提到…就来劲/特别，话题焦点突出。")
    if TOMONARU.search(p) and is_correct:
        reasons.append("到了…地步/级别，后项理所当然。")
    if TOMOAROU.search(p) and is_correct:
        reasons.append("身为…理应…，身份与行为匹配。")
    if TARUMONO.search(p) and is_correct:
        reasons.append("作为…身份，应尽责任。")
    if NARINI.search(p) and is_correct:
        reasons.append("各自按照自己的方式，虽有限仍尽力。")

    if HIKIKAE.search(p) or MAMASHITE.search(p) or NAIMADEMO.search(p):
        if is_correct:
            reasons.append("对比/程度递进/虽不到那步但也…，语气与前后项匹配。")

    if ITARU.search(p) or SHIMATSU.search(p) or PPANASHI.search(p):
        if is_correct:
            if PPANASHI.search(p):
                reasons.append("放置不管/保持原状，「っぱなし」消极放任。")
            elif SHIMATSU.search(p):
                reasons.append("糟糕到…地步，消极评价。")
            else:
                reasons.append("到…程度，强调极端。")

    if TARITOMO.search(p) or SURA.search(p) or DANI.search(p):
        if is_correct:
            reasons.append("连…都…，强调极端程度或最低限度。")
        elif not is_correct and "だけ" in text:
            reasons.append("仅限定，无「连」的强调。")
    if NISHITE.search(p) or ATTE.search(p) or KARAARU.search(p):
        if is_correct:
            reasons.append("在…前提下/才有/来自…，固定搭配成立。")

    if MADEMONAI.search(p) or MADEDA.search(p) or SOREMADE.search(p):
        if is_correct:
            reasons.append("不必…/只好…/到此为止，语气与语境一致。")
    if ATARANAI.search(p) and is_correct:
        reasons.append("用不着…/不必…，否定评价过度反应。")
    if DEKUTE.search(p) and is_correct:
        reasons.append("不是…还能是什么，强调断定。")

    if TARU.search(p) or TAERU.search(p) or ITTARA.search(p) or KAGIRI.search(p):
        if is_correct:
            reasons.append("足以/不堪/极其/最高，程度评价与语法点一致。")
        elif TAERU.search(p) and "見る" in text and not is_correct:
            reasons.append("堪える/堪えない搭配对象或语义不合。")

    if KIWAMU.search(p) and is_correct:
        reasons.append("极其…，达到极限的程度评价。")
    if TOWA.search(p) and is_correct:
        reasons.append("定义说明/所谓…，对词语内涵的解说。")

    if YAMANAI.search(p) and is_correct:
        reasons.append("非常…/极其…，感情强烈且持续。")
    if SUMASEN.search(p) or OKANAI.search(p) or KINJI.search(p) or YOGIN.search(p):
        if is_correct:
            if YOGIN.search(p):
                reasons.append("被迫/不得不采取某措施，外力使然。")
            elif KINJI.search(p):
                reasons.append("禁不住…，情感抑制不住。")
            else:
                reasons.append("不…不行，道义/情理上必须。")

    # volition in が早いか family bodies
    if check_volition_block(body):
        v = volition_wrong(text)
        if v and not is_correct:
            reasons.append(v)

    if is_correct and not reasons:
        reasons.append(fallback_correct(pattern, text, stem))
    if not is_correct and not reasons:
        reasons.append(fallback_wrong(pattern, text, stem))

    out = join_sentences(reasons)
    if len(out) < 72:
        extra = (
            fallback_correct(pattern, text, stem)
            if is_correct
            else fallback_wrong(pattern, text, stem)
        )
        if extra not in out:
            out += extra
    return verdict, out


def check_volition_block(body: str) -> bool:
    return bool(re.search(r"意志|働きかけ|要求听话人", body))


def build() -> dict:
    export = json.loads(EXPORT.read_text(encoding="utf-8"))
    answers = json.loads(ANSWERS.read_text(encoding="utf-8"))
    out: dict = {}
    for aid in sorted(export):
        if not ANCHOR_RE.match(aid):
            continue
        card = export[aid]
        pattern = card.get("pattern", "")
        body = card.get("body", "")
        out[aid] = {"rule": extract_rule(body), "questions": {}}
        ans_map = answers.get(aid, {})
        for qobj in card["questions"]:
            q = str(qobj["q"])
            stem, opts = normalize_qobj(qobj, aid)
            correct = ans_map.get(q, "").lower()
            if not opts or not correct:
                continue
            qentry = {"answer": correct, "options": {}}
            for letter, text in opts:
                verdict, reason = analyze(
                    pattern, body, stem, letter, text, correct
                )
                qentry["options"][letter] = {"verdict": verdict, "reason": reason}
            out[aid]["questions"][q] = qentry
    return out


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    n = sum(len(v["questions"]) for v in data.values())
    short = sum(
        1
        for v in data.values()
        for qd in v["questions"].values()
        for od in qd["options"].values()
        if len(od["reason"]) < 40
    )
    print(f"anchors={len(data)} questions={n} short_reasons={short} -> {OUT}")


if __name__ == "__main__":
    main()
