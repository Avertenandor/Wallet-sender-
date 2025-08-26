#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Извлечение проблемных строк из файла WalletSender.py
"""

# Строки с ошибками из скриншота
error_lines = {
    1879: "Аргумент типа '0 -> bool' нельзя присвоить параметру 'slot' типа 'PYQT_SLOT'",
    1896: "Аргумент типа '0 -> bool' нельзя присвоить параметру 'slot' типа 'PYQT_SLOT'", 
    2465: "Не удается получить доступ к атрибуту 'UserRole' для класса 'type[Qt]'",
    2470: "Не удается получить доступ к атрибуту 'ItemIsEditable' для класса 'type[Qt]'",
    2475: "Не удается получить доступ к атрибуту 'ItemIsEditable' для класса 'type[Qt]'",
    2491: "Не удается получить доступ к атрибуту 'UserRole' для класса 'type[Qt]'",
    2530: "Не удается получить доступ к атрибуту 'CustomContextMenu' для класса 'type[Qt]'",
    2688: "Не удается получить доступ к атрибуту 'ItemIsEditable' для класса 'type[Qt]'",
    2693: "Не удается получить доступ к атрибуту 'ItemIsEditable' для класса 'type[Qt]'",
    2874: "Не удается получить доступ к атрибуту 'UserRole' для класса 'type[Qt]'"
}

print("=" * 80)
print("АНАЛИЗ СТРОК С ОШИБКАМИ В WalletSender.py")
print("=" * 80)

with open('WalletSender.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for line_num, error_desc in error_lines.items():
    if line_num <= len(lines):
        print(f"\n📍 Строка {line_num}:")
        print(f"   Ошибка: {error_desc}")
        print(f"   Код: {lines[line_num-1].strip()}")
        
        # Показываем контекст
        start = max(0, line_num - 3)
        end = min(len(lines), line_num + 2)
        print("   Контекст:")
        for i in range(start, end):
            prefix = ">>>" if i == line_num - 1 else "   "
            print(f"   {i+1:4d}: {prefix} {lines[i].rstrip()}")

print("\n" + "=" * 80)
print("РЕШЕНИЕ ПРОБЛЕМ:")
print("=" * 80)

# Анализ проблем
print("\n1. Проблемы с PyQt слотами (строки 1879, 1896):")
print("   - Функции, подключаемые к сигналам через .connect(), не должны возвращать bool")
print("   - Нужно изменить возвращаемый тип с '-> bool' на '-> None'")

print("\n2. Проблемы с атрибутами Qt (остальные строки):")
print("   - Нужно использовать константы, определенные в начале файла")
print("   - USER_ROLE вместо QtCore.Qt.UserRole")
print("   - ITEM_IS_EDITABLE вместо QtCore.Qt.ItemIsEditable")
print("   - CUSTOM_CONTEXT_MENU вместо QtCore.Qt.CustomContextMenu")
