#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WalletSender Modular - Главная точка входа приложения
Версия: 2.0
Дата: 29 августа 2025
"""

import sys
from pathlib import Path

# Добавляем src в Python path
current_dir = Path(__file__).parent
src_path = current_dir / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Импорты модулей
try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from PyQt5.QtCore import Qt
    import qdarkstyle
    
    from wallet_sender.ui.main_window import MainWindow
    from wallet_sender import __version__
    from wallet_sender.utils.logger import setup_logger
    
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь что установлены все зависимости:")
    print("pip install -r requirements.txt")
    sys.exit(1)

def main():
    """Главная функция приложения"""
    # Настройка логгера
    logger = setup_logger("WalletSender_Modular", "wallet_sender_modular.log")
    logger.info(f"🚀 Запуск WalletSender Modular v{__version__}")
    
    try:
        # Атрибуты HighDPI должны быть установлены до создания QApplication
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        # Создание приложения Qt
        app = QApplication(sys.argv)
        
        # Применение темной темы (без падения при отсутствии)
        try:
            app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        except Exception:
            pass
        
        # Создание главного окна
        window = MainWindow()
        window.show()
        
        logger.info("✅ Главное окно создано и отображено")
        
        # Запуск цикла событий
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        if 'app' in locals():
            QMessageBox.critical(None, "Критическая ошибка", 
                               f"Не удалось запустить приложение:\n{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
