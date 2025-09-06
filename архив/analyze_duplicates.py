#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализатор для поиска дублирующихся методов
"""

def analyze_file():
    with open("WalletSender.py", 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Методы для поиска дубликатов
    methods_to_find = [
        '_mass_start_distribution',
        '_mass_distribution_worker', 
        '_mass_pause_distribution',
        '_mass_resume_distribution',
        '_mass_stop_distribution',
        '_mass_add_addresses',
        '_mass_clear_addresses'
    ]
    
    # Найдем все определения методов
    method_definitions = {}
    
    for i, line in enumerate(lines, 1):
        for method in methods_to_find:
            if f'def {method}(' in line:
                if method not in method_definitions:
                    method_definitions[method] = []
                method_definitions[method].append(i)
    
    # Выводим результаты
    print("НАЙДЕННЫЕ ДУБЛИРУЮЩИЕСЯ МЕТОДЫ:")
    print("=" * 60)
    
    for method, line_numbers in method_definitions.items():
        if len(line_numbers) > 1:
            print(f"❌ {method}:")
            for num in line_numbers:
                # Показываем строку с определением
                print(f"   Строка {num}: {lines[num-1].strip()}")
        elif len(line_numbers) == 1:
            print(f"✅ {method}: только одно определение на строке {line_numbers[0]}")
        else:
            print(f"⚠️ {method}: не найден")
    
    print("=" * 60)
    
    # Сохраняем информацию в файл для последующего использования
    with open("duplicate_methods_info.txt", 'w', encoding='utf-8') as f:
        for method, line_numbers in method_definitions.items():
            if len(line_numbers) > 1:
                f.write(f"{method}:{','.join(map(str, line_numbers))}\n")
    
    return method_definitions

if __name__ == "__main__":
    analyze_file()
