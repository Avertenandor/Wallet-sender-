#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализатор краша - запустите после краша для определения точной причины
"""

import sys
from pathlib import Path

# Добавляем src в Python path
current_dir = Path(__file__).parent
src_path = current_dir / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

def analyze_crash():
    """Анализ файлов после краша"""
    
    print("=" * 60)
    print("[SEARCH] АНАЛИЗАТОР КРАША v2.4.20")
    print("=" * 60)
    
    # 1. Проверяем execution_trace.txt
    print("\n📝 Анализ трассировки выполнения...")
    try:
        from wallet_sender.utils.crash_diagnostics import diagnose_crash_point
        crash_point = diagnose_crash_point()
        
        if crash_point:
            print(f"\n[TARGET] НАЙДЕНА ТОЧКА КРАША: {crash_point}")
            
            # Анализируем тип краша
            if "AutoSalesWorker.run" in crash_point:
                print("\n💡 Проблема в воркере автопродаж")
                print("   Возможные причины:")
                print("   • Обращение к UI из потока")
                print("   • Неинициализированный Web3")
                print("   • Ошибка в параметрах")
                
            elif "DexSwapService" in crash_point:
                print("\n💡 Проблема в сервисе обмена")
                print("   Возможные причины:")
                print("   • Потеря соединения с Web3")
                print("   • Неверный контракт роутера")
                print("   • Ошибка nonce")
                
            elif "update_ui" in crash_point.lower():
                print("\n💡 Проблема с обновлением UI")
                print("   Возможные причины:")
                print("   • Межпоточное нарушение Qt")
                print("   • Удаленный виджет")
                print("   • Неправильный сигнал/слот")
                
    except FileNotFoundError:
        print("[ERROR] Файл execution_trace.txt не найден")
        print("   Запустите приложение с диагностикой")
    
    # 2. Проверяем crash_log.txt
    print("\n📝 Проверка crash_log.txt...")
    try:
        with open("crash_log.txt", "r", encoding="utf-8") as f:
            content = f.read()
            if content:
                print("[OK] Найден crash_log.txt")
                # Ищем последнюю ошибку
                lines = content.split("\n")
                for i in range(len(lines)-1, -1, -1):
                    if "ERROR" in lines[i] or "CRASH" in lines[i]:
                        print(f"   Последняя ошибка: {lines[i]}")
                        break
            else:
                print("📄 crash_log.txt пуст")
    except FileNotFoundError:
        print("[ERROR] crash_log.txt не найден")
    
    # 3. Проверяем wallet_sender_modular.log
    print("\n📝 Проверка основного лога...")
    try:
        with open("wallet_sender_modular.log", "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Берем последние 20 строк
            last_lines = lines[-20:] if len(lines) > 20 else lines
            
            print("Последние записи в логе:")
            for line in last_lines:
                if "ERROR" in line or "CRITICAL" in line:
                    print(f"   🔴 {line.strip()}")
                elif "WARNING" in line:
                    print(f"   🟡 {line.strip()}")
    except FileNotFoundError:
        print("[ERROR] wallet_sender_modular.log не найден")
    
    # 4. Рекомендации
    print("\n" + "=" * 60)
    print("[INFO] РЕКОМЕНДАЦИИ:")
    print("=" * 60)
    
    if crash_point:
        print(f"\n1. Точка краша: {crash_point}")
        print("2. Проверьте этот метод на:")
        print("   • Обращения к UI из потока")
        print("   • Проверки на None")
        print("   • Правильность параметров")
        print("\n3. Запустите тест:")
        print("   python test_crash_fix.py")
    else:
        print("\n1. Запустите приложение еще раз")
        print("2. Воспроизведите краш")
        print("3. Запустите этот анализатор снова")
    
    print("\n" + "=" * 60)

def test_components():
    """Тест отдельных компонентов"""
    print("\n[TEST] Тестирование компонентов...")
    
    # Тест импорта
    try:
        from wallet_sender.ui.tabs.auto_sales_tab import AutoSalesTab
        print("[OK] AutoSalesTab импортируется")
    except Exception as e:
        print(f"[ERROR] Ошибка импорта AutoSalesTab: {e}")
    
    try:
        from wallet_sender.services.dex_swap_service import DexSwapService
        print("[OK] DexSwapService импортируется")
    except Exception as e:
        print(f"[ERROR] Ошибка импорта DexSwapService: {e}")
    
    # Тест Web3
    try:
        from wallet_sender.core.web3_provider import Web3Provider
        provider = Web3Provider()
        if provider.w3.is_connected():
            print("[OK] Web3 подключен к BSC")
        else:
            print("[ERROR] Web3 не подключен")
    except Exception as e:
        print(f"[ERROR] Ошибка Web3: {e}")

if __name__ == "__main__":
    analyze_crash()
    test_components()
    
    print("\n💡 Совет: Если краш воспроизводится:")
    print("   1. Запустите: python main.py")
    print("   2. Воспроизведите краш")
    print("   3. Запустите: python analyze_crash.py")
    print("   4. Отправьте результаты для анализа")
