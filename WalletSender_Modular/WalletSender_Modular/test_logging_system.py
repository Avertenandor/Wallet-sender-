#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование единой системы логирования WalletSender v2.4.9
"""

import sys
import time
from pathlib import Path

# Добавляем src в path
current_dir = Path(__file__).parent
src_path = current_dir / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

def test_logging_system():
    """Тест единой системы логирования"""
    print("=" * 60)
    print("[SEARCH] ТЕСТИРОВАНИЕ СИСТЕМЫ ЛОГИРОВАНИЯ")
    print("=" * 60)
    
    from PyQt5.QtWidgets import QApplication
    from wallet_sender.ui.main_window import MainWindow
    
    # Создаем приложение
    app = QApplication(sys.argv)
    
    # Создаем главное окно
    window = MainWindow()
    window.show()
    
    print("\n[OK] Главное окно создано")
    
    # Тест 1: Добавление логов в главное окно
    print("\n📝 Тест 1: Добавление логов в главное окно...")
    window.add_log("Тестовое сообщение INFO", "INFO")
    window.add_log("Тестовое сообщение SUCCESS", "SUCCESS")
    window.add_log("Тестовое сообщение WARNING", "WARNING")
    window.add_log("Тестовое сообщение ERROR", "ERROR")
    
    # Проверяем содержимое главного окна
    main_log_content = window.log_area.toPlainText()
    if "Тестовое сообщение INFO" in main_log_content:
        print("  [OK] Логи добавлены в главное окно")
    else:
        print("  [ERROR] Логи НЕ добавлены в главное окно")
    
    # Тест 2: Открытие отдельного окна логов
    print("\n📝 Тест 2: Отдельное окно логов...")
    window.open_log_window()
    
    if window.log_window:
        print("  [OK] Отдельное окно логов создано")
        
        # Даем время на синхронизацию
        app.processEvents()
        time.sleep(0.2)
        app.processEvents()
        
        # Проверяем синхронизацию
        log_window_content = window.log_window.log_text.toPlainText()
        if "Тестовое сообщение INFO" in log_window_content:
            print("  [OK] Логи синхронизированы с отдельным окном")
        else:
            print("  [ERROR] Логи НЕ синхронизированы с отдельным окном")
    else:
        print("  [ERROR] Отдельное окно логов НЕ создано")
    
    # Тест 3: Открытие плавающего окна логов
    print("\n📝 Тест 3: Плавающее окно логов...")
    window.open_floating_log()
    
    if window.floating_log:
        print("  [OK] Плавающее окно логов создано")
        
        # Даем время на синхронизацию
        app.processEvents()
        time.sleep(0.2)
        app.processEvents()
        
        # Проверяем синхронизацию
        floating_log_content = window.floating_log.log_text.toPlainText()
        if "Тестовое сообщение INFO" in floating_log_content:
            print("  [OK] Логи синхронизированы с плавающим окном")
        else:
            print("  [ERROR] Логи НЕ синхронизированы с плавающим окном")
    else:
        print("  [ERROR] Плавающее окно логов НЕ создано")
    
    # Тест 4: Добавление новых логов и проверка синхронизации
    print("\n📝 Тест 4: Синхронизация новых логов...")
    window.add_log("Новое сообщение после открытия окон", "SUCCESS")
    
    # Даем время на синхронизацию
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    
    # Проверяем во всех окнах
    main_has_new = "Новое сообщение после открытия окон" in window.log_area.toPlainText()
    log_window_has_new = False
    floating_has_new = False
    
    if window.log_window:
        log_window_has_new = "Новое сообщение после открытия окон" in window.log_window.log_text.toPlainText()
    
    if window.floating_log:
        floating_has_new = "Новое сообщение после открытия окон" in window.floating_log.log_text.toPlainText()
    
    print(f"  Главное окно: {'[OK]' if main_has_new else '[ERROR]'}")
    print(f"  Отдельное окно: {'[OK]' if log_window_has_new else '[ERROR]'}")
    print(f"  Плавающее окно: {'[OK]' if floating_has_new else '[ERROR]'}")
    
    # Тест 5: Логи из вкладки
    print("\n📝 Тест 5: Логи из вкладки автопокупок...")
    if hasattr(window, 'auto_buy_tab'):
        # Имитируем лог из вкладки
        window.auto_buy_tab.log("Тестовый лог из вкладки автопокупок", "INFO")
        
        # Даем время на обработку
        app.processEvents()
        time.sleep(0.3)
        app.processEvents()
        
        # Проверяем во всех окнах
        tab_log_in_main = "Тестовый лог из вкладки автопокупок" in window.log_area.toPlainText()
        tab_log_in_window = False
        tab_log_in_floating = False
        
        if window.log_window:
            tab_log_in_window = "Тестовый лог из вкладки автопокупок" in window.log_window.log_text.toPlainText()
        
        if window.floating_log:
            tab_log_in_floating = "Тестовый лог из вкладки автопокупок" in window.floating_log.log_text.toPlainText()
        
        print(f"  Главное окно: {'[OK]' if tab_log_in_main else '[ERROR]'}")
        print(f"  Отдельное окно: {'[OK]' if tab_log_in_window else '[ERROR]'}")
        print(f"  Плавающее окно: {'[OK]' if tab_log_in_floating else '[ERROR]'}")
    else:
        print("  [WARN] Вкладка автопокупок не найдена")
    
    # Итоги
    print("\n" + "=" * 60)
    print("[STATS] ИТОГИ ТЕСТИРОВАНИЯ:")
    print("=" * 60)
    
    all_tests_passed = (
        main_has_new and 
        (not window.log_window or log_window_has_new) and 
        (not window.floating_log or floating_has_new)
    )
    
    if all_tests_passed:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("[OK] Единая система логирования работает корректно")
        print("[OK] Все окна синхронизированы")
    else:
        print("[WARN] Некоторые тесты не прошли")
        print("[ERROR] Требуется дополнительная настройка")
    
    print("=" * 60)
    
    # Запускаем приложение для визуальной проверки
    print("\n👁️ Окна оставлены открытыми для визуальной проверки")
    print("Закройте приложение для завершения теста")
    
    return app.exec_()

if __name__ == "__main__":
    sys.exit(test_logging_system())
