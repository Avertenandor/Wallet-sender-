#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый запуск WalletSender Modular
"""

import sys
from pathlib import Path

# Добавляем src в Python path
current_dir = Path(__file__).parent
src_path = current_dir / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Тестируем импорты
print("[SEARCH] Проверка импортов модулей...")

try:
    from wallet_sender.config import get_config
    print("[OK] config.py")
except ImportError as e:
    print(f"[ERROR] config.py: {e}")

try:
    from wallet_sender.constants import PLEX_CONTRACT, USDT_CONTRACT
    print("[OK] constants.py")
except ImportError as e:
    print(f"[ERROR] constants.py: {e}")

try:
    from wallet_sender.ui.tabs import (
        MassDistributionTab,
        DirectSendTab,
        AutoBuyTab,
        AutoSalesTab,
        AnalysisTab,
        SearchTab,
        RewardsTab,
        QueueTab,
        HistoryTab,
        SettingsTab
    )
    print("[OK] Все вкладки импортированы")
except ImportError as e:
    print(f"[ERROR] Ошибка импорта вкладок: {e}")

try:
    from wallet_sender.ui.main_window import MainWindow
    print("[OK] main_window.py")
except ImportError as e:
    print(f"[ERROR] main_window.py: {e}")

print("\n[STATS] Результат проверки:")
print("Если все модули импортированы успешно, приложение готово к запуску!")
