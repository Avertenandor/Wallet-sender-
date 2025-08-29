#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WalletSender Modular - Production Version
Версия: 2.0.0
Автор: Production Team
Дата: 29 августа 2025
"""

import sys
import os
from pathlib import Path

# Добавляем src в Python path
current_dir = Path(__file__).parent
src_path = current_dir / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

def check_dependencies():
    """Проверка зависимостей"""
    missing_deps = []
    
    # Проверяем основные зависимости
    try:
        import PyQt5
    except ImportError:
        missing_deps.append("PyQt5")
        
    try:
        import web3
    except ImportError:
        missing_deps.append("web3")
        
    try:
        import eth_account
    except ImportError:
        missing_deps.append("eth-account")
        
    try:
        import sqlalchemy
    except ImportError:
        missing_deps.append("sqlalchemy")
        
    if missing_deps:
        print("❌ Отсутствуют необходимые зависимости:")
        print(f"   {', '.join(missing_deps)}")
        print("\n📦 Установите их командой:")
        print("   pip install -r requirements.txt")
        return False
        
    return True

def main():
    """Главная функция приложения"""
    
    # Проверка зависимостей
    if not check_dependencies():
        sys.exit(1)
        
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox, QSplashScreen
        from PyQt5.QtCore import Qt, QTimer
        from PyQt5.QtGui import QPixmap, QFont
        
        # Настройка для HiDPI дисплеев
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        
        # Установка атрибутов приложения
        try:
            # Для PyQt5 >= 5.14
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        except AttributeError:
            # Для старых версий PyQt5
            try:
                QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
                QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
            except:
                pass  # Игнорируем если атрибуты недоступны
        
        # Создание приложения
        app = QApplication(sys.argv)
        app.setApplicationName("WalletSender Modular")
        app.setOrganizationName("Production Team")
        
        # Установка стиля
        try:
            import qdarkstyle
            app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
            print("✅ Темная тема загружена")
        except ImportError:
            print("⚠️ qdarkstyle не установлен, используется стандартная тема")
            # Применяем базовый темный стиль
            app.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                }
                QWidget {
                    background-color: #3c3c3c;
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #4a4a4a;
                    border: 1px solid #5a5a5a;
                    padding: 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #5a5a5a;
                }
                QPushButton:pressed {
                    background-color: #3a3a3a;
                }
                QLineEdit, QTextEdit, QPlainTextEdit {
                    background-color: #2b2b2b;
                    border: 1px solid #5a5a5a;
                    padding: 3px;
                }
                QTabWidget::pane {
                    border: 1px solid #5a5a5a;
                    background-color: #3c3c3c;
                }
                QTabBar::tab {
                    background-color: #4a4a4a;
                    padding: 5px 10px;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background-color: #5a5a5a;
                }
                QGroupBox {
                    border: 1px solid #5a5a5a;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
            """)
        
        # Создание splash screen
        splash = QSplashScreen()
        splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # Создаем простой splash с текстом
        pixmap = QPixmap(600, 400)
        pixmap.fill(Qt.black)
        splash.setPixmap(pixmap)
        
        # Добавляем текст на splash
        font = QFont("Arial", 24, QFont.Bold)
        splash.setFont(font)
        splash.showMessage(
            "WalletSender Modular v2.0\nProduction Edition\n\nЗагрузка...",
            Qt.AlignCenter,
            Qt.white
        )
        splash.show()
        
        # Обрабатываем события для отображения splash
        app.processEvents()
        
        # Импортируем главное окно
        try:
            from wallet_sender.ui.main_window import MainWindow
            print("✅ MainWindow успешно импортирован")
        except ImportError as e:
            print(f"❌ Ошибка импорта MainWindow: {e}")
            QMessageBox.critical(None, "Ошибка", f"Не удалось загрузить главное окно:\n{e}")
            sys.exit(1)
        
        # Создаем главное окно
        try:
            window = MainWindow()
            print("✅ Главное окно создано")
        except Exception as e:
            print(f"❌ Ошибка создания главного окна: {e}")
            QMessageBox.critical(None, "Ошибка", f"Не удалось создать главное окно:\n{e}")
            sys.exit(1)
        
        # Скрываем splash и показываем главное окно
        QTimer.singleShot(2000, lambda: [
            splash.close(),
            window.show(),
            window.raise_(),
            window.activateWindow()
        ])
        
        print("🚀 WalletSender Modular v2.0 запущен!")
        print("=" * 50)
        
        # Запуск приложения
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            from PyQt5.QtWidgets import QApplication, QMessageBox
            if QApplication.instance():
                QMessageBox.critical(
                    None, 
                    "Критическая ошибка", 
                    f"Не удалось запустить приложение:\n{e}\n\n"
                    f"Проверьте логи для подробной информации."
                )
        except:
            pass
            
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 50)
    print("WalletSender Modular v2.0 - Production Edition")
    print("=" * 50)
    main()
