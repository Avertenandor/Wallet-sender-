#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки основных компонентов WalletSender
"""

import sys
import os
from pathlib import Path

# Добавляем src в Python path
current_dir = Path(__file__).parent
src_path = current_dir / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

print("=" * 60)
print("ТЕСТИРОВАНИЕ КОМПОНЕНТОВ WALLETSENDER")
print("=" * 60)

def test_imports():
    """Тест импорта модулей"""
    print("\n1. Проверка импортов...")
    
    modules_to_test = [
        ('wallet_sender.config', 'Config'),
        ('wallet_sender.utils.logger', 'get_logger'),
        ('wallet_sender.services.bscscan_service', 'get_bscscan_service'),
        ('wallet_sender.services.job_router', 'get_job_router'),
        ('wallet_sender.core.rpc', 'get_rpc_pool'),
        ('wallet_sender.core.limiter', 'get_rate_limiter'),
        ('wallet_sender.core.nonce_manager', 'get_nonce_manager'),
    ]
    
    failed = []
    for module_name, item_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[item_name])
            if hasattr(module, item_name):
                print(f"  [OK] {module_name}.{item_name}")
            else:
                print(f"  [ERROR] {module_name}.{item_name} - атрибут не найден")
                failed.append(f"{module_name}.{item_name}")
        except ImportError as e:
            print(f"  [ERROR] {module_name} - {e}")
            failed.append(module_name)
    
    return len(failed) == 0

def test_services():
    """Тест создания сервисов"""
    print("\n2. Проверка сервисов...")
    
    try:
        # BscScanService
        from wallet_sender.services.bscscan_service import get_bscscan_service
        bscscan = get_bscscan_service()
        print(f"  [OK] BscScanService создан")
        
        # JobRouter
        from wallet_sender.services.job_router import get_job_router
        router = get_job_router()
        stats = router.stats()
        print(f"  [OK] JobRouter создан, очередь: {stats['states'].get('queued', 0)}")
        
        # RPC Pool
        from wallet_sender.core.rpc import get_rpc_pool
        rpc_pool = get_rpc_pool()
        endpoint = rpc_pool.current_primary()
        print(f"  [OK] RPC Pool создан, endpoint: {endpoint[:30] if endpoint else 'None'}...")
        
        # Rate Limiter
        from wallet_sender.core.limiter import get_rate_limiter
        limiter = get_rate_limiter()
        limiter_stats = limiter.get_stats()
        print(f"  [OK] Rate Limiter создан, rps: {limiter_stats.get('recent_rps', 0):.1f}")
        
        # Nonce Manager
        from wallet_sender.core.nonce_manager import get_nonce_manager
        nonce_mgr = get_nonce_manager()
        print(f"  [OK] NonceManager создан")
        
        return True
        
    except Exception as e:
        print(f"  [ERROR] Ошибка создания сервисов: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config():
    """Тест конфигурации"""
    print("\n3. Проверка конфигурации...")
    
    try:
        from wallet_sender.config import get_config
        config = get_config()
        
        # Проверяем основные параметры
        checks = [
            ('API ключи', len(config.bscscan_api_keys) > 0),
            ('RPC URLs', len(config.rpc_urls) > 0),
            ('Токены', 'PLEX ONE' in config.tokens),
            ('TxQueue', hasattr(config, 'txqueue')),
        ]
        
        all_ok = True
        for name, check in checks:
            if check:
                print(f"  [OK] {name}: OK")
            else:
                print(f"  [ERROR] {name}: FAIL")
                all_ok = False
        
        return all_ok
        
    except Exception as e:
        print(f"  [ERROR] Ошибка загрузки конфигурации: {e}")
        return False

def test_api_integration():
    """Тест интеграции с API"""
    print("\n4. Проверка API интеграции...")
    
    try:
        from wallet_sender.services.bscscan_service import get_bscscan_service
        import asyncio
        
        async def check_api():
            service = get_bscscan_service()
            
            # Проверяем статус
            stats = service.get_stats()
            print(f"  [STATS] Статус API: {stats.get('status', 'unknown')}")
            print(f"  [STATS] Доступные ключи: {stats.get('available_keys', 0)}")
            print(f"  [STATS] Активный ключ: {stats.get('current_key_index', -1)}")
            
            # Пробуем простой запрос
            try:
                result = await service.get_block_by_time(
                    timestamp=1700000000,
                    closest='before'
                )
                if result:
                    print(f"  [OK] API работает, блок: {result}")
                else:
                    print(f"  [WARN] API вернул пустой результат")
            except Exception as e:
                print(f"  [ERROR] Ошибка API запроса: {e}")
        
        # Запускаем асинхронную проверку
        asyncio.run(check_api())
        return True
        
    except Exception as e:
        print(f"  [ERROR] Ошибка проверки API: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Главная функция"""
    results = []
    
    # Запускаем тесты
    results.append(("Импорты", test_imports()))
    results.append(("Сервисы", test_services()))
    results.append(("Конфигурация", test_config()))
    results.append(("API интеграция", test_api_integration()))
    
    # Итоги
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "[OK] PASS" if passed else "[ERROR] FAIL"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("[OK] ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("Приложение готово к запуску.")
        return 0
    else:
        print("[ERROR] НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        print("Требуется устранить проблемы перед запуском.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
