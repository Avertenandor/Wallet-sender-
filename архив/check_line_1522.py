#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Скрипт для проверки строки 1522 в WalletSender.py"""

def check_line_1522():
    """Проверка строки 1522 и окружающего контекста"""
    
    with open('WalletSender.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Индекс строки 1522 (отсчет с 0)
    target_line = 1521
    
    # Показываем контекст - 5 строк до и после
    start = max(0, target_line - 5)
    end = min(len(lines), target_line + 6)
    
    print(f"Контекст вокруг строки 1522 (всего строк в файле: {len(lines)}):\n")
    print("=" * 60)
    
    for i in range(start, end):
        line_num = i + 1
        marker = ">>>" if line_num == 1522 else "   "
        print(f"{marker} {line_num:4d}: {lines[i].rstrip()}")
    
    print("=" * 60)
    
    # Анализ строки 1522
    if target_line < len(lines):
        line = lines[target_line]
        print(f"\nСтрока 1522:")
        print(f"  {repr(line)}")
        
        if "setSectionResizeMode" in line:
            print("\nОБНАРУЖЕНО: вызов setSectionResizeMode")
            print("Проблема: передается литерал 0 вместо QtWidgets.QHeaderView.Stretch")
            print("Решение: заменить 0 на STRETCH_MODE (константа уже определена в начале файла)")
        
        # Поиск всех вызовов setSectionResizeMode
        print("\n" + "=" * 60)
        print("Все вызовы setSectionResizeMode в файле:")
        print("=" * 60)
        
        count = 0
        for i, line in enumerate(lines):
            if "setSectionResizeMode" in line:
                count += 1
                print(f"Строка {i+1:4d}: {line.strip()}")
        
        print(f"\nВсего найдено вызовов: {count}")

if __name__ == "__main__":
    check_line_1522()
