#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WalletSender Modular - Главная точка входа приложения
Версия: 2.3.0
Дата: 6 сентября 2025
"""

import sys
import logging
from pathlib import Path
# Добавляем src в Python path (для запуска из корня проекта)
current_dir = Path(__file__).parent
src_path = current_dir / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Импорты Qt и модулей приложения (PyQt5)
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt
from wallet_sender import __version__
from wallet_sender.utils.logger import setup_logger


def main() -> int:
    """Главная функция приложения.

    Возвращает код выхода для sys.exit.
    """
    logger: logging.Logger = setup_logger("WalletSender_Modular", "wallet_sender_modular.log")
    logger.info(f"🚀 Запуск WalletSender Modular v{__version__}")
    logger.info("Qt бэкенд: PyQt5")

    try:
        # Включаем поддержку High DPI для PyQt5
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        # Создаем приложение Qt
        app = QApplication(sys.argv)

        # Применяем темную тему, если доступна
        try:
            import qdarkstyle  # type: ignore[import]
            # Рекомендуется использовать стиль Fusion перед qdarkstyle
            app.setStyle('Fusion')
            app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
            logger.info("🎨 Dark theme applied (qdarkstyle + Fusion).")
        except Exception as e:
            logger.warning(f"Не удалось применить темную тему: {e}")

        # Создаем и показываем главное окно (ленивый импорт после QApplication)
        from wallet_sender.ui.main_window import MainWindow
        window = MainWindow()
        window.show()
        logger.info("✅ Главное окно создано и отображено")

        # Запуск цикла событий (совместимость PyQt5/PyQt6)
        run_loop = getattr(app, 'exec', None) or getattr(app, 'exec_', None)
        if run_loop is None:
            raise RuntimeError('Не найден метод запуска цикла событий Qt')
        return run_loop()

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        try:
            QMessageBox.critical(
                None,
                "Критическая ошибка",
                f"Не удалось запустить приложение:\n{e}"
            )
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
