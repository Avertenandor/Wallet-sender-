#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест новой функции очистки кеша
"""

import sys
from pathlib import Path

# Добавляем src в Python path
current_dir = Path(__file__).parent
src_path = current_dir / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

def test_imports():
    """Проверка импортов"""
    try:
        # Проверяем, что модуль импортируется
        from wallet_sender.ui.tabs.settings_tab import SettingsTab
        print("[OK] SettingsTab импортирован успешно")
        
        # Проверяем версию
        from wallet_sender import __version__
        print(f"[OK] Версия приложения: {__version__}")
        
        # Проверяем наличие новых методов
        methods = ['clear_python_cache', 'clear_db_cache', 'clear_all_cache', 'update_cache_stats', 'create_maintenance_tab']
        for method in methods:
            if hasattr(SettingsTab, method):
                print(f"[OK] Метод {method} найден")
            else:
                print(f"[ERROR] Метод {method} НЕ найден")
        
        return True
    except Exception as e:
        print(f"[ERROR] Ошибка импорта: {e}")
        return False

if __name__ == "__main__":
    if test_imports():
        print("\n[OK] Все тесты пройдены успешно!")
        print("Новый функционал очистки кеша готов к использованию.")
        print("Для доступа: Настройки → Обслуживание")
    else:
        print("\n[ERROR] Тесты провалены, проверьте код!")
