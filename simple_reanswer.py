#!/usr/bin/env python3
"""简单直接的答题脚本"""

import json
from pathlib import Path

REVIEW_DIR = Path(__file__).resolve().parent
EXERCISES_FILE = REVIEW_DIR / "_all_exercises_export.json"
ANSWERS_FILE = REVIEW_DIR / "grammar_exercise_answers.json"

def answer_n1_l01_g01():
    """N1第1课语法点1: 〜が早いか"""
    return {
        "1": "b",  # 見る
        "2": "a",  # 若い女性たちが殺到した
        "3": "c"   # 彼はビールを飲み始めた
    }

def answer_n1_l01_g02():
    """N1第1课语法点2: 〜や・〜や否や"""
    return {
        "1": "b",  # 始める
        "2": "b",  # 消防車が出動した
        "3": "a",  # 彼女は逃げ出した
        "4": "b"   # 彼は会社を辞めた
    }

def answer_n1_l01_g03():
    """N1第1课语法点3: 〜なり"""
    return {
        "1": "b",  # 彼女は
        "2": "a",  # 彼は
        "3": "b"   # 彼女は
    }

def answer_n1_l01_g04():
    """N1第1课语法点4: 〜そばから"""
    return {
        "1": "a",  # 言われる
        "2": "b",  # 片付ける
        "3": "b"   # 覚える
    }

def answer_n1_l01_g05():
    """N1第1课语法点5: 〜てからというもの（は）"""
    return {
        "1": "b",  # 始まって
        "2": "a",  # 習って
        "3": "a",  # 退職して
        "4": "b"   # 入って
    }

def answer_n1_l01_g06():
    """N1第1课语法点6: 〜にあって"""
    return {
        "1": "b",  # この不況下に
        "2": "a",  # 今の社会に
        "3": "b"   # そんな状況に
    }

def main():
    # 加载现有答案
    if ANSWERS_FILE.exists():
        with open(ANSWERS_FILE, 'r', encoding='utf-8') as f:
            answers = json.load(f)
    else:
        answers = {}
    
    # 更新N1第1课的答案
    answers["n1-l01-g01"] = answer_n1_l01_g01()
    answers["n1-l01-g02"] = answer_n1_l01_g02()
    answers["n1-l01-g03"] = answer_n1_l01_g03()
    answers["n1-l01-g04"] = answer_n1_l01_g04()
    answers["n1-l01-g05"] = answer_n1_l01_g05()
    answers["n1-l01-g06"] = answer_n1_l01_g06()
    
    # 保存答案
    with open(ANSWERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(answers, f, ensure_ascii=False, indent=2)
    
    print(f"已更新N1第1课答案，保存到: {ANSWERS_FILE}")
    
    # 统计
    n1_lesson1_count = sum(len(answers.get(f"n1-l01-g{i:02d}", {})) for i in range(1, 7))
    print(f"N1第1课答题数: {n1_lesson1_count}")

if __name__ == "__main__":
    main()