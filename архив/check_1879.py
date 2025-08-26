#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('WalletSender.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Показываем контекст вокруг строки 1879
print("Контекст строки 1879:")
print("=" * 60)

for i in range(1873, min(1885, len(lines))):
    line_num = i + 1
    marker = ">>>" if line_num == 1879 else "   "
    print(f"{marker} {line_num}: {lines[i].rstrip()}")

# Сохраним в файл для анализа
with open('line_1879_context.txt', 'w', encoding='utf-8') as out:
    for i in range(1873, min(1885, len(lines))):
        out.write(f"{i+1}: {lines[i]}")

print("\nКонтекст сохранен в line_1879_context.txt")
