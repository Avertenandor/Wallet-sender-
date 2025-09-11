#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправлений WalletSender v2.4.8
"""

import sys
from pathlib import Path

# Добавляем src в path
current_dir = Path(__file__).parent
src_path = current_dir / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

def test_qt_imports():
    """Тест импорта Qt атрибутов"""
    print("[SEARCH] Тестирование импортов Qt...")
    try:
        from wallet_sender.qt_compat import (
            Qt, QApplication, QMainWindow,
            QT_BACKEND, ItemFlags
        )
        
        # Проверяем наличие атрибутов
        assert hasattr(Qt, 'UserRole'), "UserRole не найден"
        assert hasattr(Qt, 'ItemIsEnabled'), "ItemIsEnabled не найден"
        assert hasattr(Qt, 'ItemIsSelectable'), "ItemIsSelectable не найден"
        assert hasattr(Qt, 'QueuedConnection'), "QueuedConnection не найден"
        
        print(f"[OK] Qt атрибуты импортированы успешно!")
        print(f"   Backend: {QT_BACKEND}")
        print(f"   UserRole: {Qt.UserRole}")
        print(f"   ItemIsEnabled: {Qt.ItemIsEnabled}")
        print(f"   ItemIsSelectable: {Qt.ItemIsSelectable}")
        print(f"   QueuedConnection: {Qt.QueuedConnection}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка импорта Qt: {e}")
        return False

def test_api_configuration():
    """Тест конфигурации API"""
    print("\n[SEARCH] Тестирование API конфигурации...")
    try:
        from wallet_sender.api.etherscan import EtherscanAPI
        from wallet_sender.api.bscscan import BSCScanAPI
        
        # Проверяем URL и chainId
        assert EtherscanAPI.BASE_URL == "https://api.etherscan.io/v2/api", "Неверный BASE_URL"
        assert EtherscanAPI.BSC_CHAIN_ID == 56, "Неверный BSC_CHAIN_ID"
        
        print("[OK] API правильно настроен для Etherscan V2")
        print(f"   URL: {EtherscanAPI.BASE_URL}")
        print(f"   BSC Chain ID: {EtherscanAPI.BSC_CHAIN_ID}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка API: {e}")
        return False

def test_logging():
    """Тест логирования с правильной кодировкой"""
    print("\n[SEARCH] Тестирование логирования...")
    try:
        from wallet_sender.utils.logger import setup_logger
        import tempfile
        import os
        
        # Создаем временный файл для логов
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name
        
        logger = setup_logger("TestLogger", log_file, "DEBUG")
        
        # Тестируем кириллицу
        test_messages = [
            "Тест кириллицы: Привет мир!",
            "Специальные символы: ₽ € $ ¥",
            "Эмодзи: [START] [OK] [ERROR] [INFO]"
        ]
        
        for msg in test_messages:
            logger.info(msg)
        
        # Читаем файл и проверяем кодировку
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            for msg in test_messages:
                assert msg in content, f"Сообщение '{msg}' не найдено в логах"
        
        # Удаляем временный файл
        os.unlink(log_file)
        
        print("[OK] Логирование работает с правильной кодировкой UTF-8")
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка логирования: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("=" * 60)
    print("[START] ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ WalletSender v2.4.8")
    print("=" * 60)
    
    results = []
    
    # Запускаем тесты
    results.append(("Qt импорты", test_qt_imports()))
    results.append(("API конфигурация", test_api_configuration()))
    results.append(("Логирование", test_logging()))
    
    # Подводим итоги
    print("\n" + "=" * 60)
    print("[STATS] РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "[OK] PASSED" if passed else "[ERROR] FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("[OK] Обе проблемы исправлены:")
        print("   1. Миграция на Etherscan API V2 - завершена")
        print("   2. Qt атрибуты исправлены")
        print("   + Бонус: Логирование с UTF-8 работает корректно")
    else:
        print("[WARN] Некоторые тесты не прошли. Требуется дополнительная проверка.")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
