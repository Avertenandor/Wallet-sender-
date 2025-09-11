#!/usr/bin/env python3
"""
Тестовый скрипт для воспроизведения ошибки QColor
"""

import sys
import os
from pathlib import Path

# Добавляем путь к src
current_dir = Path(__file__).parent
src_path = current_dir / "src"
sys.path.insert(0, str(src_path))

try:
    print("[TEST] Импорт модулей...")
    
    # Импортируем основные модули
    from wallet_sender.ui.tabs.auto_sales_tab import AutoSalesTab
    from wallet_sender.services.dex_swap_service_async import DexSwapServiceAsync
    from wallet_sender.core.web3_provider import Web3Provider
    from PyQt5.QtWidgets import QApplication, QMainWindow
    
    print("[OK] Модули импортированы успешно")
    
    # Создаем приложение Qt
    app = QApplication(sys.argv)
    window = QMainWindow()
    
    print("[TEST] Имитация операции продажи...")
    
    # Попробуем найти код, который может вызывать QColor
    # Скорее всего ошибка в методе обновления UI после продажи
    
    # Создаем tab
    sales_tab = AutoSalesTab(main_window=window)
    
    print("[OK] AutoSalesTab создан")
    
    # Попробуем найти методы, которые могут использовать QColor
    methods_to_check = [
        '_update_ui_after_sale',
        '_highlight_successful_sale', 
        '_update_status_color',
        '_set_row_color',
        'update_table_row_color'
    ]
    
    for method_name in methods_to_check:
        if hasattr(sales_tab, method_name):
            print(f"[FOUND] Метод {method_name} найден в AutoSalesTab")
        else:
            print(f"[NOT_FOUND] Метод {method_name} не найден")
    
    # Проверим все методы, содержащие 'color'
    all_methods = [method for method in dir(sales_tab) if not method.startswith('_') and 'color' in method.lower()]
    if all_methods:
        print(f"[INFO] Методы с 'color': {all_methods}")
    else:
        print("[INFO] Методы с 'color' не найдены")
    
    print("[SUCCESS] Тест завершен без критических ошибок")
    
except Exception as e:
    print(f"[ERROR] Ошибка в тесте: {e}")
    import traceback
    traceback.print_exc()
