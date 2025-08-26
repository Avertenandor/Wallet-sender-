#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Скрипт для проверки ошибок в WalletSender — копия.py"""

import ast
import sys
import importlib
import traceback

def check_imports():
    """Проверка доступности всех импортов"""
    required_modules = [
        'requests',
        'mnemonic',
        'cryptography',
        'PyQt5',
        'qdarkstyle',
        'eth_utils',
        'web3',
        'eth_account',
        'openpyxl'
    ]
    
    missing = []
    for module in required_modules:
        try:
            importlib.import_module(module)
            print(f"✓ {module} установлен")
        except ImportError:
            print(f"✗ {module} НЕ установлен")
            missing.append(module)
    
    return missing

def check_syntax(filename):
    """Проверка синтаксиса файла"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Компиляция AST
        ast.parse(code)
        print("\n✓ Синтаксис файла корректный")
        return True
    except SyntaxError as e:
        print(f"\n✗ Синтаксическая ошибка:")
        print(f"  Строка {e.lineno}: {e.msg}")
        if e.text:
            print(f"  Код: {e.text.strip()}")
        return False
    except Exception as e:
        print(f"\n✗ Ошибка при проверке синтаксиса: {e}")
        return False

def check_file_structure(filename):
    """Проверка структуры файла"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"\n📊 Статистика файла:")
        print(f"  Всего строк: {len(lines)}")
        
        # Проверка незакрытых кавычек
        open_quotes = 0
        for i, line in enumerate(lines, 1):
            # Подсчёт тройных кавычек
            open_quotes += line.count('"""') % 2
            open_quotes += line.count("'''") % 2
        
        if open_quotes != 0:
            print(f"  ⚠ Возможны незакрытые тройные кавычки")
        
        # Проверка баланса скобок
        brackets = {'(': 0, '[': 0, '{': 0}
        for line in lines:
            # Игнорируем строки в комментариях
            if line.strip().startswith('#'):
                continue
            for char in line:
                if char == '(':
                    brackets['('] += 1
                elif char == ')':
                    brackets['('] -= 1
                elif char == '[':
                    brackets['['] += 1
                elif char == ']':
                    brackets['['] -= 1
                elif char == '{':
                    brackets['{'] += 1
                elif char == '}':
                    brackets['{'] -= 1
        
        unbalanced = False
        for bracket, count in brackets.items():
            if count != 0:
                print(f"  ⚠ Несбалансированные скобки {bracket}: {abs(count)}")
                unbalanced = True
        
        if not unbalanced:
            print(f"  ✓ Все скобки сбалансированы")
        
        return True
    except Exception as e:
        print(f"\n✗ Ошибка при проверке структуры: {e}")
        return False

def try_import_file(filename):
    """Попытка импортировать файл и найти ошибки выполнения"""
    try:
        # Удаляем расширение для импорта
        module_name = filename.replace('.py', '').replace(' — копия', '_copy')
        
        # Читаем файл
        with open(filename, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Компилируем код
        compiled = compile(code, filename, 'exec')
        
        # Создаём пространство имён для выполнения
        namespace = {}
        
        # Пытаемся выполнить
        exec(compiled, namespace)
        
        print("\n✓ Файл может быть выполнен без критических ошибок")
        return True
    except Exception as e:
        print(f"\n⚠ Ошибка при попытке выполнения:")
        print(f"  Тип: {type(e).__name__}")
        print(f"  Сообщение: {str(e)}")
        
        # Выводим traceback для более детальной информации
        tb_lines = traceback.format_exc().split('\n')
        for line in tb_lines[-5:]:
            if line.strip():
                print(f"  {line}")
        return False

def main():
    filename = "WalletSender — копия.py"
    
    print("=" * 50)
    print("ПРОВЕРКА ФАЙЛА:", filename)
    print("=" * 50)
    
    # 1. Проверка импортов
    print("\n1. ПРОВЕРКА МОДУЛЕЙ:")
    missing_modules = check_imports()
    
    # 2. Проверка синтаксиса
    print("\n2. ПРОВЕРКА СИНТАКСИСА:")
    syntax_ok = check_syntax(filename)
    
    # 3. Проверка структуры
    print("\n3. ПРОВЕРКА СТРУКТУРЫ:")
    check_file_structure(filename)
    
    # 4. Попытка выполнения
    print("\n4. ПРОВЕРКА ВЫПОЛНЕНИЯ:")
    try_import_file(filename)
    
    # Итоги
    print("\n" + "=" * 50)
    print("ИТОГИ ПРОВЕРКИ:")
    print("=" * 50)
    
    if missing_modules:
        print(f"\n⚠ Необходимо установить модули:")
        for module in missing_modules:
            print(f"  pip install {module}")
    
    if syntax_ok:
        print("\n✓ Синтаксических ошибок не обнаружено")
    else:
        print("\n✗ Обнаружены синтаксические ошибки - требуется исправление")
    
    print("\n📝 Рекомендации:")
    print("  1. Установите все недостающие модули")
    print("  2. Проверьте конфигурационные файлы (config.json)")
    print("  3. Убедитесь в наличии необходимых директорий (logs, rewards_configs)")

if __name__ == "__main__":
    main()
