#!/usr/bin/env python3
"""
Тестовый скрипт для проверки SearchTab
"""

import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    print("Тестирование импортов SearchTab...")
    
    # Базовые импорты
    from wallet_sender.utils.logger import get_logger
    print("[OK] Logger импортирован")
    
    from wallet_sender.constants import PLEX_CONTRACT, USDT_CONTRACT
    print("[OK] Constants импортированы")
    
    from wallet_sender.services import get_bscscan_service
    print("[OK] BscScanService импортирован")
    
    from wallet_sender.ui.tabs.base_tab import BaseTab
    print("[OK] BaseTab импортирован")
    
    # Главный импорт
    from wallet_sender.ui.tabs.search_tab import SearchTab
    print("[OK] SearchTab импортирован успешно!")
    
    print("\n🎉 Все импорты работают корректно!")
    
except ImportError as e:
    print(f"[ERROR] Ошибка импорта: {e}")
    import traceback
    traceback.print_exc()
    
except Exception as e:
    print(f"[ERROR] Неожиданная ошибка: {e}")
    import traceback
    traceback.print_exc()
