#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Анализ строки 1522 в WalletSender.py"""

import os

# Переход в нужную директорию
os.chdir(r'C:\Users\konfu\Desktop\Sites\Experiment\Experiment1\WalletSender_MCP  копия')

# Чтение файла
with open('WalletSender.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Запись результата анализа в файл
with open('line_1522_analysis.txt', 'w', encoding='utf-8') as out:
    # Строка 1522 (индекс 1521)
    target_line = 1521
    
    out.write(f"АНАЛИЗ СТРОКИ 1522 в WalletSender.py\n")
    out.write(f"Всего строк в файле: {len(lines)}\n\n")
    out.write("=" * 60 + "\n")
    out.write("КОНТЕКСТ (строки 1517-1527):\n")
    out.write("=" * 60 + "\n\n")
    
    # Показываем контекст
    for i in range(max(0, target_line - 5), min(len(lines), target_line + 6)):
        line_num = i + 1
        marker = ">>>" if line_num == 1522 else "   "
        out.write(f"{marker} {line_num:4d}: {lines[i].rstrip()}\n")
    
    out.write("\n" + "=" * 60 + "\n")
    out.write("АНАЛИЗ:\n")
    out.write("=" * 60 + "\n\n")
    
    if target_line < len(lines):
        line = lines[target_line]
        out.write(f"Строка 1522 содержит:\n{repr(line)}\n\n")
        
        if "setSectionResizeMode" in line:
            out.write("✓ ОБНАРУЖЕН вызов setSectionResizeMode\n")
            out.write("✗ ПРОБЛЕМА: передается литерал 0 вместо ResizeMode\n")
            out.write("✓ РЕШЕНИЕ: заменить 0 на STRETCH_MODE\n\n")
    
    # Поиск всех вызовов setSectionResizeMode
    out.write("=" * 60 + "\n")
    out.write("ВСЕ ВЫЗОВЫ setSectionResizeMode в файле:\n")
    out.write("=" * 60 + "\n\n")
    
    count = 0
    for i, line in enumerate(lines):
        if "setSectionResizeMode" in line:
            count += 1
            out.write(f"Строка {i+1:4d}: {line.strip()}\n")
    
    out.write(f"\nВсего найдено вызовов: {count}\n")

print("Анализ завершен. Результат сохранен в line_1522_analysis.txt")
