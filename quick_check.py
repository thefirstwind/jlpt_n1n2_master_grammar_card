#!/usr/bin/env python3
"""快速检查所有题目，一课一课地进行"""

import json
import re
from pathlib import Path

REVIEW_DIR = Path(__file__).resolve().parent
EXPORT_PATH = REVIEW_DIR / "_all_exercises_export.json"
HTML_FILE = REVIEW_DIR / "index.html"

def load_exercises():
    with open(EXPORT_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def quick_check():
    exercises = load_exercises()
    
    # 读取HTML文件
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 按课程分组
    lessons = {}
    for aid, data in exercises.items():
        level = data.get('level', '')
        lesson = data.get('lesson', 0)
        key = f"{level}-L{lesson}"
        if key not in lessons:
            lessons[key] = []
        lessons[key].append((aid, data))
    
    print("=== 快速检查报告 ===\n")
    
    total_questions = 0
    total_correct = 0
    total_need_check = 0
    
    # 按课程检查
    for key in sorted(lessons.keys()):
        level_lesson = key
        grammar_points = lessons[key]
        
        print(f"\n## {level_lesson}")
        
        lesson_questions = 0
        lesson_correct = 0
        lesson_need_check = 0
        
        for aid, data in grammar_points:
            pattern = data.get('pattern', '')
            questions = data.get('questions', [])
            
            for q in questions:
                lesson_questions += 1
                total_questions += 1
                
                q_num = q.get('q', '')
                stem = q.get('stem', '')
                
                # 在HTML中查找答案
                html_pattern = f'data-aid="{re.escape(aid)}".*?data-q="{re.escape(str(q_num))}" data-answer="([a-c])"'
                match = re.search(html_pattern, html_content, re.DOTALL)
                
                if match:
                    # 这里可以添加逻辑判断答案是否正确
                    # 暂时只记录找到的题目
                    lesson_correct += 1
                    total_correct += 1
                else:
                    lesson_need_check += 1
                    total_need_check += 1
        
        print(f"  题目数: {lesson_questions}, 找到答案: {lesson_correct}, 需检查: {lesson_need_check}")
    
    print(f"\n=== 总计 ===")
    print(f"总题目数: {total_questions}")
    print(f"找到答案的题目: {total_correct}")
    print(f"需检查的题目: {total_need_check}")
    
    if total_need_check > 0:
        print(f"\n⚠️  有 {total_need_check} 个题目需要详细检查")
    else:
        print("🎉 所有题目的答案都在HTML中找到")

if __name__ == "__main__":
    quick_check()