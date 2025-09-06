#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый запуск WalletSender Modular
"""

import sys
import traceback
from pathlib import Path

# Добавляем src в Python path
current_dir = Path(__file__).parent
src_path = current_dir / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

def test_imports():
    """Тестирование импортов"""
    print("Testing imports...")
    
    try:
        print("1. Importing qt_compat...")
        from wallet_sender.qt_compat import enable_high_dpi, QT_BACKEND
        print(f"   ✓ Qt backend: {QT_BACKEND}")
        
        print("2. Importing PyQt5...")
        from PyQt5.QtWidgets import QApplication, QMainWindow
        print("   ✓ PyQt5 imported")
        
        print("3. Importing main_window...")
        from wallet_sender.ui.main_window import MainWindow
        print("   ✓ MainWindow imported")
        
        print("4. Importing tabs...")
        from wallet_sender.ui.tabs import (
            AutoBuyTab,
            AutoSalesTab,
            DirectSendTab,
            MassDistributionTab,
            AnalysisTab,
            SearchTab,
            RewardsTab,
            QueueTab,
            HistoryTab,
            SettingsTab,
            FoundTxTab
        )
        print("   ✓ All tabs imported")
        
        print("\n✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        print("\nTraceback:")
        traceback.print_exc()
        return False

def test_launch():
    """Тестовый запуск приложения"""
    print("\n" + "="*50)
    print("Testing application launch...")
    print("="*50 + "\n")
    
    try:
        from wallet_sender.qt_compat import enable_high_dpi
        from PyQt5.QtWidgets import QApplication
        from wallet_sender.ui.main_window import MainWindow
        from wallet_sender import __version__
        from wallet_sender.utils.logger import setup_logger
        
        logger = setup_logger("Test", "test.log")
        logger.info(f"Starting test for WalletSender v{__version__}")
        
        # Включаем High DPI
        enable_high_dpi()
        
        # Создаем приложение
        app = QApplication(sys.argv)
        
        # Создаем главное окно
        window = MainWindow()
        window.show()
        
        print("✅ Application launched successfully!")
        print("Window should be visible now.")
        
        # Запускаем event loop
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"\n❌ Launch failed: {e}")
        print("\nTraceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Сначала тестируем импорты
    if test_imports():
        # Если импорты успешны, пробуем запустить
        test_launch()
    else:
        print("\nCannot launch application due to import errors.")
        sys.exit(1)
