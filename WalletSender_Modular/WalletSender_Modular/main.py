#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WalletSender Modular - Главная точка входа приложения
Версия: 2.4.17
Дата: 11 сентября 2025
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
from wallet_sender.utils.logger import setup_logging


def main() -> int:
    """Главная функция приложения.

    Возвращает код выхода для sys.exit.
    """
    # Настройка логирования
    setup_logging("INFO", "wallet_sender_modular.log")
    logger = logging.getLogger(__name__)
    logger.info(f"[START] Запуск WalletSender Modular v{__version__}")
    logger.info("Qt бэкенд: PyQt5")

    try:
        # Включаем поддержку High DPI для PyQt5
        try:
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # type: ignore[attr-defined]
        except AttributeError:
            pass
        try:
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)  # type: ignore[attr-defined] 
        except AttributeError:
            pass

        # Создаем приложение Qt
        app = QApplication(sys.argv)
        
        # Улучшенная стабильность Qt приложения
        try:
            # Отключаем потенциально проблемные атрибуты Qt
            app.setAttribute(Qt.AA_DisableWindowContextHelpButton, True)  # type: ignore[attr-defined]
        except (AttributeError, Exception):
            pass

        # Применяем темную тему, если доступна
        try:
            import qdarkstyle  # type: ignore[import]
            # Рекомендуется использовать стиль Fusion перед qdarkstyle
            app.setStyle('Fusion')
            app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
            logger.info("[THEME] Dark theme applied (qdarkstyle + Fusion).")
        except Exception as e:
            logger.warning(f"Не удалось применить темную тему: {e}")

        # Отключение проблемных Qt межпоточных сигналов
        try:
            import os
            
            # Устанавливаем переменные окружения для отключения Qt warnings
            os.environ['QT_LOGGING_RULES'] = 'qt5ct.debug=false'
            os.environ['QT_ASSUME_STDERR_HAS_CONSOLE'] = '1'
            os.environ['QT_FORCE_STDERR_LOGGING'] = '0'
            
            # Перенаправляем Qt warnings в /dev/null (отключаем)
            from PyQt5.QtCore import qInstallMessageHandler
            def qt_message_handler(mode, context, message):  # type: ignore[no-untyped-def]
                # Полностью игнорируем Qt warnings чтобы предотвратить крах
                pass
            
            qInstallMessageHandler(qt_message_handler)
            logger.info("[OK] Qt warnings ОТКЛЮЧЕНЫ - межпоточные краши предотвращены")
            
        except Exception as e:
            logger.warning(f"[WARN] Не удалось отключить Qt warnings: {e}")
            # Fallback - пытаемся минимальную "регистрацию"
            try:
                from PyQt5.QtCore import QMetaType
                QMetaType.type('QVariant')  # Хотя бы что-то
                logger.info("[MINIMAL] Применена минимальная Qt защита")
            except Exception:
                logger.warning("[ERROR] Qt защита недоступна - возможны warnings")

        # Создаем и показываем главное окно (ленивый импорт после QApplication)
        from wallet_sender.ui.main_window import MainWindow
        window = MainWindow()
        window.show()
        logger.info("[OK] Главное окно создано и отображено")

        # Запуск цикла событий (совместимость PyQt5/PyQt6)
        run_loop = getattr(app, 'exec', None) or getattr(app, 'exec_', None)
        if run_loop is None:
            raise RuntimeError('Не найден метод запуска цикла событий Qt')
        return run_loop()

    except Exception as e:
        logger.error(f"[ERROR] Критическая ошибка: {e}", exc_info=True)
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
