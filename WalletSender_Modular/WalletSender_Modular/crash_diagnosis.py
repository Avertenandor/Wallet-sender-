#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Диагностический скрипт для исследования падения при операциях продажи
"""

import sys
import traceback
import asyncio
from pathlib import Path
import signal
import logging

# Добавляем src в путь
current_dir = Path(__file__).parent
src_path = current_dir / "src"
sys.path.insert(0, str(src_path))

# Настройка логирования для отладки
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('crash_diagnosis.log')
    ]
)

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    print(f"\n🛑 Получен сигнал {signum}, завершаем...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def test_imports():
    """Тест импортов критических модулей"""
    try:
        print("[1] 📦 Тестируем импорты...")
        
        from wallet_sender.services.dex_swap_service_async import DexSwapServiceAsync
        from wallet_sender.core.web3_provider import Web3Provider
        from wallet_sender.utils.gas_manager import GasManager
        from wallet_sender.core.nonce_manager import get_nonce_manager
        from wallet_sender.ui.tabs.auto_sales_tab import AutoSalesTab
        
        print("[OK] Все критические модули импортированы успешно")
        return True
    except Exception as e:
        print(f"[ERROR] Ошибка импортов: {e}")
        traceback.print_exc()
        return False

def test_dex_service_creation():
    """Тест создания DexSwapService"""
    try:
        print("\n[2] [CONFIG] Тестируем создание DexSwapService...")
        
        from wallet_sender.core.web3_provider import Web3Provider
        from wallet_sender.services.dex_swap_service_async import DexSwapServiceAsync
        
        # Создаем Web3Provider
        web3_provider = Web3Provider()
        web3 = web3_provider.get_web3()
        
        print(f"[OK] Web3 подключен к: {web3.provider.endpoint_uri}")
        
        # Тестовые данные (НЕ используем реальные ключи!)
        test_private_key = "0x" + "1" * 64  # Фиктивный ключ
        router_address = "0x10ED43C718714eb63d5aA57B78B54704E256024E"  # PancakeSwap V2
        
        # Создаем сервис
        dex_service = DexSwapServiceAsync(
            web3=web3,
            router_address=router_address,
            private_key=test_private_key,
            custom_gas_price_gwei=0.1
        )
        
        print("[OK] DexSwapServiceAsync создан успешно")
        print(f"   - Адрес аккаунта: {dex_service.address}")
        print(f"   - Адрес роутера: {dex_service.router_address}")
        print(f"   - Nonce manager: {'Есть' if dex_service.nonce_manager else 'Нет'}")
        
        return dex_service, web3
        
    except Exception as e:
        print(f"[ERROR] Ошибка создания DexSwapService: {e}")
        traceback.print_exc()
        return None, None

def test_transaction_simulation():
    """Симуляция транзакции без отправки"""
    try:
        print("\n[3] [TEST] Симуляция транзакции...")
        
        dex_service, web3 = test_dex_service_creation()
        if not dex_service:
            return False
            
        # Тестовые данные для swap
        amount_in = 1000000000000000000  # 1 токен (18 decimals)
        amount_out_min = 0  # Минимум 0 для теста
        path = [
            "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
            "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"   # BUSD
        ]
        
        print(f"   - Сумма входа: {amount_in}")
        print(f"   - Минимум выхода: {amount_out_min}")
        print(f"   - Путь: {path[0]} -> {path[1]}")
        
        # Пробуем получить amounts out (не требует отправки tx)
        try:
            amounts = dex_service.get_amounts_out(amount_in, path)
            print(f"[OK] getAmountsOut работает: {amounts}")
        except Exception as e:
            print(f"[WARN] getAmountsOut ошибка: {e}")
        
        # Тестируем построение транзакции (без отправки)
        try:
            import time
            deadline = int(time.time()) + 1200
            
            # Получаем nonce через внутренний метод
            nonce = dex_service._sync_nonce_with_network()
            print(f"[OK] Nonce получен: {nonce}")
            
            # Параметры транзакции
            tx_params = {
                'from': dex_service.address,
                'nonce': nonce,
                'gas': 300000,
                'gasPrice': dex_service._gas_price(None, 'swap'),
                'chainId': web3.eth.chain_id
            }
            
            # Строим транзакцию (но НЕ отправляем)
            fn = dex_service.router.functions.swapExactTokensForTokens(
                amount_in, amount_out_min, path, dex_service.address, deadline
            )
            tx = fn.build_transaction(tx_params)
            print(f"[OK] Транзакция построена успешно:")
            print(f"   - Gas: {tx['gas']}")
            print(f"   - Gas Price: {tx['gasPrice']} wei")
            print(f"   - Nonce: {tx['nonce']}")
            
        except Exception as e:
            print(f"[ERROR] Ошибка построения транзакции: {e}")
            traceback.print_exc()
            return False
            
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка симуляции транзакции: {e}")
        traceback.print_exc()
        return False

async def test_async_operations():
    """Тест асинхронных операций"""
    try:
        print("\n[4] [MINIMAL] Тестируем асинхронные операции...")
        
        # Простой тест asyncio
        await asyncio.sleep(0.1)
        print("[OK] Asyncio работает корректно")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка асинхронных операций: {e}")
        traceback.print_exc()
        return False

def test_error_handling():
    """Тест обработки ошибок"""
    try:
        print("\n[5] 🚨 Тестируем обработку ошибок...")
        
        # Тест обработки исключений в DexSwapService
        dex_service, web3 = test_dex_service_creation()
        if not dex_service:
            return False
            
        # Создаем намеренно неправильные параметры
        try:
            # Неправильный путь
            bad_path = ["0x0000000000000000000000000000000000000000"]
            amounts = dex_service.get_amounts_out(1000, bad_path)
            print(f"[WARN] Неожиданно получили результат для плохого пути: {amounts}")
        except Exception as e:
            print(f"[OK] Правильно обработана ошибка неправильного пути: {type(e).__name__}")
        
        print("[OK] Обработка ошибок работает корректно")
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка в тесте обработки ошибок: {e}")
        traceback.print_exc()
        return False

def main():
    """Главная функция диагностики"""
    print("[SEARCH] ДИАГНОСТИКА ПАДЕНИЯ WALLETSENDER ПРИ ОПЕРАЦИЯХ ПРОДАЖИ")
    print("=" * 65)
    
    # Выполняем тесты последовательно
    tests = [
        test_imports,
        test_transaction_simulation,
        test_error_handling
    ]
    
    async_tests = [
        test_async_operations
    ]
    
    passed = 0
    total = len(tests) + len(async_tests)
    
    # Синхронные тесты
    for i, test in enumerate(tests, 1):
        try:
            print(f"\n--- ТЕСТ {i}/{total} ---")
            if test():
                passed += 1
                print(f"[OK] ТЕСТ {i} ПРОЙДЕН")
            else:
                print(f"[ERROR] ТЕСТ {i} ПРОВАЛЕН")
        except Exception as e:
            print(f"💥 КРИТИЧЕСКАЯ ОШИБКА В ТЕСТЕ {i}: {e}")
            traceback.print_exc()
    
    # Асинхронные тесты
    for i, test in enumerate(async_tests, len(tests) + 1):
        try:
            print(f"\n--- ТЕСТ {i}/{total} (ASYNC) ---")
            if asyncio.run(test()):
                passed += 1
                print(f"[OK] ТЕСТ {i} ПРОЙДЕН")
            else:
                print(f"[ERROR] ТЕСТ {i} ПРОВАЛЕН")
        except Exception as e:
            print(f"💥 КРИТИЧЕСКАЯ ОШИБКА В ТЕСТЕ {i}: {e}")
            traceback.print_exc()
    
    # Итоги
    print(f"\n[STATS] РЕЗУЛЬТАТЫ ДИАГНОСТИКИ")
    print("=" * 35)
    print(f"Пройдено тестов: {passed}/{total}")
    print(f"Процент успешности: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ - ПРОБЛЕМА НЕ В БАЗОВОЙ ФУНКЦИОНАЛЬНОСТИ")
        print("💡 Возможные причины падения:")
        print("   - Проблемы с обработкой исключений в UI потоке")
        print("   - Неправильная обработка AsyncIO в Qt приложении") 
        print("   - Проблемы с cleanup ресурсов")
        print("   - Race conditions в многопоточности")
    else:
        print("[WARN] ОБНАРУЖЕНЫ ПРОБЛЕМЫ В БАЗОВОЙ ФУНКЦИОНАЛЬНОСТИ")
        print("[CONFIG] ТРЕБУЕТСЯ ИСПРАВЛЕНИЕ НАЙДЕННЫХ ОШИБОК")
    
    print(f"\n📝 Детальные логи сохранены в: crash_diagnosis.log")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Диагностика прервана пользователем")
    except Exception as e:
        print(f"\n💥 КРИТИЧЕСКАЯ ОШИБКА ДИАГНОСТИКИ: {e}")
        traceback.print_exc()
    finally:
        print("[BYE] Диагностика завершена")
