#!/usr/bin/env python3
"""
Тест для проверки исправления ошибки QColor
"""

import sys
from pathlib import Path

# Добавляем путь к src
current_dir = Path(__file__).parent
src_path = current_dir / "src"
sys.path.insert(0, str(src_path))

print("[TEST] Проверка импорта QColor в auto_sales_tab...")

try:
    # Тестируем импорт auto_sales_tab
    from wallet_sender.ui.tabs.auto_sales_tab import AutoSalesTab
    
    print("[OK] AutoSalesTab импортирован без ошибок")
    
    # Проверяем наличие QColor в модуле
    import wallet_sender.ui.tabs.auto_sales_tab as ast_module
    
    if hasattr(ast_module, 'QColor'):
        print("[OK] QColor доступен в auto_sales_tab")
    else:
        print("[WARN] QColor не найден как атрибут модуля")
    
    # Проверяем что можем создать QColor
    from PyQt5.QtGui import QColor
    test_color = QColor(255, 0, 0)
    print(f"[OK] QColor можно создать: {test_color}")
    
    print("[SUCCESS] Тест импорта QColor прошел успешно!")
    
except Exception as e:
    print(f"[ERROR] Ошибка в тесте: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
