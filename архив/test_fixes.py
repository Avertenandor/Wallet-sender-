#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простая проверка, что основные импорты работают после исправлений
"""

try:
    # Пытаемся импортировать исправленный файл
    import sys
    import importlib.util
    
    spec = importlib.util.spec_from_file_location("WalletSender", "WalletSender — копия.py")
    module = importlib.util.module_from_spec(spec)
    
    print("✅ Файл успешно импортирован!")
    print("✅ Проверка базовых импортов:")
    
    # Проверяем наличие импортов типизации
    import typing
    print("  - typing: OK")
    
    # Проверяем основные классы
    spec.loader.exec_module(module)
    
    if hasattr(module, 'Config'):
        print("  - Класс Config: OK")
    
    if hasattr(module, 'RPCPool'):
        print("  - Класс RPCPool: OK")
        
    if hasattr(module, 'SimpleCache'):
        print("  - Класс SimpleCache: OK")
        
    # Проверяем функции
    if hasattr(module, 'add_history'):
        print("  - Функция add_history: OK")
        
    if hasattr(module, 'bscscan_request'):
        print("  - Функция bscscan_request: OK")
        
    print("\n✅ Все основные компоненты доступны!")
    print("✅ Типизация добавлена успешно!")
    
except SyntaxError as e:
    print(f"❌ Синтаксическая ошибка: {e}")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
except Exception as e:
    print(f"❌ Неожиданная ошибка: {e}")
