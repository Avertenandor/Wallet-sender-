#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализатор и исправитель ошибок Pylance для WalletSender
Этот скрипт анализирует типичные проблемы Pylance и предлагает исправления
"""

import os
import json
from datetime import datetime

def analyze_pylance_errors():
    """Анализирует типичные ошибки Pylance в Python коде"""
    
    filename = "WalletSender — копия.py"
    
    print("="*60)
    print("АНАЛИЗ ОШИБОК PYLANCE В ФАЙЛЕ:", filename)
    print("="*60)
    
    if not os.path.exists(filename):
        print(f"❌ Файл {filename} не найден!")
        return
    
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Счетчики проблем
    issues = {
        'type_annotations': [],
        'undefined_vars': [],
        'import_errors': [],
        'optional_types': [],
        'any_types': []
    }
    
    # Анализ построчно
    for i, line in enumerate(lines, 1):
        line_stripped = line.strip()
        
        # 1. Проверка на отсутствие type hints в функциях
        if line_stripped.startswith('def ') and ':' not in line_stripped.split('(')[1].split(')')[0]:
            if 'self' not in line_stripped:  # Пропускаем методы класса
                issues['type_annotations'].append({
                    'line': i,
                    'code': line_stripped,
                    'issue': 'Функция без type hints',
                    'fix': 'Добавьте типы параметров и возвращаемого значения'
                })
        
        # 2. Проверка на использование None без Optional
        if '= None' in line and 'Optional' not in line and 'type:' not in line:
            issues['optional_types'].append({
                'line': i,
                'code': line_stripped,
                'issue': 'Использование None без Optional типа',
                'fix': 'Используйте Optional[Type] для параметров с None'
            })
        
        # 3. Проверка на переменные объявленные как None
        if ' = None' in line and not line_stripped.startswith('#'):
            var_name = line_stripped.split('=')[0].strip()
            if var_name and not ':' in var_name:
                issues['undefined_vars'].append({
                    'line': i,
                    'code': line_stripped,
                    'issue': f'Переменная {var_name} без типизации',
                    'fix': f'Добавьте тип: {var_name}: Optional[Any] = None'
                })
        
        # 4. Проверка на проблемные импорты
        if 'from web3' in line or 'import web3' in line:
            if '# type: ignore' not in line:
                issues['import_errors'].append({
                    'line': i,
                    'code': line_stripped,
                    'issue': 'Импорт web3 может вызвать ошибки типизации',
                    'fix': 'Добавьте # type: ignore в конец строки'
                })
        
        # 5. Проверка на использование Any
        if ': Any' in line:
            issues['any_types'].append({
                'line': i,
                'code': line_stripped,
                'issue': 'Использование Any типа',
                'fix': 'По возможности замените на более конкретный тип'
            })
    
    # Вывод результатов
    print("\n📊 РЕЗУЛЬТАТЫ АНАЛИЗА:")
    print("-"*60)
    
    total_issues = 0
    
    for category, items in issues.items():
        if items:
            print(f"\n🔍 {category.upper()} ({len(items)} проблем):")
            # Показываем первые 3 примера каждой категории
            for item in items[:3]:
                print(f"  Строка {item['line']}: {item['issue']}")
                print(f"    Код: {item['code'][:60]}...")
                print(f"    Исправление: {item['fix']}")
            if len(items) > 3:
                print(f"  ... и еще {len(items) - 3} проблем")
            total_issues += len(items)
    
    print("\n" + "="*60)
    print(f"ВСЕГО НАЙДЕНО ПРОБЛЕМ: {total_issues}")
    print("="*60)
    
    # Сохранение отчета
    report = {
        'timestamp': datetime.now().isoformat(),
        'file': filename,
        'total_issues': total_issues,
        'issues': issues
    }
    
    report_file = f"pylance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 Отчет сохранен в: {report_file}")
    
    # Рекомендации
    print("\n💡 РЕКОМЕНДАЦИИ ДЛЯ ИСПРАВЛЕНИЯ:")
    print("-"*60)
    print("1. Добавьте в начало файла:")
    print("   from typing import Dict, List, Tuple, Optional, Any, Union")
    print("\n2. Для переменных инициализированных как None:")
    print("   Замените: variable = None")
    print("   На: variable: Optional[Type] = None")
    print("\n3. Для проблемных импортов добавляйте:")
    print("   import module  # type: ignore")
    print("\n4. Для функций добавляйте type hints:")
    print("   def func(param: Type) -> ReturnType:")
    print("\n5. Используйте pyright или mypy для более детальной проверки типов")
    
    return total_issues

def create_type_stub():
    """Создает заглушку типов для проблемных модулей"""
    
    stub_content = '''"""
