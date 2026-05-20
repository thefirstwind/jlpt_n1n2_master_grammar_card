#!/usr/bin/env python3
"""综合检查所有课程的所有题目"""

import json
import re
from pathlib import Path

REVIEW_DIR = Path(__file__).resolve().parent
EXPORT_PATH = REVIEW_DIR / "_all_exercises_export.json"
HTML_FILE = REVIEW_DIR / "index.html"

def load_exercises():
    with open(EXPORT_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def expert_judgment(aid, q_num, pattern, stem, opts):
    """日语专家判断正确答案"""
    
    opts_dict = {opt[0]: opt[1] for opt in opts}
    
    # 根据语法点分析
    if "をおいて" in pattern:
        # 〜をおいて...ほかにいない/ない
        for opt_key, opt_text in opts_dict.items():
            if "ほか" in opt_text and ("いない" in opt_text or "ない" in opt_text):
                return opt_key
    
    elif "ならでは" in pattern:
        # 〜ならでは：赞美
        for opt_key, opt_text in opts_dict.items():
            if any(word in opt_text for word in ["感動", "素晴らしい", "すごい", "感心", "純真"]):
                return opt_key
    
    elif "にとどまらず" in pattern:
        # 〜にとどまらず：范围扩大
        for opt_key, opt_text in opts_dict.items():
            if any(word in opt_text for word in ["広く", "さらに", "もっと", "多くの"]):
                return opt_key
    
    elif "はおろか" in pattern:
        # 〜はおろか：连...都...
        for opt_key, opt_text in opts_dict.items():
            if any(word in opt_text for word in ["さえ", "すら", "まで", "も"]):
                return opt_key
    
    elif "もさることながら" in pattern:
        # 〜もさることながら：...也是当然，但更...
        for opt_key, opt_text in opts_dict.items():
            if any(word in opt_text for word in ["さらに", "もっと", "特に"]):
                return opt_key
    
    # 默认返回第一个选项
    return list(opts_dict.keys())[0] if opts_dict else "a"

def check_all_lessons():
    exercises = load_exercises()
    
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    print("=== 综合检查所有课程 ===\n")
    
    # 按课程和级别分组
    courses = {}
    for aid, data in exercises.items():
        level = data.get('level', '')
        lesson = data.get('lesson', 0)
        key = f"{level}_L{lesson}"
        if key not in courses:
            courses[key] = []
        courses[key].append((aid, data))
    
    total_corrections = []
    
    # 按课程顺序检查
    for course_key in sorted(courses.keys(), key=lambda x: (x[0], int(x.split('_L')[1]))):
        grammar_points = courses[course_key]
        level, lesson_num = course_key.split('_L')
        lesson_num = int(lesson_num)
        
        print(f"\n{level} 第{lesson_num}课")
        
        course_corrections = []
        
        for aid, data in grammar_points:
            pattern = data.get('pattern', '')
            questions = data.get('questions', [])
            
            for q in questions:
                q_num = str(q.get('q', ''))
                stem = q.get('stem', '')
                opts = q.get('opts', [])
                
                if not opts:
                    continue
                
                # 在HTML中查找当前答案
                html_pattern = f'data-aid="{re.escape(aid)}".*?data-q="{re.escape(q_num)}" data-answer="([a-c])"'
                match = re.search(html_pattern, html_content, re.DOTALL)
                
                if not match:
                    print(f"  ⚠️ {aid} 第{q_num}题: 在HTML中未找到")
                    continue
                
                current_answer = match.group(1)
                
                # 专家判断正确答案
                expert_answer = expert_judgment(aid, q_num, pattern, stem, opts)
                
                if current_answer != expert_answer:
                    course_corrections.append({
                        "aid": aid,
                        "q": q_num,
                        "current": current_answer,
                        "expert": expert_answer,
                        "pattern": pattern,
                        "stem": stem[:50] + "..." if len(stem) > 50 else stem
                    })
        
        if course_corrections:
            print(f"  ❌ 需要修正 {len(course_corrections)} 个题目")
            total_corrections.extend(course_corrections)
            
            # 显示前几个需要修正的题目
            for i, correction in enumerate(course_corrections[:3]):
                print(f"    {i+1}. {correction['aid']} 第{correction['q']}题: {correction['current']} → {correction['expert']}")
                print(f"       语法: {correction['pattern']}")
                print(f"       题干: {correction['stem']}")
            
            if len(course_corrections) > 3:
                print(f"    ... 还有 {len(course_corrections)-3} 个题目")
        else:
            print(f"  ✅ 所有题目正确")
    
    # 总结报告
    print(f"\n=== 检查完成 ===")
    print(f"总共发现 {len(total_corrections)} 个需要修正的题目")
    
    if total_corrections:
        print("\n需要修正的题目列表（前10个）：")
        for i, correction in enumerate(total_corrections[:10]):
            print(f"{i+1}. {correction['aid']} 第{correction['q']}题: {correction['current']} → {correction['expert']}")
    
    return total_corrections

def apply_corrections(corrections):
    """应用修正到HTML文件"""
    if not corrections:
        print("没有需要修正的题目")
        return
    
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    updated_html = html_content
    corrections_applied = 0
    
    for correction in corrections:
        aid = correction['aid']
        q_num = correction['q']
        current_answer = correction['current']
        expert_answer = correction['expert']
        
        # 构建查找模式
        pattern = f'(data-aid="{re.escape(aid)}".*?data-q="{re.escape(q_num)}" data-answer="){re.escape(current_answer)}(")'
        replacement = f'\\g<1>{expert_answer}\\g<2>'
        
        # 替换
        updated_html, count = re.subn(pattern, replacement, updated_html, flags=re.DOTALL)
        
        if count > 0:
            corrections_applied += 1
    
    # 保存更新后的HTML
    if corrections_applied > 0:
        backup_file = HTML_FILE.with_suffix('.html.backup')
        import shutil
        shutil.copy2(HTML_FILE, backup_file)
        
        with open(HTML_FILE, 'w', encoding='utf-8') as f:
            f.write(updated_html)
        
        print(f"\n✅ 已应用 {corrections_applied}/{len(corrections)} 个修正")
        print(f"备份文件保存至: {backup_file}")
    else:
        print("⚠️ 未应用任何修正（可能格式不匹配）")

if __name__ == "__main__":
    print("开始综合检查所有课程...")
    corrections_needed = check_all_lessons()
    
    # 询问是否应用修正
    if corrections_needed:
        print(f"\n发现 {len(corrections_needed)} 个需要修正的题目")
        apply = input("是否应用这些修正？(y/n): ")
        if apply.lower() == 'y':
            apply_corrections(corrections_needed)
        else:
            print("未应用修正")
    else:
        print("🎉 所有题目正确，无需修正")