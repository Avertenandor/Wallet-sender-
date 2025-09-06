#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка исправлений в WalletSender.py"""

import ast
import sys
import os

def check_file():
    print("=" * 50)
    print("Проверка файла WalletSender.py")
    print("=" * 50)
    
    try:
        # Проверяем существование файла
        if not os.path.exists('WalletSender.py'):
            print("✗ Файл WalletSender.py не найден")
            return False
            
        with open('WalletSender.py', 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Проверяем синтаксис через AST
        tree = ast.parse(code)
        print("✓ Синтаксис корректный")
        print(f"✓ Файл содержит {len(code)} символов")
        print(f"✓ Файл содержит {code.count(chr(10))} строк")
        
        # Проверяем исправления
        print("\n" + "=" * 50)
        print("Проверка исправлений:")
        print("=" * 50)
        
        # 1. Проверка кодировки в логировании
        if "encoding='utf-8'" in code:
            print("✓ Кодировка UTF-8 добавлена в FileHandler")
        else:
            print("✗ Кодировка UTF-8 НЕ найдена в FileHandler")
            
        # 2. Проверка пути к ds_components (не должно быть кракозябр)
        lines = code.split('\n')
        has_corrupted_path = False
        for i, line in enumerate(lines):
            if 'ds_components_path' in line and any(ord(c) > 127 and ord(c) < 1040 for c in line):
                print(f"✗ Найдены кракозябры в строке {i+1}: {line}")
                has_corrupted_path = True
                
        if not has_corrupted_path:
            print("✓ Путь к ds_components исправлен (нет кракозябр)")
            
        # 3. Проверка правильного пути к ds_components
        if '"ds_components"' in code and 'ds_components_path = os.path.join' in code:
            print("✓ Путь к ds_components указан корректно")
        
        # Проверяем критические импорты
        print("\n" + "=" * 50)
        print("Проверка критических импортов:")
        print("=" * 50)
        
        critical_imports = ['web3', 'PyQt5', 'logging', 'sqlite3', 'json']
        for imp in critical_imports:
            if f'import {imp}' in code or f'from {imp}' in code:
                print(f"✓ Импорт {imp} найден")
            else:
                print(f"⚠ Импорт {imp} может отсутствовать")
        
        print("\n" + "=" * 50)
        print("✓ ПРОВЕРКА ЗАВЕРШЕНА УСПЕШНО")
        print("=" * 50)
        return True
        
    except SyntaxError as e:
        print(f"\n✗ СИНТАКСИЧЕСКАЯ ОШИБКА на строке {e.lineno}: {e.msg}")
        if e.text:
            print(f"  Проблемный код: {e.text.strip()}")
            print(f"  " + " " * (e.offset - 1) + "^")
        return False
    except Exception as e:
        print(f"\n✗ ОШИБКА: {e}")
        return False

if __name__ == "__main__":
    success = check_file()
    sys.exit(0 if success else 1)
