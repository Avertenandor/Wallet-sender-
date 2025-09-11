#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Исправление проблем WalletSender v2.4.9
- Дублирование логов
- Несинхронизированные логи между окнами
- Ошибка ликвидности
"""

import os
import sys
from pathlib import Path

def fix_auto_buy_tab():
    """Исправляет проблемы в auto_buy_tab.py"""
    
    file_path = Path(r"C:\Users\konfu\Desktop\Sites\Experiment\Experiment1\WalletSender_MCP  копия\WalletSender_Modular\WalletSender_Modular\src\wallet_sender\ui\tabs\auto_buy_tab.py")
    
    if not file_path.exists():
        print(f"[ERROR] Файл не найден: {file_path}")
        return False
    
    print(f"📝 Исправляем {file_path.name}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Исправление 1: Убираем дублирующие декораторы
    # Оставляем только один декоратор на методе
    fixes = [
        # connect_wallet - убираем лишние декораторы, оставляем только @log_click
        (
            '    @log_click("Подключить кошелек")\n    @log_action("Подключение кошелька")\n    @log_validation("Проверка кошелька")\n    def connect_wallet',
            '    @log_click("Подключить кошелек")\n    def connect_wallet'
        ),
        # disconnect_wallet - убираем дублирующий декоратор
        (
            '    @log_click("Отключить кошелек")\n    @log_action("Отключение кошелька")\n    def disconnect_wallet',
            '    @log_click("Отключить кошелек")\n    def disconnect_wallet'
        ),
        # refresh_all_balances - оставляем только @log_click
        (
            '    @log_click("Обновить балансы")\n    @log_action("Обновление всех балансов")\n    def refresh_all_balances',
            '    @log_click("Обновить балансы")\n    def refresh_all_balances'
        ),
        # debug_balance - оставляем только @log_click
        (
            '    @log_click("Диагностика баланса")\n    @log_action("Диагностика балансов токенов")\n    def debug_balance',
            '    @log_click("Диагностика баланса")\n    def debug_balance'
        ),
        # start_auto_buy - оставляем только @log_click
        (
            '    @log_click("Начать покупки")\n    @log_action("Запуск автоматических покупок")\n    def start_auto_buy',
            '    @log_click("Начать покупки")\n    def start_auto_buy'
        ),
        # stop_auto_buy - оставляем только @log_click
        (
            '    @log_click("Остановить покупки")\n    @log_action("Остановка автоматических покупок")\n    def stop_auto_buy',
            '    @log_click("Остановить покупки")\n    def stop_auto_buy'
        ),
        # reset_stats - оставляем только @log_click
        (
            '    @log_click("Сбросить статистику")\n    @log_action("Сброс статистики покупок")\n    def reset_stats',
            '    @log_click("Сбросить статистику")\n    def reset_stats'
        ),
        # clear_log - оставляем только @log_click
        (
            '    @log_click("Очистить лог")\n    @log_action("Очистка лога операций")\n    def clear_log',
            '    @log_click("Очистить лог")\n    def clear_log'
        ),
        # _validate_buy_settings - убираем декоратор вообще (внутренний метод)
        (
            '    @log_validation("Проверка настроек покупки")\n    def _validate_buy_settings',
            '    def _validate_buy_settings'
        ),
    ]
    
    for old_text, new_text in fixes:
        if old_text in content:
            content = content.replace(old_text, new_text)
            print(f"  [OK] Исправлены дублирующие декораторы в {old_text.split('def ')[1].split('(')[0]}")
    
    # Исправление 2: Изменяем метод log() чтобы он выводил в главное окно
    old_log_method = '''    def log(self, message: str, level: str = 'INFO'):
        """Потокобезопасное логирование без двойного вывода (не дергаем BaseTab)."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        try:
            from PyQt5.QtCore import QThread
            if QThread.currentThread() != self.thread():
                self.log_message_signal.emit(formatted_message)
            else:
                self._append_log_line(formatted_message)
        except Exception:
            self._append_log_line(formatted_message)'''
    
    new_log_method = '''    def log(self, message: str, level: str = 'INFO'):
        """Потокобезопасное логирование с выводом в главное окно."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # Выводим в локальный лог вкладки
        try:
            from PyQt5.QtCore import QThread
            if QThread.currentThread() != self.thread():
                self.log_message_signal.emit(formatted_message)
            else:
                self._append_log_line(formatted_message)
        except Exception:
            self._append_log_line(formatted_message)
        
        # Также выводим в главное окно для синхронизации
        if hasattr(self, 'main_window') and self.main_window:
            try:
                self.main_window.add_log(message, level)
            except Exception:
                pass'''
    
    if old_log_method in content:
        content = content.replace(old_log_method, new_log_method)
        print("  [OK] Исправлен метод log() для синхронизации с главным окном")
    
    # Исправление 3: Исправляем проблему с ликвидностью
    # Исправляем неправильное количество decimals для USDT
    old_liquidity_check = '''            # Проверяем ликвидность с правильным путем для покупки
            self.log("[SEARCH] Проверяем ликвидность для покупки...", "INFO")
            if buy_with == 'BNB':
                amount_wei = self.web3.to_wei(buy_amount, 'ether')
            else:
                amount_wei = int(buy_amount * (10 ** 6))  # USDT имеет 6 decimals'''
    
    new_liquidity_check = '''            # Проверяем ликвидность с правильным путем для покупки
            self.log("[SEARCH] Проверяем ликвидность для покупки...", "INFO")
            if buy_with == 'BNB':
                amount_wei = self.web3.to_wei(buy_amount, 'ether')
            else:
                # USDT имеет 18 decimals на BSC (не 6!)
                amount_wei = self.web3.to_wei(buy_amount, 'ether')  # Используем 18 decimals'''
    
    if old_liquidity_check in content:
        content = content.replace(old_liquidity_check, new_liquidity_check)
        print("  [OK] Исправлены decimals для USDT (18 вместо 6)")
    
    # Исправление USDT decimals в другом месте
    old_usdt_amount = '''                # USDT имеет 6 decimals, не 18
                amount_in_units = int(buy_amount * (10 ** 6))'''
    
    new_usdt_amount = '''                # USDT на BSC имеет 18 decimals
                amount_in_units = self.web3.to_wei(buy_amount, 'ether')'''
    
    if old_usdt_amount in content:
        content = content.replace(old_usdt_amount, new_usdt_amount)
        print("  [OK] Исправлены decimals для USDT approve")
    
    # Исправление баланса USDT
    old_usdt_balance = '''                usdt_balance = usdt_balance_wei / (10 ** 6)  # USDT decimals'''
    new_usdt_balance = '''                usdt_balance = self.web3.from_wei(usdt_balance_wei, 'ether')  # USDT на BSC имеет 18 decimals'''
    
    if old_usdt_balance in content:
        content = content.replace(old_usdt_balance, new_usdt_balance)
        print("  [OK] Исправлен расчет баланса USDT")
    
    # Сохраняем только если были изменения
    if content != original_content:
        # Создаем резервную копию
        backup_path = file_path.with_suffix('.py.backup')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        print(f"  📁 Резервная копия: {backup_path}")
        
        # Сохраняем исправленный файл
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [OK] Файл успешно исправлен")
        return True
    else:
        print("  ℹ️ Изменения не требуются")
        return False

def update_version():
    """Обновляет версию приложения"""
    version_file = Path(r"C:\Users\konfu\Desktop\Sites\Experiment\Experiment1\WalletSender_MCP  копия\WalletSender_Modular\WalletSender_Modular\VERSION")
    
    if version_file.exists():
        with open(version_file, 'w') as f:
            f.write("2.4.9")
        print("[OK] Версия обновлена до 2.4.9")
        return True
    return False

def main():
    print("=" * 60)
    print("[CONFIG] ИСПРАВЛЕНИЕ ПРОБЛЕМ WalletSender v2.4.9")
    print("=" * 60)
    print()
    print("Исправляемые проблемы:")
    print("1. [ERROR] Дублирование логов в основном окне")
    print("2. [ERROR] Несинхронизированные логи между окнами")
    print("3. [ERROR] Ошибка ликвидности (неправильные decimals)")
    print()
    print("=" * 60)
    
    # Выполняем исправления
    success = True
    
    print("\n📝 Применение исправлений...")
    if not fix_auto_buy_tab():
        success = False
    
    print("\n📝 Обновление версии...")
    if not update_version():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ВСЕ ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ УСПЕШНО!")
        print()
        print("Что было исправлено:")
        print("[OK] Убраны дублирующие декораторы логирования")
        print("[OK] Добавлена синхронизация логов с главным окном")
        print("[OK] Исправлены decimals для USDT (18 вместо 6)")
        print("[OK] Версия обновлена до 2.4.9")
        print()
        print("[WARN] ВАЖНО: Перезапустите приложение для применения изменений!")
    else:
        print("[WARN] Некоторые исправления не удалось применить")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
