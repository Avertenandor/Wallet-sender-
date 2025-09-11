#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WalletSender Modular - Package entry point
Позволяет запускать приложение как: python -m wallet_sender
"""

import sys
from pathlib import Path

# Добавляем текущую директорию в Python path если запускаем как модуль
current_dir = Path(__file__).parent.parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


def main():
    """Entry point for python -m wallet_sender"""
    # Импортируем main из корневого main.py
    try:
        # Пытаемся импортировать из корня проекта
        main_module_path = current_dir / "main.py"
        if main_module_path.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("main_module", main_module_path)
            if spec and spec.loader:
                main_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(main_module)
                return main_module.main()
        
        # Fallback - прямой импорт если структура изменилась
        from ...main import main as main_func
        return main_func()
        
    except Exception as e:
        print(f"[ERROR] Ошибка запуска через модуль: {e}")
        print("💡 Попробуйте запустить через: python main.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
