#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для массового удаления всех эмодзи из всех Python файлов проекта
"""

import os
import re
from pathlib import Path

def remove_emoji_from_file(file_path):
    """Удаляет все эмодзи из файла"""
    
    # Словарь замен эмодзи на текстовые аналоги
    emoji_replacements = {
        '[START]': '[START]',
        '[OK]': '[OK]',
        '[ERROR]': '[ERROR]',
        '[WARN]': '[WARN]',
        '[THEME]': '[THEME]',
        '[CONFIG]': '[CONFIG]',
        '[INFO]': '[INFO]',
        '[CONNECT]': '[CONNECT]',
        '[DISCONNECT]': '[DISCONNECT]',
        '[MONEY]': '[MONEY]',
        '[BUY]': '[BUY]',
        '[SEND]': '[SEND]',
        '[MASS]': '[MASS]',
        '[SEARCH]': '[SEARCH]',
        '[HISTORY]': '[HISTORY]',
        '[SETTINGS]': '[SETTINGS]',
        '[BYE]': '[BYE]',
        '[STATS]': '[STATS]',
        '[TARGET]': '[TARGET]',
        '[FINISH]': '[FINISH]',
        '[SAVE]': '[SAVE]',
        '[WEB]': '[WEB]',
        '[MINIMAL]': '[MINIMAL]',
        '[HOT]': '[HOT]',
        '[MAGIC]': '[MAGIC]',
        '[IMAGE]': '[IMAGE]',
        '[SECURE]': '[SECURE]',
        '[DOC]': '[DOC]',
        '[TEST]': '[TEST]',
        '[DELETE]': '[DELETE]',
        '[COMPRESS]': '[COMPRESS]',
        '[ARROW]': '[ARROW]',
        '[PLAY]': '[PLAY]',
        '[RETURN]': '[RETURN]',
        '[CHECK]': '[CHECK]'
    }
    
    try:
        # Читаем файл с правильной кодировкой
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Сохраняем оригинальный контент для сравнения
        original_content = content
        
        # Заменяем все эмодзи
        for emoji, replacement in emoji_replacements.items():
            content = content.replace(emoji, replacement)
        
        # Проверяем, были ли изменения
        if content != original_content:
            # Сохраняем изменения
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"[ERROR] Ошибка обработки файла {file_path}: {e}")
        return False

def main():
    """Основная функция"""
    print("[START] Удаление эмодзи из всех Python файлов проекта")
    print("=" * 60)
    
    # Корневая директория проекта
    project_root = Path(".")
    
    # Поиск всех .py файлов
    python_files = list(project_root.rglob("*.py"))
    
    print(f"[INFO] Найдено {len(python_files)} Python файлов")
    
    modified_count = 0
    processed_count = 0
    
    for file_path in python_files:
        try:
            # Пропускаем файлы в .venv и __pycache__
            if '.venv' in str(file_path) or '__pycache__' in str(file_path):
                continue
                
            processed_count += 1
            
            if remove_emoji_from_file(file_path):
                modified_count += 1
                print(f"[MODIFIED] {file_path}")
            else:
                print(f"[SKIPPED] {file_path}")
                
        except Exception as e:
            print(f"[ERROR] Ошибка файла {file_path}: {e}")
    
    print("\n" + "=" * 60)
    print(f"[FINISH] Обработка завершена:")
    print(f"  - Обработано файлов: {processed_count}")
    print(f"  - Изменено файлов: {modified_count}")
    print(f"  - Пропущено файлов: {len(python_files) - processed_count}")
    
    if modified_count > 0:
        print("\n[OK] Все эмодзи успешно заменены на текстовые аналоги!")
    else:
        print("\n[INFO] Эмодзи не найдены или уже заменены")

if __name__ == "__main__":
    main()
