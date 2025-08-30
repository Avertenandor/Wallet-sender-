#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для запуска WalletSender Modular с проверкой зависимостей
"""

import sys
import os
from pathlib import Path

def check_dependencies():
    """Проверка установленных зависимостей"""
    print("=" * 60)
    print("ПРОВЕРКА ЗАВИСИМОСТЕЙ")
    print("=" * 60)
    
    required_packages = {
        'PyQt5': 'PyQt5',
        'web3': 'Web3',
        'eth_account': 'eth-account',
        'pandas': 'pandas',
        'qdarkstyle': 'qdarkstyle',
        'aiohttp': 'aiohttp',
        'requests': 'requests',
        'sqlalchemy': 'SQLAlchemy'
    }
    
    missing = []
    
    for module, package in required_packages.items():
        try:
            __import__(module)
            print(f"✅ {package} установлен")
        except ImportError:
            print(f"❌ {package} НЕ установлен")
            missing.append(package)
    
    if missing:
        print("\n❗ Установите недостающие пакеты:")
        print(f"pip install {' '.join(missing)}")
        return False
    
    print("\n✅ Все зависимости установлены")
    return True

def setup_environment():
    """Настройка окружения"""
    # Добавляем src в Python path
    current_dir = Path(__file__).parent
    src_path = current_dir / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    # Создаем необходимые директории
    dirs_to_create = [
        current_dir / "logs",
        current_dir / "data",
        current_dir / "backups",
        current_dir / "rewards_configs"
    ]
    
    for dir_path in dirs_to_create:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    print("✅ Окружение настроено")

def create_default_config():
    """Создание конфигурации по умолчанию"""
    config_path = Path(__file__).parent / "config.json"
    
    if not config_path.exists():
        import json
        
        default_config = {
            "version": "2.0.0",
            "network": "bsc_mainnet",
            "rpc_urls": {
                "bsc_mainnet": "https://bsc-dataseed.binance.org/",
                "bsc_testnet": "https://data-seed-prebsc-1-s1.binance.org:8545/"
            },
            "bscscan_api_keys": [
                "RF1Q8SCFHFD1EVAP5A4WCMIM4DREA7UNUH",
                "U89HXHR9Y26CHMWAA9JUZ17YK2AAXS65CZ",
                "RAI3FTD9W53JPYZ2AHW8IBH9BXUC71NRH1"
            ],
            "gas_settings": {
                "default_gas_price": 5,
                "default_gas_limit": 100000,
                "auto_estimate": False
            },
            "tokens": {
                "PLEX ONE": "0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1",
                "USDT": "0x55d398326f99059ff775485246999027b3197955"
            },
            "ui": {
                "theme": "dark",
                "language": "ru",
                "window_width": 1400,
                "window_height": 900
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        print("✅ Создан файл конфигурации по умолчанию")
    else:
        print("✅ Файл конфигурации существует")

def main():
    """Главная функция"""
    print("🚀 ЗАПУСК WALLETSENDER MODULAR")
    print("=" * 60)
    
    # Проверка зависимостей
    if not check_dependencies():
        print("\n❌ Установите недостающие зависимости перед запуском!")
        input("\nНажмите Enter для выхода...")
        return 1
    
    print("\n" + "=" * 60)
    print("НАСТРОЙКА ПРИЛОЖЕНИЯ")
    print("=" * 60)
    
    # Настройка окружения
    setup_environment()
    
    # Создание конфигурации
    create_default_config()
    
    print("\n" + "=" * 60)
    print("ЗАПУСК ПРИЛОЖЕНИЯ")
    print("=" * 60)
    
    try:
        # Импортируем и запускаем приложение
        from wallet_sender.qt_compat import enable_high_dpi, QT_BACKEND
        from PyQt5.QtWidgets import QApplication, QMessageBox
        from PyQt5.QtCore import Qt
        import qdarkstyle
        
        from wallet_sender.ui.main_window import MainWindow
        from wallet_sender import __version__
        from wallet_sender.utils.logger import setup_logger
        
        # Настройка логгера
        logger = setup_logger("WalletSender_Modular", "wallet_sender_modular.log")
        logger.info(f"🚀 Запуск WalletSender Modular v{__version__}")
        logger.info(f"Qt бэкенд: {QT_BACKEND}")
        
        # Включаем поддержку High DPI
        enable_high_dpi()
        
        # Создание приложения Qt
        app = QApplication(sys.argv)
        
        # Применение темной темы
        try:
            app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
            print("✅ Темная тема применена")
        except Exception as e:
            print(f"⚠️ Не удалось применить тему: {e}")
        
        # Создание главного окна
        print("Создание главного окна...")
        window = MainWindow()
        window.show()
        
        print("✅ Приложение запущено успешно!")
        print("\n" + "=" * 60)
        print("Приложение работает. Закройте окно для выхода.")
        print("=" * 60)
        
        # Запуск цикла событий
        return app.exec_()
        
    except ImportError as e:
        print(f"\n❌ Ошибка импорта: {e}")
        print("Проверьте структуру файлов проекта")
        input("\nНажмите Enter для выхода...")
        return 1
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            if 'app' in locals():
                QMessageBox.critical(None, "Критическая ошибка", 
                                   f"Не удалось запустить приложение:\n{e}")
        except:
            pass
        
        input("\nНажмите Enter для выхода...")
        return 1

if __name__ == "__main__":
    sys.exit(main())
