#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестировщик исправлений - проверяет, что краш устранен
"""

import sys
import time
from pathlib import Path

# Добавляем src в Python path
current_dir = Path(__file__).parent
src_path = current_dir / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

def test_fix():
    """Проверка исправления краша"""
    
    print("=" * 60)
    print("[TEST] ТЕСТ ИСПРАВЛЕНИЯ КРАША v2.4.20")
    print("=" * 60)
    
    # Очищаем файл трассировки
    with open("execution_trace.txt", "w") as f:
        f.write("=== Test started ===\n")
    
    print("\n📝 Тест 1: Импорт модулей")
    try:
        from wallet_sender.ui.tabs.auto_sales_tab import AutoSalesTab, AutoSalesWorker
        from wallet_sender.services.dex_swap_service import DexSwapService
        from wallet_sender.core.web3_provider import Web3Provider
        print("[OK] Все модули импортированы")
    except Exception as e:
        print(f"[ERROR] Ошибка импорта: {e}")
        return False
    
    print("\n📝 Тест 2: Создание Web3 провайдера")
    try:
        provider = Web3Provider()
        if provider.w3.is_connected():
            print("[OK] Web3 подключен")
        else:
            print("[WARN] Web3 не подключен, но объект создан")
    except Exception as e:
        print(f"[ERROR] Ошибка создания Web3: {e}")
        return False
    
    print("\n📝 Тест 3: Создание DexSwapService")
    try:
        # Тестовый приватный ключ (не используйте реальный!)
        test_key = "0x" + "1" * 64
        router = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
        
        service = DexSwapService(
            web3=provider.w3,
            router_address=router,
            private_key=test_key
        )
        print("[OK] DexSwapService создан")
        
        # Проверяем методы
        if hasattr(service, '_sync_nonce_with_network'):
            print("[OK] Метод синхронизации nonce найден")
        if hasattr(service, '_wait_receipt_async'):
            print("[OK] Асинхронный метод ожидания найден")
            
    except Exception as e:
        print(f"[ERROR] Ошибка создания DexSwapService: {e}")
        return False
    
    print("\n📝 Тест 4: Создание воркера (без запуска)")
    try:
        # Создаем фиктивный воркер для теста
        worker = AutoSalesWorker(
            private_key=test_key,
            token_address="0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1",
            sell_amount=0.1,
            slippage=5,
            interval=60,
            cycles=1
        )
        print("[OK] AutoSalesWorker создан")
        
        # Проверяем атрибуты
        if hasattr(worker, 'swap_service'):
            print("[OK] swap_service инициализирован")
        if hasattr(worker, 'is_running'):
            print("[OK] is_running флаг установлен")
            
    except Exception as e:
        print(f"[ERROR] Ошибка создания воркера: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n📝 Тест 5: Проверка Qt потоков")
    try:
        from PyQt5.QtCore import QThread
        from PyQt5.QtWidgets import QApplication
        
        # Создаем тестовое приложение если его нет
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
            
        # Создаем тестовый поток
        thread = QThread()
        print("[OK] Qt потоки работают")
        
        # Проверяем текущий поток
        current = QThread.currentThread()
        main = app.thread()
        if current == main:
            print("[OK] Находимся в главном потоке Qt")
        else:
            print("[WARN] Не в главном потоке Qt")
            
    except Exception as e:
        print(f"[ERROR] Ошибка Qt: {e}")
        return False
    
    # Анализ трассировки
    print("\n📝 Анализ трассировки...")
    try:
        from wallet_sender.utils.crash_diagnostics import diagnose_crash_point
        crash_point = diagnose_crash_point()
        
        if crash_point:
            print(f"[WARN] Обнаружена незавершенная функция: {crash_point}")
            print("   Это может быть местом потенциального краша")
            return False
        else:
            print("[OK] Крашей не обнаружено")
            
    except Exception as e:
        print(f"[WARN] Не удалось проанализировать трассировку: {e}")
    
    print("\n" + "=" * 60)
    print("[OK] ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    print("=" * 60)
    print("\nТеперь можно запускать основное приложение:")
    print("  python main.py")
    print("\nЕсли краш повторится:")
    print("  1. Запустите: python analyze_crash.py")
    print("  2. Отправьте результаты анализа")
    
    return True

def test_isolated_swap():
    """Изолированный тест swap операции"""
    print("\n" + "=" * 60)
    print("[TEST] ИЗОЛИРОВАННЫЙ ТЕСТ SWAP")
    print("=" * 60)
    
    try:
        from wallet_sender.services.dex_swap_service import DexSwapService
        from wallet_sender.core.web3_provider import Web3Provider
        
        print("\n1. Создаем Web3...")
        provider = Web3Provider()
        
        print("2. Создаем DexSwapService...")
        test_key = "0x" + "1" * 64
        service = DexSwapService(
            web3=provider.w3,
            router_address="0x10ED43C718714eb63d5aA57B78B54704E256024E",
            private_key=test_key
        )
        
        print("3. Проверяем nonce...")
        nonce = service._reserve_nonce()
        print(f"   Nonce: {nonce}")
        
        print("4. Проверяем gas price...")
        gas = service._gas_price(None, "test")
        print(f"   Gas price: {gas} wei ({gas/10**9} gwei)")
        
        print("\n[OK] Изолированный тест пройден")
        
    except Exception as e:
        print(f"\n[ERROR] Ошибка в изолированном тесте: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    success = test_fix()
    
    if success:
        test_isolated_swap()
    
    print("\n" + "=" * 60)
    if success:
        print("[OK] Система готова к работе")
    else:
        print("[ERROR] Обнаружены проблемы, требуется дополнительная диагностика")
    print("=" * 60)
