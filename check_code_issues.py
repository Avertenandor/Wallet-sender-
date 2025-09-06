#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для поиска проблем в коде
"""

import os
import re
from pathlib import Path

def check_files():
    """Проверка файлов на проблемы"""
    issues = []
    patterns = [
        (r'^\s*pass\s*$', 'Empty pass statement'),
        (r'#\s*TODO', 'TODO comment'),
        (r'#\s*FIXME', 'FIXME comment'),
        (r'#\s*HACK', 'HACK comment'),
        (r'NotImplementedError', 'NotImplementedError'),
        (r'raise\s+NotImplementedError', 'Raises NotImplementedError'),
        (r'\.\.\.', 'Ellipsis (possible placeholder)'),
        (r'^\s*return\s+None\s*$', 'Explicit return None (might be placeholder)'),
    ]
    
    src_path = Path(__file__).parent / "src"
    
    for py_file in src_path.rglob("*.py"):
        # Пропускаем __pycache__ и .mypy_cache
        if '__pycache__' in str(py_file) or '.mypy_cache' in str(py_file):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                for pattern, issue_type in patterns:
                    if re.search(pattern, line):
                        # Проверяем что это не просто pass в except блоке
                        if 'pass' in line and line_num > 1:
                            prev_line = lines[line_num-2].strip()
                            if prev_line.startswith('except') or prev_line.startswith('finally'):
                                continue
                        
                        issues.append({
                            'file': str(py_file.relative_to(Path(__file__).parent)),
                            'line': line_num,
                            'type': issue_type,
                            'content': line.strip()
                        })
        except Exception as e:
            print(f"Error reading {py_file}: {e}")
    
    return issues

def main():
    print("=" * 60)
    print("Проверка кода на проблемы")
    print("=" * 60)
    
    issues = check_files()
    
    if not issues:
        print("✅ Проблем не найдено!")
    else:
        print(f"⚠️ Найдено {len(issues)} потенциальных проблем:\n")
        
        # Группируем по типу
        by_type = {}
        for issue in issues:
            issue_type = issue['type']
            if issue_type not in by_type:
                by_type[issue_type] = []
            by_type[issue_type].append(issue)
        
        for issue_type, items in by_type.items():
            print(f"\n{issue_type} ({len(items)} occurrences):")
            print("-" * 40)
            for item in items[:5]:  # Показываем первые 5
                print(f"  {item['file']}:{item['line']}")
                print(f"    {item['content']}")
            if len(items) > 5:
                print(f"  ... and {len(items) - 5} more")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
