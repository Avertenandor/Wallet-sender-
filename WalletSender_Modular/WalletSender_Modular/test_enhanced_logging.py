#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый файл для проверки улучшенной системы логирования
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к src для импорта модулей
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from wallet_sender.utils.logger_enhanced import (
    set_ui_log_handler,
    log_action,
    log_async_action,
    log_click,
    log_network_action,
    log_transaction,
    log_validation,
    log_api_call
)


# Простой обработчик для вывода в консоль
def console_log_handler(message: str, level: str):
    """Обработчик для вывода логов в консоль"""
    print(f"[{level}] {message}")


# Устанавливаем обработчик
set_ui_log_handler(console_log_handler)


class TestClass:
    """Тестовый класс для проверки декораторов"""
    
    def __init__(self):
        self.value = 42
    
    @log_action("Инициализация данных", log_result=True)
    def initialize_data(self, data_size: int = 100):
        """Синхронный метод с логированием"""
        # Имитация работы
        result = [i for i in range(data_size)]
        return f"Инициализировано {len(result)} элементов"
    
    @log_async_action("Загрузка данных с сервера")
    async def fetch_data(self, url: str):
        """Асинхронный метод с логированием"""
        # Имитация асинхронной операции
        await asyncio.sleep(1)
        return f"Данные загружены с {url}"
    
    @log_validation("Проверка валидности данных")
    def validate_data(self, data):
        """Метод валидации с логированием"""
        if data and len(data) > 0:
            return True
        return False
    
    @log_api_call("BSC API")
    async def call_api(self, endpoint: str):
        """Вызов API с логированием"""
        await asyncio.sleep(0.5)
        return {"status": "success", "endpoint": endpoint}
    
    @log_network_action("Подключение к блокчейну")
    def connect_blockchain(self):
        """Сетевая операция с логированием"""
        # Имитация подключения
        return "0x1234567890abcdef"
    
    @log_action("Операция с ошибкой")
    def failing_operation(self):
        """Метод, который вызывает ошибку"""
        raise ValueError("Это тестовая ошибка для проверки логирования")
    
    @log_async_action("Отменяемая операция")
    async def cancellable_operation(self):
        """Асинхронная операция, которая будет отменена"""
        await asyncio.sleep(10)  # Долгая операция
        return "Не должно выполниться"


@log_click("Тестовая кнопка")
def test_button_click():
    """Функция для теста декоратора кнопки"""
    print("Кнопка нажата!")
    return "clicked"


@log_transaction
def send_transaction(to_address: str, amount: float):
    """Функция для теста декоратора транзакций"""
    # Имитация отправки транзакции
    tx_hash = "0xabcdef1234567890" * 4
    return tx_hash


@log_action("Функция с длинными параметрами", log_params=True)
def function_with_long_params(very_long_string: str, another_param: dict):
    """Тест обрезания длинных параметров"""
    return "processed"


async def main():
    """Главная функция для тестирования"""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ УЛУЧШЕННОЙ СИСТЕМЫ ЛОГИРОВАНИЯ")
    print("=" * 60)
    
    # Создаем тестовый объект
    test_obj = TestClass()
    
    print("\n1. Тест синхронного метода класса:")
    result = test_obj.initialize_data(50)
    print(f"   Результат: {result}")
    
    print("\n2. Тест асинхронного метода:")
    result = await test_obj.fetch_data("https://api.example.com/data")
    print(f"   Результат: {result}")
    
    print("\n3. Тест валидации:")
    is_valid = test_obj.validate_data([1, 2, 3])
    print(f"   Валидно: {is_valid}")
    
    print("\n4. Тест API вызова:")
    api_result = await test_obj.call_api("/v2/tokens")
    print(f"   API результат: {api_result}")
    
    print("\n5. Тест сетевой операции:")
    connection = test_obj.connect_blockchain()
    print(f"   Подключение: {connection}")
    
    print("\n6. Тест декоратора кнопки:")
    test_button_click()
    
    print("\n7. Тест декоратора транзакции:")
    tx = send_transaction("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb8", 100.5)
    print(f"   TX Hash: {tx[:20]}...")
    
    print("\n8. Тест обрезания длинных параметров:")
    long_string = "Это очень длинная строка " * 10
    long_dict = {f"key_{i}": f"value_{i}" for i in range(20)}
    function_with_long_params(long_string, long_dict)
    
    print("\n9. Тест обработки ошибок:")
    try:
        test_obj.failing_operation()
    except ValueError:
        print("   Ошибка успешно перехвачена и залогирована")
    
    print("\n10. Тест отмены асинхронной операции:")
    task = asyncio.create_task(test_obj.cancellable_operation())
    await asyncio.sleep(0.5)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("   Операция успешно отменена и залогирована")
    
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
    print("=" * 60)


if __name__ == "__main__":
    # Запускаем асинхронную главную функцию
    asyncio.run(main())
