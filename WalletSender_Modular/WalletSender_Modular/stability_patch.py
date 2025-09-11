"""
Критический патч стабильности для WalletSender
Версия: 2.4.19
Дата: 11.09.2025

ПРОБЛЕМА: Приложение закрывается после 5 транзакций без ошибки

ДИАГНОСТИКА И РЕШЕНИЯ:
"""

import sys
import gc
import traceback
import signal
from typing import Any
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

def install_crash_handler():
    """Установка обработчика критических ошибок"""
    
    # Оригинальный обработчик исключений
    original_excepthook = sys.excepthook
    
    def exception_handler(exctype, value, tb):
        """Обработчик необработанных исключений"""
        error_msg = ''.join(traceback.format_exception(exctype, value, tb))
        
        # Логируем ошибку в файл
        with open("crash_log.txt", "a", encoding="utf-8") as f:
            from datetime import datetime
            f.write(f"\n\n=== CRASH at {datetime.now()} ===\n")
            f.write(error_msg)
            f.write("=== END CRASH ===\n")
        
        print(f"\n[WARN] КРИТИЧЕСКАЯ ОШИБКА:\n{error_msg}")
        
        # Пытаемся показать диалог
        try:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Критическая ошибка", 
                               f"Приложение столкнулось с критической ошибкой:\n\n{value}\n\n"
                               "Подробности сохранены в crash_log.txt")
        except:
            pass
        
        # Вызываем оригинальный обработчик
        original_excepthook(exctype, value, tb)
    
    # Устанавливаем новый обработчик
    sys.excepthook = exception_handler
    
    # Обработчик сигналов ОС
    def signal_handler(sig, frame):
        print(f"\n[WARN] Получен сигнал {sig}")
        with open("crash_log.txt", "a", encoding="utf-8") as f:
            from datetime import datetime
            f.write(f"\n\n=== SIGNAL {sig} at {datetime.now()} ===\n")
            f.write(f"Stack trace:\n{''.join(traceback.format_stack(frame))}\n")
        sys.exit(0)
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("[OK] Обработчики критических ошибок установлены")

def install_memory_monitor():
    """Установка монитора памяти"""
    
    def check_memory():
        """Проверка использования памяти каждые 30 секунд"""
        import psutil
        import os
        
        try:
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            print(f"[SAVE] Память: {memory_mb:.1f} MB")
            
            # Если память превышает 500 MB - запускаем сборщик мусора
            if memory_mb > 500:
                print("[WARN] Высокое использование памяти, запуск сборщика мусора...")
                gc.collect()
                
                # Проверяем снова
                new_memory = process.memory_info().rss / 1024 / 1024
                print(f"[SAVE] Память после очистки: {new_memory:.1f} MB (освобождено {memory_mb - new_memory:.1f} MB)")
        except:
            pass
    
    # Создаем таймер для проверки памяти
    timer = QTimer()
    timer.timeout.connect(check_memory)
    timer.start(30000)  # Каждые 30 секунд
    
    return timer

def patch_dex_swap_service():
    """Патч для DexSwapService для улучшения стабильности"""
    
    try:
        from wallet_sender.services.dex_swap_service import DexSwapService
        
        # Сохраняем оригинальный метод
        original_build_and_send = DexSwapService._build_and_send
        
        def patched_build_and_send(self, fn, tx_params):
            """Патченная версия с обработкой ошибок и восстановлением"""
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # Проверяем соединение перед отправкой
                    if not self.web3.is_connected():
                        print("[WARN] Потеряно соединение с Web3, переподключение...")
                        # Пытаемся переподключиться
                        from wallet_sender.core.web3_provider import Web3Provider
                        provider = Web3Provider()
                        if provider.w3.is_connected():
                            self.web3 = provider.w3
                            print("[OK] Переподключение успешно")
                        else:
                            raise Exception("Не удалось восстановить соединение")
                    
                    # Вызываем оригинальный метод
                    result = original_build_and_send(self, fn, tx_params)
                    
                    # Сброс счетчика транзакций для предотвращения утечек
                    if hasattr(self, '_tx_count'):
                        self._tx_count += 1
                        if self._tx_count >= 5:
                            print("🔄 Выполнено 5 транзакций, очистка кеша...")
                            gc.collect()
                            self._tx_count = 0
                    else:
                        self._tx_count = 1
                    
                    return result
                    
                except Exception as e:
                    retry_count += 1
                    print(f"[WARN] Ошибка при отправке транзакции (попытка {retry_count}/{max_retries}): {e}")
                    
                    if retry_count >= max_retries:
                        # Логируем критическую ошибку
                        with open("crash_log.txt", "a", encoding="utf-8") as f:
                            from datetime import datetime
                            f.write(f"\n\n=== TX ERROR at {datetime.now()} ===\n")
                            f.write(f"Error: {e}\n")
                            f.write(f"Traceback:\n{traceback.format_exc()}\n")
                        raise
                    
                    # Ждем перед повтором
                    import time
                    time.sleep(2 ** retry_count)
            
            raise Exception("Превышено количество попыток отправки транзакции")
        
        # Применяем патч
        DexSwapService._build_and_send = patched_build_and_send
        print("[OK] DexSwapService пропатчен для улучшения стабильности")
        
    except Exception as e:
        print(f"[WARN] Не удалось пропатчить DexSwapService: {e}")

def patch_auto_sales_tab():
    """Патч для AutoSalesTab для предотвращения крашей"""
    
    try:
        from wallet_sender.ui.tabs.auto_sales_tab import AutoSalesTab
        
        # Сохраняем оригинальный метод
        if hasattr(AutoSalesTab, 'execute_sale'):
            original_execute = AutoSalesTab.execute_sale
            
            def patched_execute(self):
                """Патченная версия с защитой от крашей"""
                try:
                    # Проверяем состояние перед выполнением
                    if not hasattr(self, 'is_running') or not self.is_running:
                        print("[WARN] Попытка выполнить продажу при остановленном процессе")
                        return
                    
                    # Вызываем оригинальный метод
                    return original_execute(self)
                    
                except Exception as e:
                    print(f"[WARN] Ошибка при выполнении продажи: {e}")
                    # Логируем ошибку
                    with open("crash_log.txt", "a", encoding="utf-8") as f:
                        from datetime import datetime
                        f.write(f"\n\n=== SALE ERROR at {datetime.now()} ===\n")
                        f.write(f"Error: {e}\n")
                        f.write(f"Traceback:\n{traceback.format_exc()}\n")
                    
                    # Останавливаем автопродажи при критической ошибке
                    if hasattr(self, 'stop_auto_sales'):
                        self.stop_auto_sales()
            
            AutoSalesTab.execute_sale = patched_execute
            print("[OK] AutoSalesTab пропатчен для предотвращения крашей")
            
    except Exception as e:
        print(f"[WARN] Не удалось пропатчить AutoSalesTab: {e}")

def apply_all_patches():
    """Применение всех патчей стабильности"""
    print("\n[CONFIG] Применение патчей стабильности...")
    
    # Устанавливаем обработчики ошибок
    install_crash_handler()
    
    # Патчим критические компоненты
    patch_dex_swap_service()
    patch_auto_sales_tab()
    
    print("[OK] Все патчи применены\n")
    
    return install_memory_monitor  # Возвращаем функцию для установки после создания QApplication

if __name__ == "__main__":
    print("Этот файл должен быть импортирован в main.py")
    print("Добавьте в начало main.py:")
    print("from stability_patch import apply_all_patches")
    print("И вызовите apply_all_patches() перед созданием главного окна")
