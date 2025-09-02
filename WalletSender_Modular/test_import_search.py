"""
Простой тест импорта search_tab
"""
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    # Проверяем что PyQt5 доступен
    from PyQt5.QtWidgets import QWidget
    print("✅ PyQt5 доступен")
    
    # Проверяем базовые импорты
    from wallet_sender.ui.tabs.base_tab import BaseTab
    print("✅ BaseTab импортирован")
    
    # Импортируем SearchTab
    from wallet_sender.ui.tabs.search_tab import SearchTab
    print("✅ SearchTab импортирован успешно!")
    
    # Проверяем что класс корректен
    assert hasattr(SearchTab, 'start_search'), "Метод start_search не найден"
    assert hasattr(SearchTab, 'stop_search'), "Метод stop_search не найден"
    assert hasattr(SearchTab, 'run_async_safe'), "Метод run_async_safe не найден"
    print("✅ Все основные методы на месте")
    
    print("\n🎉 SearchTab готов к использованию!")
    
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

sys.exit(0)
