#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('WalletSender.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Строка 1879 (индекс 1878)
if len(lines) > 1878:
    print(f"Строка 1879: {lines[1878].strip()}")
    
    # Ищем connect вокруг этой строки
    for i in range(max(0, 1878-5), min(len(lines), 1878+5)):
        if 'connect' in lines[i].lower():
            print(f"Строка {i+1}: {lines[i].strip()}")
