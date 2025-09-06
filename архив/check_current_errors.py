#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки текущих ошибок в WalletSender.py
"""

import ast
import sys
import os
import re
from typing import Dict, List, Tuple

def check_syntax():
    """Проверка синтаксиса Python"""
    print("=" * 60)
    print("ПРОВЕРКА СИНТАКСИСА WalletSender.py")
    print("=" * 60)
    
    filename = "WalletSender.py"
    if not os.path.exists(filename):
        print(f"❌ Файл {filename} не найден!")
        return False
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Проверка компиляции
        compile(code, filename, 'exec')
        print("✅ Синтаксис Python корректен - файл компилируется")
        
        # Проверка AST
        ast.parse(code)
        print("✅ AST дерево построено успешно")
        
        return True
        
    except SyntaxError as e:
        print(f"❌ Синтаксическая ошибка на строке {e.lineno}:")
        print(f"   {e.msg}")
        print(f"   Файл: {e.filename}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при проверке: {e}")
        return False

def check_imports():
    """Проверка импортов"""
    print("\n" + "=" * 60)
    print("ПРОВЕРКА ИМПОРТОВ")
    print("=" * 60)
    
    filename = "WalletSender.py"
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    imports = []
    missing_imports = []
    
    # Собираем все импорты
    for i, line in enumerate(lines[:100], 1):  # Проверяем первые 100 строк
        if line.strip().startswith(('import ', 'from ')):
            imports.append((i, line.strip()))
    
    print(f"Найдено {len(imports)} импортов:")
    
    # Проверяем критические импорты
    critical_imports = {
        'typing': ['Optional', 'Dict', 'List', 'Any', 'Union', 'Tuple'],
        'PyQt5.QtCore': ['pyqtSignal', 'pyqtSlot', 'QThread'],
        'PyQt5.QtWidgets': ['QApplication', 'QMainWindow'],
        'web3': ['Web3'],
        'eth_account': ['Account']
    }
    
    found_imports = set()
    for _, import_line in imports:
        for module, items in critical_imports.items():
            if module in import_line:
                found_imports.add(module)
    
    print("\nКритические импорты:")
    for module in critical_imports:
        if module in found_imports:
            print(f"  ✅ {module}")
        else:
            print(f"  ⚠️ {module} - возможно отсутствует")
            missing_imports.append(module)
    
    return len(missing_imports) == 0

def check_common_errors():
    """Проверка типичных ошибок"""
    print("\n" + "=" * 60)
    print("АНАЛИЗ ТИПИЧНЫХ ПРОБЛЕМ")
    print("=" * 60)
    
    filename = "WalletSender.py"
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    issues = {
        'optional_none': [],
        'undefined_vars': [],
        'qt_headers': [],
        'type_hints': [],
        'web3_types': []
    }
    
    for i, line in enumerate(lines, 1):
        line_stripped = line.strip()
        
        # Проверка Optional с None
        if '= None' in line and 'Optional' not in line and not line_stripped.startswith('#'):
            if ':' in line.split('=')[0]:  # Есть аннотация типа
                var_part = line.split('=')[0]
                if 'Optional' not in var_part and 'None' not in var_part:
                    issues['optional_none'].append(i)
        
        # Проверка Qt headers
        if '.horizontalHeader()' in line and 'if' not in line:
            issues['qt_headers'].append(i)
        
        # Проверка Web3 типов
        if any(x in line for x in ['Web3.', 'w3.', 'contract.', 'Account.']):
            if '# type: ignore' not in line:
                issues['web3_types'].append(i)
        
        # Проверка функций без типов
        if line_stripped.startswith('def ') and '->' not in line:
            if '__init__' not in line:  # Пропускаем конструкторы
                issues['type_hints'].append(i)
    
    # Вывод результатов
    total_issues = 0
    
    for category, lines_list in issues.items():
        if lines_list:
            count = len(lines_list)
            total_issues += count
            print(f"\n{category.upper()}: {count} проблем")
            # Показываем первые 5 примеров
            print(f"  Строки: {lines_list[:5]}")
            if count > 5:
                print(f"  ... и еще {count - 5}")
    
    print("\n" + "-" * 60)
    print(f"ВСЕГО ОБНАРУЖЕНО ПРОБЛЕМ: {total_issues}")
    
    return total_issues

def check_critical_functions():
    """Проверка критических функций"""
    print("\n" + "=" * 60)
    print("ПРОВЕРКА КРИТИЧЕСКИХ ФУНКЦИЙ")
    print("=" * 60)
    
    filename = "WalletSender.py"
    with open(filename, 'r', encoding='utf-8') as f:
        code = f.read()
    
    critical_functions = [
        'send_transaction',
        'mass_distribution',
        'check_balance',
        'save_to_database',
        'fetch_found_transactions',
        '_update_address_progress',
        '_mass_update_table_status'
    ]
    
    found_functions = []
    missing_functions = []
    
    for func in critical_functions:
        if f"def {func}" in code:
            found_functions.append(func)
            print(f"  ✅ {func}")
        else:
            missing_functions.append(func)
            print(f"  ❌ {func} - не найдена")
    
    return len(missing_functions) == 0

def main():
    """Главная функция"""
    print("\n🔍 КОМПЛЕКСНАЯ ПРОВЕРКА WalletSender.py")
    print("=" * 60)
    
    results = {
        'syntax': check_syntax(),
        'imports': check_imports(),
        'functions': check_critical_functions()
    }
    
    total_issues = check_common_errors()
    
    print("\n" + "=" * 60)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 60)
    
    if results['syntax']:
        print("✅ Синтаксис: OK")
    else:
        print("❌ Синтаксис: ОШИБКИ")
    
    if results['imports']:
        print("✅ Импорты: OK")
    else:
        print("⚠️ Импорты: Есть предупреждения")
    
    if results['functions']:
        print("✅ Критические функции: OK")
    else:
        print("❌ Критические функции: Есть проблемы")
    
    print(f"\n📊 Обнаружено типовых проблем: {total_issues}")
    
    if total_issues > 0:
        print("\n💡 РЕКОМЕНДАЦИИ:")
        print("1. Запустите FIX_ALL_ERRORS.py для автоматического исправления")
        print("2. Проверьте Qt headers на наличие проверок на None")
        print("3. Добавьте # type: ignore для проблемных импортов Web3")
        print("4. Используйте Optional для параметров со значением None")
    else:
        print("\n✅ Файл в хорошем состоянии!")
    
    print("\n" + "=" * 60)
    print("Проверка завершена")
    print("=" * 60)

if __name__ == "__main__":
    main()
