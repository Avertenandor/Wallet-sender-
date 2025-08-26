#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки конкретных строк с ошибками
"""

def check_error_lines():
    error_lines = [1879, 1896, 2465, 2470, 2475, 2491, 2530, 2688, 2693, 2874]
    
    with open('WalletSender.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print("=" * 80)
    print("АНАЛИЗ СТРОК С ОШИБКАМИ")
    print("=" * 80)
    
    for line_num in error_lines:
        if line_num <= len(lines):
            # Показываем контекст: 2 строки до и 2 после
            start = max(0, line_num - 3)
            end = min(len(lines), line_num + 2)
            
            print(f"\n📍 Строка {line_num}:")
            print("-" * 60)
            for i in range(start, end):
                prefix = ">>> " if i == line_num - 1 else "    "
                print(f"{i+1:4d}: {prefix}{lines[i].rstrip()}")
            print("-" * 60)
    
    # Анализ типов ошибок
    print("\n" + "=" * 80)
    print("АНАЛИЗ ТИПОВ ОШИБОК")
    print("=" * 80)
    
    # Проверка слотов PyQt
    print("\n1. Проверка слотов connect() (строки 1879, 1896):")
    for line_num in [1879, 1896]:
        if line_num <= len(lines):
            line = lines[line_num - 1]
            if '.connect(' in line:
                print(f"   Строка {line_num}: {line.strip()}")
                # Ищем функцию, которая используется в connect
                if 'self.' in line:
                    func_name = line.split('self.')[1].split(')')[0]
                    print(f"   Функция: self.{func_name}")
                    # Ищем определение функции
                    for i, l in enumerate(lines):
                        if f'def {func_name}(' in l:
                            print(f"   Определение на строке {i+1}: {l.strip()}")
                            # Проверяем возвращаемый тип
                            if '-> bool' in l:
                                print(f"   ⚠️ Возвращает bool - нужно изменить на None")
                            break
    
    # Проверка атрибутов Qt
    print("\n2. Проверка атрибутов Qt (остальные строки):")
    qt_error_lines = [2465, 2470, 2475, 2491, 2530, 2688, 2693, 2874]
    for line_num in qt_error_lines:
        if line_num <= len(lines):
            line = lines[line_num - 1]
            if 'Qt.' in line or 'type[Qt]' in line:
                print(f"   Строка {line_num}: {line.strip()}")
                if 'UserRole' in line:
                    print(f"   ⚠️ Использует UserRole - нужна проверка импорта")
                if 'ItemIsEditable' in line:
                    print(f"   ⚠️ Использует ItemIsEditable - нужна проверка импорта")

if __name__ == "__main__":
    check_error_lines()
