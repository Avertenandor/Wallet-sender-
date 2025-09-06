#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Детальный анализ проблемных строк
"""

print("=" * 80)
print("ДЕТАЛЬНЫЙ АНАЛИЗ ПРОБЛЕМНЫХ СТРОК")
print("=" * 80)

with open('WalletSender.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Анализ строк 1879 и 1896 (проблемы с PyQt слотами)
print("\n1. Анализ проблем с PyQt слотами:")
print("-" * 40)

for line_num in [1879, 1896]:
    if line_num <= len(lines):
        line = lines[line_num - 1]
        print(f"\nСтрока {line_num}:")
        print(f"  Код: {line.strip()}")
        
        # Ищем функцию, на которую ссылается connect
        if '.connect(' in line:
            # Пытаемся найти имя функции
            if 'self.' in line:
                start = line.find('self.')
                end = line.find(')', start)
                if start > -1 and end > -1:
                    func_ref = line[start:end]
                    print(f"  Ссылка на функцию: {func_ref}")
                    
                    # Ищем определение этой функции
                    func_name = func_ref.split('self.')[1].split('(')[0] if 'self.' in func_ref else None
                    if func_name:
                        print(f"  Ищем определение функции: {func_name}")
                        for i, l in enumerate(lines):
                            if f'def {func_name}(' in l:
                                print(f"  Найдено определение на строке {i+1}:")
                                print(f"    {l.strip()}")
                                # Проверяем возвращаемый тип
                                if '-> bool' in l:
                                    print(f"    ⚠️ ПРОБЛЕМА: Функция возвращает bool")
                                    print(f"    ✅ РЕШЕНИЕ: Изменить на '-> None'")
                                break

# Анализ проблем с Qt атрибутами
print("\n2. Анализ проблем с Qt атрибутами:")
print("-" * 40)

qt_error_lines = [2465, 2470, 2475, 2491, 2530, 2688, 2693, 2874]

for line_num in qt_error_lines:
    if line_num <= len(lines):
        line = lines[line_num - 1]
        print(f"\nСтрока {line_num}:")
        print(f"  Код: {line.strip()}")
        
        # Проверяем наличие проблемных атрибутов
        problems = []
        solutions = []
        
        if 'QtCore.Qt.UserRole' in line or 'Qt.UserRole' in line:
            problems.append("QtCore.Qt.UserRole или Qt.UserRole")
            solutions.append("USER_ROLE")
        
        if 'QtCore.Qt.ItemIsEditable' in line or 'Qt.ItemIsEditable' in line:
            problems.append("QtCore.Qt.ItemIsEditable или Qt.ItemIsEditable")
            solutions.append("ITEM_IS_EDITABLE")
        
        if 'QtCore.Qt.CustomContextMenu' in line or 'Qt.CustomContextMenu' in line:
            problems.append("QtCore.Qt.CustomContextMenu или Qt.CustomContextMenu")
            solutions.append("CUSTOM_CONTEXT_MENU")
        
        if problems:
            print(f"  ⚠️ ПРОБЛЕМА: Использование {', '.join(problems)}")
            print(f"  ✅ РЕШЕНИЕ: Заменить на {', '.join(solutions)}")
        else:
            print(f"  ❓ Проблемный атрибут не найден в строке")

print("\n" + "=" * 80)
print("ИТОГОВЫЕ РЕКОМЕНДАЦИИ:")
print("=" * 80)
print("\n1. Для строк 1879, 1896:")
print("   - Найти функции, используемые в .connect()")
print("   - Изменить их возвращаемый тип с '-> bool' на '-> None'")
print("\n2. Для остальных строк:")
print("   - Заменить прямые обращения к Qt атрибутам на константы")
print("   - QtCore.Qt.UserRole → USER_ROLE")
print("   - QtCore.Qt.ItemIsEditable → ITEM_IS_EDITABLE")
print("   - QtCore.Qt.CustomContextMenu → CUSTOM_CONTEXT_MENU")
