#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Простая проверка синтаксиса файла"""

import ast
import sys

def check_file():
    try:
        with open('WalletSender — копия.py', 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Пытаемся парсить AST
        tree = ast.parse(code)
        print("✓ Синтаксис корректный")
        print(f"✓ Файл содержит {len(code)} символов")
        print(f"✓ Файл содержит {code.count(chr(10))} строк")
        
        # Проверяем импорты
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module if node.module else ''
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)
        
        print(f"✓ Найдено {len(set(imports))} уникальных импортов")
        
        # Проверяем классы и функции
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        
        print(f"✓ Найдено {len(classes)} классов")
        print(f"✓ Найдено {len(functions)} функций")
        
        return True
        
    except SyntaxError as e:
        print(f"✗ Синтаксическая ошибка на строке {e.lineno}: {e.msg}")
        if e.text:
            print(f"  Проблемный код: {e.text.strip()}")
            print(f"  " + " " * (e.offset - 1) + "^")
        return False
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False

if __name__ == "__main__":
    success = check_file()
    sys.exit(0 if success else 1)
