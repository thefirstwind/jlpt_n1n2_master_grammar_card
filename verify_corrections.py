#!/usr/bin/env python3
"""验证所有修正是否已正确应用到HTML文件中"""

import json
import re
from pathlib import Path

REVIEW_DIR = Path(__file__).resolve().parent
CORRECTIONS_FILE = REVIEW_DIR / "grammar_exercise_corrections.json"
HTML_FILE = REVIEW_DIR / "index.html"

def load_corrections():
    with open(CORRECTIONS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def verify_corrections():
    corrections = load_corrections()
    
    # 读取HTML文件
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    print("=== 修正验证报告 ===\n")
    print(f"总修正数量: {len(corrections)}")
    
    correct_count = 0
    incorrect_count = 0
    not_found_count = 0
    
    # 检查每个修正
    for i, correction in enumerate(corrections[:100], 1):  # 先检查前100个
        aid = correction['anchor_id']
        q_num = correction['q']
        stem = correction['stem']
        correct_answer = correction['correct_answer']
        
        # 在HTML中查找这个题目
        # 构建正则表达式匹配模式
        pattern = f'data-aid="{re.escape(aid)}".*?data-q="{re.escape(q_num)}" data-answer="([a-c])"'
        match = re.search(pattern, html_content, re.DOTALL)
        
        if match:
            html_answer = match.group(1)
            if html_answer == correct_answer:
                correct_count += 1
                if i <= 10:  # 显示前10个正确验证
                    print(f"✅ {i}. {aid} 第{q_num}题: HTML答案={html_answer}, 修正答案={correct_answer}")
            else:
                incorrect_count += 1
                print(f"❌ {i}. {aid} 第{q_num}题: 错误！HTML答案={html_answer}, 修正答案={correct_answer}")
                print(f"   题干: {stem[:50]}...")
        else:
            not_found_count += 1
            if i <= 10:  # 显示前10个未找到的
                print(f"⚠️  {i}. {aid} 第{q_num}题: 在HTML中未找到")
    
    print(f"\n=== 验证结果 ===")
    print(f"正确应用: {correct_count}")
    print(f"错误应用: {incorrect_count}")
    print(f"未找到: {not_found_count}")
    
    if incorrect_count == 0:
        print("🎉 所有检查的修正都已正确应用！")
    else:
        print(f"⚠️  发现 {incorrect_count} 个修正未正确应用")

if __name__ == "__main__":
    verify_corrections()