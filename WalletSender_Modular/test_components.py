#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки работоспособности компонентов WalletSender_Modular
"""

import sys
from pathlib import Path

# Добавляем src в путь
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Тест импорта всех критических модулей"""
    print("=" * 60)
    print("ТЕСТ ИМПОРТА МОДУЛЕЙ")
    print("=" * 60)
    
    tests = []
    
    # Тестируем core модули
    try:
        from wallet_sender.core.nonce_manager import get_nonce_manager
        print("✅ NonceManager импортирован")
        tests.append(True)
    except Exception as e:
        print(f"❌ NonceManager: {e}")
        tests.append(False)
    
    try:
        from wallet_sender.core.rpc import get_rpc_pool
        rpc_pool = get_rpc_pool()
        print(f"✅ RPC Manager импортирован")
        
        # Проверяем метод current_primary
        if hasattr(rpc_pool, 'current_primary'):
            print("✅ Метод current_primary() существует")
            tests.append(True)
        else:
            print("❌ Метод current_primary() не найден")
            tests.append(False)
    except Exception as e:
        print(f"❌ RPC Manager: {e}")
        tests.append(False)
    
    try:
        from wallet_sender.core.job_engine import get_job_engine
        print("✅ JobEngine импортирован")
        tests.append(True)
    except Exception as e:
        print(f"❌ JobEngine: {e}")
        tests.append(False)
    
    # Тестируем services
    try:
        from wallet_sender.services.job_router import get_job_router
        print("