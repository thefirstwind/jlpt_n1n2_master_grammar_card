#!/usr/bin/env python3
"""更新N1第2课答案"""

import json
from pathlib import Path

REVIEW_DIR = Path(__file__).resolve().parent
ANSWERS_FILE = REVIEW_DIR / "grammar_exercise_answers.json"

def update_n1_l02():
    """更新N1第2课答案"""
    
    # 加载现有答案
    if ANSWERS_FILE.exists():
        with open(ANSWERS_FILE, 'r', encoding='utf-8') as f:
            answers = json.load(f)
    else:
        answers = {}
    
    # N1第2课 语法点1: 〜を皮切りに（して）・〜を皮切りとして
    answers["n1-l02-g01"] = {
        "1": "a",  # 北海道
        "2": "c",  # いくつもの大会で好成績を残している
        "3": "b",  # みんなが次々に意見を言った
        "4": "a",  # いろいろなところで個展を開いている
        "5": "b"   # 国内、国外をあちこち旅行している
    }
    
    # N1第2课 语法点2: 〜に至るまで
    answers["n1-l02-g02"] = {
        "1": "c",  # 恋愛の悩み
        "2": "a",  # ベッドからスプーン
        "3": "b"   # その日の朝、昼、晩の気温
    }
    
    # N1第2课 语法点3: 〜を限りに
    answers["n1-l02-g03"] = {
        "1": "a",  # 今月
        "2": "b",  # この会社を辞めます
        "3": "c"   # 生徒を募集しない
    }
    
    # N1第2课 语法点4: 〜をもって
    answers["n1-l02-g04"] = {
        "1": "a",  # 以上
        "2": "b",  # このサービスは停止させていただきます
        "3": "c",  # 閉会
        "4": "b"   # この職を引退します
    }
    
    # N1第2课 语法点5: 〜といったところだ
    answers["n1-l02-g05"] = {
        "1": "c",  # 5時間
        "2": "c",  # 無理なく続けられる
        "3": "b"   # せいぜい
    }
    
    # 保存答案
    with open(ANSWERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(answers, f, ensure_ascii=False, indent=2)
    
    print(f"已更新N1第2课答案，保存到: {ANSWERS_FILE}")
    
    # 统计
    n1_lesson2_count = sum(len(answers.get(f"n1-l02-g{i:02d}", {})) for i in range(1, 6))
    print(f"N1第2课答题数: {n1_lesson2_count}")
    print(f"累计答题数: {sum(len(a) for a in answers.values())}")

if __name__ == "__main__":
    update_n1_l02()