Type stubs для WalletSender
Этот файл помогает Pylance правильно определять типы
"""

from typing import Any, Optional, Dict, List, Tuple, Union, Callable

# Web3 типы
class Web3:
    eth: Any
    is_connected: Callable[[], bool]
    middleware_onion: Any
    
class HTTPProvider:
    def __init__(self, url: str, request_kwargs: Optional[Dict] = None) -> None: ...

# Middleware типы
geth_poa_middleware: Optional[Any] = None

# Account типы
class Account:
    @staticmethod
    def enable_unaudited_hdwallet_features() -> None: ...
    
    @staticmethod
    def from_key(private_key: str) -> Any: ...

# Contract типы
class Contract:
    functions: Any
    
# Transaction типы
TxReceipt = Dict[str, Any]
TxHash = str

# BSC константы
PLEX_CONTRACT: str = "0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1"
USDT_CONTRACT: str = "0x55d398326f99059ff775485246999027b3197955"

# ERC20 ABI
ERC20_ABI: List[Dict[str, Any]] = []
'''
    
    stub_file = "wallet_sender_types.pyi"
    with open(stub_file, 'w', encoding='utf-8') as f:
        f.write(stub_content)
    
    print(f"\n✅ Создан файл заглушек типов: {stub_file}")
    print("   Добавьте в начало WalletSender файла:")
    print(f"   # type: ignore[import]")
    print(f"   from wallet_sender_types import *")

def create_pyrightconfig():
    """Создает конфигурацию для Pyright/Pylance"""
    
    config = {
        "include": [
            "*.py"
        ],
        "exclude": [
            "**/node_modules",
            "**/__pycache__",
            "venv",
            ".venv"
        ],
        "reportMissingImports": "warning",
        "reportMissingTypeStubs": "warning",
        "reportUnknownMemberType": "warning",
        "reportUnknownVariableType": "warning",
        "reportUnknownArgumentType": "warning",
        "reportGeneralTypeIssues": "warning",
        "reportOptionalCall": "warning",
        "reportOptionalIterable": "warning",
        "reportOptionalMemberAccess": "warning",
        "reportOptionalOperand": "warning",
        "reportOptionalSubscript": "warning",
        "pythonVersion": "3.8",
        "typeCheckingMode": "basic"
    }
    
    config_file = "pyrightconfig.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✅ Создан файл конфигурации Pyright: {config_file}")
    print("   Это поможет настроить Pylance для более корректной работы")

if __name__ == "__main__":
    print("\n🔧 АНАЛИЗАТОР ОШИБОК PYLANCE")
    print("="*60)
    
    # Анализ ошибок
    total_issues = analyze_pylance_errors()
    
    # Создание вспомогательных файлов
    if total_issues > 0:
        print("\n📦 СОЗДАНИЕ ВСПОМОГАТЕЛЬНЫХ ФАЙЛОВ...")
        create_type_stub()
        create_pyrightconfig()
        
        print("\n✅ ГОТОВО!")
        print("="*60)
        print("Теперь:")
        print("1. Запустите fix_type_hints.py для автоматических исправлений")
        print("2. Перезагрузите VSCode для применения новой конфигурации")
        print("3. Проверьте оставшиеся ошибки вручную")
