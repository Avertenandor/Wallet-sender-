#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Простая проверка синтаксиса WalletSender.py"""

import ast
import sys

def check_syntax():
    try:
        with open('WalletSender.py', 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Пробуем скомпилировать
        compile(code, 'WalletSender.py', 'exec')
        print("✅ Синтаксис корректен - файл компилируется")
        
        # Пробуем построить AST
        ast.parse(code)
        print("✅ AST дерево построено успешно")
        
        print("\n📊 Статистика файла:")
        lines = code.split('\n')
        print(f"  - Строк кода: {len(lines)}")
        print(f"  - Размер: {len(code)} байт")
        
        # Подсчет функций и классов
        tree = ast.parse(code)
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        print(f"  - Функций: {len(functions)}")
        print(f"  - Классов: {len(classes)}")
        
        return True
        
    except SyntaxError as e:
        print(f"❌ Синтаксическая ошибка на строке {e.lineno}:")
        print(f"   {e.msg}")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    success = check_syntax()
    sys.exit(0 if success else 1)
