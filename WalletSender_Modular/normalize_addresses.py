#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для нормализации и проверки адресов из файла 01.09_ГЕНА_50.txt
"""

from web3 import Web3
from pathlib import Path
import sys

def normalize_addresses(input_file: str, output_file: str = None):
    """
    Нормализация адресов в checksum формат и удаление дубликатов
    
    Args:
        input_file: Путь к исходному файлу
        output_file: Путь к выходному файлу (если None, добавляется _normalized)
    """
    
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"❌ Файл не найден: {input_file}")
        return False
    
    if output_file is None:
        output_file = input_path.stem + "_normalized" + input_path.suffix
    
    print(f"📂 Обработка файла: {input_file}")
    
    # Читаем адреса
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"📋 Прочитано строк: {len(lines)}")
    
    # Обработка адресов
    valid_addresses = set()  # Используем set для автоматического удаления дубликатов
    invalid_lines = []
    duplicates = 0
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        
        # Пропускаем пустые строки
        if not line:
            continue
        
        # Проверяем валидность адреса
        if Web3.is_address(line):
            # Нормализуем в checksum формат
            checksum_address = Web3.to_checksum_address(line)
            
            # Проверяем на дубликат
            if checksum_address in valid_addresses:
                duplicates += 1
                print(f"  ⚠️ Строка {i}: Дубликат {checksum_address[:10]}...")
            else:
                valid_addresses.add(checksum_address)
        else:
            invalid_lines.append((i, line))
            print(f"  ❌ Строка {i}: Невалидный адрес: {line[:20]}...")
    
    # Сохраняем нормализованные адреса
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='