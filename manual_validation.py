#!/usr/bin/env python3
"""手动验证有争议的题目"""

import json
from pathlib import Path

REVIEW_DIR = Path(__file__).resolve().parent
EXPORT_PATH = REVIEW_DIR / "_all_exercises_export.json"
CONSENSUS_REPORT = REVIEW_DIR / "grammar_exercise_consensus_report.json"
EXPERT_A_PATH = REVIEW_DIR / "_expert_A_snapshot.json"
ANSWER_FILE = REVIEW_DIR / "grammar_exercise_answers_expert.json"

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    # 加载数据
    exercises = load_json(EXPORT_PATH)
    consensus = load_json(CONSENSUS_REPORT)
    expert_a = load_json(EXPERT_A_PATH)
    current_answers = load_json(ANSWER_FILE)
    
    print("=== 有争议题目验证报告 ===\n")
    print(f"总共有 {len(consensus['items'])} 个有争议的题目\n")
    
    # 检查每个有争议的题目
    for i, item in enumerate(consensus['items'], 1):
        aid = item['aid']
        q = item['q']
        expert_a_answer = item['A']
        expert_b_answer = item['B']
        expert_c_answer = item['C']
        final_answer = item['final']
        
        # 获取题目信息
        if aid not in exercises:
            print(f"{i}. 题目 {aid} 第{q}题: 在练习数据中未找到")
            continue
            
        exercise = exercises[aid]
        pattern = exercise.get('pattern', '')
        questions = exercise.get('questions', [])
        
        # 找到对应的题目
        target_q = None
        for question in questions:
            if str(question.get('q', '')) == q:
                target_q = question
                break
        
        if not target_q:
            print(f"{i}. 题目 {aid} 第{q}题: 未找到题目")
            continue
            
        stem = target_q.get('stem', '')
        opts = target_q.get('opts', [])
        
        # 显示题目信息
        print(f"{i}. 题目: {aid} 第{q}题")
        print(f"   语法点: {pattern}")
        print(f"   题干: {stem}")
        print(f"   选项:")
        for opt in opts:
            print(f"     {opt[0]}. {opt[1]}")
        
        # 显示专家答案
        print(f"   专家A: {expert_a_answer}")
        print(f"   专家B: {expert_b_answer}")
        print(f"   专家C: {expert_c_answer}")
        print(f"   最终答案: {final_answer}")
        
        # 分析正确答案
        print(f"   分析:")
        
        # 根据语法点分析
        if "ならでは" in pattern:
            print("    语法点: 〜ならでは（只有...才能做到的赞美）")
            print("    正确选项应该是表达正面评价的选项")
            # 检查哪个选项是正面评价
            for opt in opts:
                opt_text = opt[1]
                if any(word in opt_text for word in ["感動", "素晴らしい", "すごい", "感心", "純真", "上手", "立派"]):
                    print(f"    建议答案: {opt[0]}（{opt_text}）")
                    break
            else:
                print("    警告: 未找到明显的正面评价选项")
                
        elif "をおいて" in pattern:
            print("    语法点: 〜をおいて...ほかにいない/ない")
            print("    正确选项应该与'ほかにいない/ない'搭配")
            for opt in opts:
                opt_text = opt[1]
                if "ほか" in opt_text and ("いない" in opt_text or "ない" in opt_text):
                    print(f"    建议答案: {opt[0]}（{opt_text}）")
                    break
            else:
                print("    警告: 未找到合适的搭配选项")
                
        elif "にとどまらず" in pattern:
            print("    语法点: 〜にとどまらず（不限于...）")
            print("    正确选项应该表示范围扩大")
            for opt in opts:
                opt_text = opt[1]
                if any(word in opt_text for word in ["広く", "世界中", "多くの", "さらに", "もっと"]):
                    print(f"    建议答案: {opt[0]}（{opt_text}）")
                    break
            else:
                print("    警告: 未找到表示范围扩大的选项")
                
        elif "はおろか" in pattern:
            print("    语法点: 〜はおろか（不用说...连...）")
            print("    正确选项应该表示程度更甚")
            for opt in opts:
                opt_text = opt[1]
                if any(word in opt_text for word in ["さえ", "まで", "も", "すら"]):
                    print(f"    建议答案: {opt[0]}（{opt_text}）")
                    break
            else:
                print("    警告: 未找到表示程度递进的选项")
        
        print()  # 空行分隔

if __name__ == "__main__":
    main()