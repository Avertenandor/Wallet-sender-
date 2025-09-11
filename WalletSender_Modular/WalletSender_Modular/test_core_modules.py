#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки работоспособности core модулей WalletSender
"""

import sys
import asyncio
from pathlib import Path

# Добавляем src в Python path
current_dir = Path(__file__).parent
src_path = current_dir / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

def test_imports():
    """Тестирование импортов"""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ИМПОРТОВ")
    print("=" * 60)
    
    modules_to_test = [
        ('wallet_sender.core.store', 'Store'),
        ('wallet_sender.core.rpc', 'RPCPool'),
        ('wallet_sender.core.job_engine', 'JobEngine'),
        ('wallet_sender.qt_compat', 'QT_BACKEND'),
        ('wallet_sender.utils.logger', 'setup_logger'),
        ('wallet_sender.api.etherscan', 'EtherscanAPI'),
    ]
    
    success = 0
    failed = 0
    
    for module_name, attr_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[attr_name])
            attr = getattr(module, attr_name)
            print(f"[OK] {module_name}.{attr_name} - OK")
            success += 1
        except ImportError as e:
            print(f"[ERROR] {module_name} - ОШИБКА ИМПОРТА: {e}")
            failed += 1
        except AttributeError as e:
            print(f"[ERROR] {module_name}.{attr_name} - НЕ НАЙДЕН: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {module_name} - НЕОЖИДАННАЯ ОШИБКА: {e}")
            failed += 1
    
    print(f"\nРезультат: {success} успешно, {failed} ошибок")
    return failed == 0

def test_store():
    """Тестирование Store"""
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ STORE")
    print("=" * 60)
    
    try:
        from wallet_sender.core.store import Store
        
        # Создаем временную БД
        store = Store(":memory:")
        print("[OK] Store создан")
        
        # Тест настроек
        settings = {"test_key": "test_value", "nested": {"key": "value"}}
        store.save_settings(settings)
        loaded = store.load_settings()
        assert loaded["test_key"] == "test_value"
        assert loaded["nested"]["key"] == "value"
        print("[OK] Настройки сохранены и загружены")
        
        # Тест задач
        job_id = store.create_job("Test Job", "test", {"param": "value"})
        assert job_id > 0
        print(f"[OK] Создана задача #{job_id}")
        
        job = store.get_job(job_id)
        assert job is not None
        assert job["title"] == "Test Job"
        print("[OK] Задача загружена")
        
        # Тест транзакций
        tx_id = store.add_transaction(
            tx_hash="0x123",
            from_address="0xabc",
            to_address="0xdef",
            amount=100.0,
            status="pending"
        )
        assert tx_id > 0
        print(f"[OK] Добавлена транзакция #{tx_id}")
        
        # Тест поиска
        results = store.search_transactions("0x123")
        print(f"[OK] Поиск работает, найдено: {len(results)} транзакций")
        
        # Тест статистики
        stats = store.get_statistics()
        print(f"[OK] Статистика: {stats}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка тестирования Store: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_rpc():
    """Тестирование RPC Pool"""
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ RPC POOL")
    print("=" * 60)
    
    try:
        from wallet_sender.core.rpc import RPCPool
        
        # Создаем пул
        pool = RPCPool()
        print(f"[OK] RPC Pool создан с {len(pool.endpoints)} endpoints")
        
        # Тест статистики
        stats = pool.get_statistics()
        print(f"[OK] Статистика пула: {stats}")
        
        # Тест получения Web3 (может не работать без интернета)
        try:
            w3 = pool.get_web3()
            if w3:
                print(f"[OK] Web3 подключен")
                if w3.is_connected():
                    block = w3.eth.block_number
                    print(f"[OK] Текущий блок: {block}")
            else:
                print("[WARN] Не удалось получить Web3 соединение")
        except Exception as e:
            print(f"[WARN] Web3 не доступен: {e}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка тестирования RPC Pool: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_job_engine():
    """Тестирование Job Engine"""
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ JOB ENGINE")
    print("=" * 60)
    
    try:
        from wallet_sender.core.job_engine import JobEngine, JobState
        
        # Создаем движок
        engine = JobEngine()
        print("[OK] JobEngine создан")
        
        # Тест NonceManager
        from wallet_sender.core.job_engine import NonceManager
        nonce_mgr = NonceManager()
        print("[OK] NonceManager создан")
        
        # Проверяем состояния
        for state in JobState:
            print(f"  - {state.name}: {state.value}")
        print("[OK] JobState enum работает")
        
        # Тест добавления задачи
        job_id = engine.submit_job(
            title="Test Task",
            mode="test",
            config={"test": True},
            priority=5
        )
        print(f"[OK] Задача #{job_id} добавлена в очередь")
        
        # Проверяем прогресс
        progress = engine.get_job_progress(job_id)
        if progress:
            print(f"[OK] Прогресс задачи: {progress}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка тестирования JobEngine: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_etherscan_api():
    """Тестирование Etherscan API"""
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ETHERSCAN API V2")
    print("=" * 60)
    
    try:
        from wallet_sender.api.etherscan import EtherscanAPI
        
        # Тестовые ключи из задания
        api_keys = [
            "RF1Q8SCFHFD1EVAP5A4WCMIM4DREA7UNUH",
            "U89HXHR9Y26CHMWAA9JUZ17YK2AAXS65CZ",
            "RAI3FTD9W53JPYZ2AHW8IBH9BXUC71NRH1"
        ]
        
        api = EtherscanAPI(api_keys)
        print(f"[OK] EtherscanAPI создан с {len(api_keys)} ключами")
        
        # Проверяем базовый URL
        assert api.BASE_URL == "https://api.etherscan.io/v2/api"
        assert api.BSC_CHAIN_ID == 56
        print("[OK] Корректный URL для V2 API и chainId для BSC")
        
        # Тест получения последнего блока
        try:
            block = await api.get_latest_block()
            if block:
                print(f"[OK] Последний блок BSC: {block}")
            else:
                print("[WARN] Не удалось получить последний блок")
        except Exception as e:
            print(f"[WARN] Ошибка получения блока: {e}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка тестирования Etherscan API: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Главная функция тестирования"""
    print("[START] ЗАПУСК ТЕСТИРОВАНИЯ CORE МОДУЛЕЙ WALLETSENDER")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Тест импортов
    if not test_imports():
        all_tests_passed = False
    
    # Тест Store
    if not test_store():
        all_tests_passed = False
    
    # Тест RPC
    if not test_rpc():
        all_tests_passed = False
    
    # Тест JobEngine
    if not test_job_engine():
        all_tests_passed = False
    
    # Тест Etherscan API
    try:
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(test_etherscan_api())
        if not result:
            all_tests_passed = False
    except Exception as e:
        print(f"[ERROR] Ошибка асинхронного теста: {e}")
        all_tests_passed = False
    
    # Итоговый результат
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("[OK] ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    else:
        print("[ERROR] НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
    print("=" * 60)
    
    return 0 if all_tests_passed else 1

if __name__ == "__main__":
    sys.exit(main())
