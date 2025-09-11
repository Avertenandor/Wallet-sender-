"""
Улучшенная система логирования с автоматическим перехватом действий пользователя
"""

import logging
import functools
import asyncio
import traceback
import inspect
from typing import Optional, Callable, Any, Union
from pathlib import Path
from datetime import datetime


# Глобальный обработчик для UI логов
_ui_log_handler = None


def _get_context_info(func: Callable, args: tuple, kwargs: dict) -> dict:
    """
    Получение контекстной информации о вызове функции
    
    Args:
        func: Функция
        args: Позиционные аргументы
        kwargs: Именованные аргументы
    
    Returns:
        Словарь с контекстной информацией
    """
    context = {
        'module': func.__module__,
        'function': func.__name__,
        'self_obj': None,
        'class_name': None
    }
    
    # Определяем, является ли это методом класса
    if args and hasattr(args[0], '__class__'):
        # Проверяем, что это действительно метод класса
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        if params and params[0] == 'self':
            context['self_obj'] = args[0]
            context['class_name'] = args[0].__class__.__name__
    
    # Добавляем информацию о файле и строке
    frame = inspect.currentframe()
    if frame and frame.f_back and frame.f_back.f_back:
        context['file'] = frame.f_back.f_back.f_code.co_filename
        context['line'] = frame.f_back.f_back.f_lineno
    
    return context


def _format_action_message(name: str, context: dict, kwargs: Optional[dict] = None) -> str:
    """
    Форматирование сообщения о действии
    
    Args:
        name: Название действия
        context: Контекстная информация
        kwargs: Параметры для логирования
    
    Returns:
        Отформатированное сообщение
    """
    if context.get('class_name'):
        message = f"[{context['class_name']}] Действие: {name}"
    else:
        message = f"Действие: {name}"
    
    # Добавляем параметры если есть
    if kwargs:
        # Ограничиваем длину строковых параметров
        params_str = ", ".join(
            f"{k}={_truncate_str(v, 50)}" 
            for k, v in kwargs.items()
        )
        message += f" ({params_str})"
    
    return message


def _format_result(result: Any, max_length: int = 100) -> str:
    """
    Форматирование результата для логирования
    
    Args:
        result: Результат для форматирования
        max_length: Максимальная длина строки
    
    Returns:
        Отформатированный результат
    """
    result_str = str(result)
    return _truncate_str(result_str, max_length)


def _truncate_str(s: Any, max_length: int = 50) -> str:
    """
    Обрезание строки до максимальной длины
    
    Args:
        s: Строка или объект для обрезания
        max_length: Максимальная длина
    
    Returns:
        Обрезанная строка
    """
    s_str = str(s)
    if len(s_str) > max_length:
        return s_str[:max_length] + '...'
    return s_str


def _log_error(action_name: str, error: Exception, context: dict):
    """
    Детальное логирование ошибки
    
    Args:
        action_name: Название действия
        error: Ошибка
        context: Контекстная информация
    """
    error_msg = f"[ERROR] {action_name} ошибка: {str(error)}"
    
    # Добавляем информацию о типе ошибки
    error_msg += f" [{error.__class__.__name__}]"
    
    # Логируем основное сообщение
    log_to_ui(error_msg, "ERROR")
    
    # Логируем детали в отдельных сообщениях с уровнем DEBUG
    if context.get('file'):
        log_to_ui(f"  📍 Файл: {context['file']}:{context.get('line', '?')}", "DEBUG")
    
    # Получаем краткий стек вызовов (только последние 3 строки)
    tb_lines = traceback.format_exception(type(error), error, error.__traceback__)
    if tb_lines:
        # Берем только последние строки с файлами
        relevant_lines = []
        for line in tb_lines:
            if 'File "' in line and '.py"' in line:
                relevant_lines.append(line.strip())
        
        if relevant_lines:
            # Оставляем только последние 3 строки
            for line in relevant_lines[-3:]:
                log_to_ui(f"  🔴 {line}", "DEBUG")


def set_ui_log_handler(handler: Callable[[str, str], None]):
    """
    Установка обработчика для отправки логов в UI
    
    Args:
        handler: Функция для обработки логов (message, level)
    """
    global _ui_log_handler
    _ui_log_handler = handler


def log_to_ui(message: str, level: str = "INFO"):
    """
    Отправка лога в UI если обработчик установлен
    
    Args:
        message: Сообщение для логирования
        level: Уровень логирования
    """
    if _ui_log_handler:
        try:
            _ui_log_handler(message, level)
        except Exception as e:
            print(f"Ошибка отправки лога в UI: {e}")


def log_action(action_name: str = None, level: str = "INFO", log_result: bool = False, log_params: bool = True):
    """
    Декоратор для автоматического логирования действий пользователя
    Поддерживает как синхронные, так и асинхронные функции
    
    Args:
        action_name: Название действия (если не указано, используется имя функции)
        level: Уровень логирования
        log_result: Логировать ли результат выполнения
        log_params: Логировать ли параметры вызова
    """
    def decorator(func):
        # Проверяем, является ли функция асинхронной
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Определяем имя действия
                name = action_name or func.__name__.replace('_', ' ').title()
                
                # Получаем контекст
                context = _get_context_info(func, args, kwargs)
                
                # Формируем сообщение о начале действия
                message = _format_action_message(name, context, kwargs if log_params else None)
                
                # Логируем начало действия
                log_to_ui(f"▶ {message}", level)
                
                try:
                    # Выполняем асинхронную функцию
                    result = await func(*args, **kwargs)
                    
                    # Логируем успешное завершение
                    if log_result and result is not None:
                        log_to_ui(f"[OK] {name} завершено. Результат: {_format_result(result)}", "SUCCESS")
                    else:
                        log_to_ui(f"[OK] {name} завершено", "SUCCESS")
                    
                    return result
                    
                except Exception as e:
                    # Логируем ошибку с деталями
                    _log_error(name, e, context)
                    raise
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Определяем имя действия
                name = action_name or func.__name__.replace('_', ' ').title()
                
                # Получаем контекст
                context = _get_context_info(func, args, kwargs)
                
                # Формируем сообщение о начале действия
                message = _format_action_message(name, context, kwargs if log_params else None)
                
                # Логируем начало действия
                log_to_ui(f"▶ {message}", level)
                
                try:
                    # Выполняем синхронную функцию
                    result = func(*args, **kwargs)
                    
                    # Логируем успешное завершение
                    if log_result and result is not None:
                        log_to_ui(f"[OK] {name} завершено. Результат: {_format_result(result)}", "SUCCESS")
                    else:
                        log_to_ui(f"[OK] {name} завершено", "SUCCESS")
                    
                    return result
                    
                except Exception as e:
                    # Логируем ошибку с деталями
                    _log_error(name, e, context)
                    raise
            
            return sync_wrapper
    return decorator


def log_click(button_name: str = None):
    """
    Декоратор для логирования нажатий на кнопки
    
    Args:
        button_name: Название кнопки
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = button_name or func.__name__.replace('_', ' ').title()
            log_to_ui(f"🖱️ Нажата кнопка: {name}", "INFO")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_input_change(field_name: str = None):
    """
    Декоратор для логирования изменений в полях ввода
    
    Args:
        field_name: Название поля
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = field_name or func.__name__.replace('_', ' ').title()
            
            # Пытаемся получить новое значение
            value = args[1] if len(args) > 1 else kwargs.get('value', kwargs.get('text', ''))
            
            if value:
                log_to_ui(f"✏️ Изменено поле '{name}': {value}", "DEBUG")
            else:
                log_to_ui(f"✏️ Изменено поле '{name}'", "DEBUG")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_tab_change(func):
    """
    Декоратор для логирования переключения вкладок
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Пытаемся получить индекс вкладки
        tab_index = args[1] if len(args) > 1 else kwargs.get('index', -1)
        
        # Пытаемся получить объект вкладки для получения имени
        self_obj = args[0] if args else None
        if self_obj and hasattr(self_obj, 'tab_widget'):
            tab_name = self_obj.tab_widget.tabText(tab_index)
            log_to_ui(f"[DOC] Переключение на вкладку: {tab_name}", "INFO")
        else:
            log_to_ui(f"[DOC] Переключение на вкладку #{tab_index}", "INFO")
        
        return func(*args, **kwargs)
    return wrapper


def log_window_action(action: str):
    """
    Декоратор для логирования действий с окнами
    
    Args:
        action: Описание действия
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            log_to_ui(f"🪟 {action}", "INFO")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_network_action(action: str):
    """
    Декоратор для логирования сетевых операций
    
    Args:
        action: Описание операции
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            log_to_ui(f"[WEB] {action}...", "INFO")
            
            try:
                result = func(*args, **kwargs)
                log_to_ui(f"[OK] {action} выполнено", "SUCCESS")
                return result
            except Exception as e:
                log_to_ui(f"[ERROR] {action} ошибка: {str(e)}", "ERROR")
                raise
                
        return wrapper
    return decorator


def log_async_action(action_name: str = None):
    """
    Декоратор специально для асинхронных операций
    
    Args:
        action_name: Название операции
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            name = action_name or func.__name__.replace('_', ' ').title()
            
            # Получаем контекст
            context = _get_context_info(func, args, kwargs)
            
            log_to_ui(f"[MINIMAL] Асинхронная операция: {name}...", "INFO")
            
            try:
                result = await func(*args, **kwargs)
                log_to_ui(f"[OK] {name} выполнено", "SUCCESS")
                return result
            except asyncio.CancelledError:
                log_to_ui(f"[WARN] {name} отменено", "WARNING")
                raise
            except Exception as e:
                _log_error(name, e, context)
                raise
                
        return wrapper
    return decorator


def log_transaction(func):
    """
    Декоратор для логирования транзакций
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Пытаемся извлечь информацию о транзакции
        self_obj = args[0] if args else None
        
        log_to_ui(f"[MONEY] Начало транзакции...", "INFO")
        
        try:
            result = func(*args, **kwargs)
            
            # Пытаемся получить хэш транзакции из результата
            if isinstance(result, str) and result.startswith('0x'):
                log_to_ui(f"[OK] Транзакция отправлена: {result[:20]}...", "SUCCESS")
            elif isinstance(result, dict) and 'tx_hash' in result:
                log_to_ui(f"[OK] Транзакция отправлена: {result['tx_hash'][:20]}...", "SUCCESS")
            else:
                log_to_ui(f"[OK] Транзакция завершена", "SUCCESS")
            
            return result
            
        except Exception as e:
            log_to_ui(f"[ERROR] Ошибка транзакции: {str(e)}", "ERROR")
            raise
            
    return wrapper


def log_file_operation(operation: str):
    """
    Декоратор для логирования файловых операций
    
    Args:
        operation: Тип операции (загрузка, сохранение и т.д.)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            log_to_ui(f"📁 {operation}...", "INFO")
            
            try:
                result = func(*args, **kwargs)
                
                # Пытаемся получить имя файла из результата или аргументов
                filename = None
                if isinstance(result, str):
                    filename = Path(result).name
                elif len(args) > 1 and isinstance(args[1], str):
                    filename = Path(args[1]).name
                
                if filename:
                    log_to_ui(f"[OK] {operation} завершено: {filename}", "SUCCESS")
                else:
                    log_to_ui(f"[OK] {operation} завершено", "SUCCESS")
                
                return result
                
            except Exception as e:
                log_to_ui(f"[ERROR] Ошибка {operation}: {str(e)}", "ERROR")
                raise
                
        return wrapper
    return decorator


def log_settings_change(setting_name: str):
    """
    Декоратор для логирования изменения настроек
    
    Args:
        setting_name: Название настройки
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Пытаемся получить новое значение
            value = args[1] if len(args) > 1 else kwargs.get('value', '')
            
            log_to_ui(f"[SETTINGS] Изменена настройка '{setting_name}': {value}", "INFO")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_dropdown_change(field_name: str = None):
    """
    Декоратор для логирования изменений в выпадающих списках
    
    Args:
        field_name: Название поля
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = field_name or func.__name__.replace('_', ' ').title()
            
            # Пытаемся получить новое значение
            value = args[1] if len(args) > 1 else kwargs.get('value', kwargs.get('text', ''))
            
            log_to_ui(f"[INFO] Выбран '{name}': {value}", "INFO")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_checkbox_change(checkbox_name: str = None):
    """
    Декоратор для логирования изменений чекбоксов
    
    Args:
        checkbox_name: Название чекбокса
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = checkbox_name or func.__name__.replace('_', ' ').title()
            
            # Пытаемся получить состояние
            checked = args[1] if len(args) > 1 else kwargs.get('checked', kwargs.get('state', False))
            state = "включен" if checked else "выключен"
            
            log_to_ui(f"☑️ '{name}' {state}", "INFO")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_radio_change(radio_group: str = None):
    """
    Декоратор для логирования изменений радио-кнопок
    
    Args:
        radio_group: Название группы радио-кнопок
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            group = radio_group or "Радио-группа"
            
            # Пытаемся получить выбранный элемент
            value = args[1] if len(args) > 1 else kwargs.get('value', kwargs.get('text', ''))
            
            log_to_ui(f"⭕ {group}: выбрано '{value}'", "INFO")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_slider_change(slider_name: str = None):
    """
    Декоратор для логирования изменений слайдеров
    
    Args:
        slider_name: Название слайдера
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = slider_name or func.__name__.replace('_', ' ').title()
            
            # Пытаемся получить значение
            value = args[1] if len(args) > 1 else kwargs.get('value', 0)
            
            log_to_ui(f"🎚️ '{name}' изменен на: {value}", "DEBUG")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_spinbox_change(spinbox_name: str = None):
    """
    Декоратор для логирования изменений SpinBox
    
    Args:
        spinbox_name: Название SpinBox
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = spinbox_name or func.__name__.replace('_', ' ').title()
            
            # Пытаемся получить значение
            value = args[1] if len(args) > 1 else kwargs.get('value', 0)
            
            log_to_ui(f"🔢 '{name}' изменен на: {value}", "DEBUG")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_table_action(action: str):
    """
    Декоратор для логирования действий с таблицами
    
    Args:
        action: Описание действия
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            log_to_ui(f"[STATS] Таблица: {action}", "INFO")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_dialog_action(dialog_name: str):
    """
    Декоратор для логирования открытия диалогов
    
    Args:
        dialog_name: Название диалога
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            log_to_ui(f"💬 Открыт диалог: {dialog_name}", "INFO")
            
            result = func(*args, **kwargs)
            
            if result is not None:
                log_to_ui(f"[OK] Диалог '{dialog_name}' закрыт с результатом: {result}", "DEBUG")
            
            return result
        return wrapper
    return decorator


def log_validation(validation_name: str = None):
    """
    Декоратор для логирования валидации
    
    Args:
        validation_name: Название валидации
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = validation_name or func.__name__.replace('_', ' ').title()
            
            log_to_ui(f"[CHECK] Проверка: {name}...", "DEBUG")
            
            try:
                result = func(*args, **kwargs)
                
                if result:
                    log_to_ui(f"[OK] {name}: успешно", "SUCCESS")
                else:
                    log_to_ui(f"[WARN] {name}: не пройдена", "WARNING")
                
                return result
                
            except Exception as e:
                log_to_ui(f"[ERROR] {name}: ошибка - {str(e)}", "ERROR")
                raise
                
        return wrapper
    return decorator


def log_api_call(api_name: str):
    """
    Декоратор для логирования API вызовов
    
    Args:
        api_name: Название API
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            log_to_ui(f"[DISCONNECT] API вызов: {api_name}...", "INFO")
            
            try:
                result = func(*args, **kwargs)
                log_to_ui(f"[OK] API {api_name}: успешно", "SUCCESS")
                return result
            except Exception as e:
                log_to_ui(f"[ERROR] API {api_name} ошибка: {str(e)}", "ERROR")
                raise
                
        return wrapper
    return decorator


def log_currency_change(func):
    """
    Декоратор для логирования смены валюты
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Пытаемся получить новую валюту
        currency = args[1] if len(args) > 1 else kwargs.get('currency', kwargs.get('token', ''))
        
        log_to_ui(f"💱 Смена валюты на: {currency}", "INFO")
        
        return func(*args, **kwargs)
    return wrapper


def log_time_change(func):
    """
    Декоратор для логирования изменения времени/интервалов
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Пытаемся получить новое время
        time_value = args[1] if len(args) > 1 else kwargs.get('time', kwargs.get('interval', ''))
        
        log_to_ui(f"⏰ Изменено время/интервал: {time_value}", "INFO")
        
        return func(*args, **kwargs)
    return wrapper


class EnhancedLogger:
    """
    Класс для улучшенного логирования с поддержкой UI
    """
    
    def __init__(self, name: str, ui_handler: Optional[Callable] = None):
        """
        Инициализация логгера
        
        Args:
            name: Имя логгера
            ui_handler: Обработчик для отправки логов в UI
        """
        self.logger = logging.getLogger(name)
        self.ui_handler = ui_handler
        
        # Устанавливаем глобальный обработчик если передан
        if ui_handler:
            set_ui_log_handler(ui_handler)
    
    def log(self, message: str, level: str = "INFO"):
        """
        Логирование сообщения
        
        Args:
            message: Сообщение
            level: Уровень логирования
        """
        # Логируем в стандартный логгер
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.log(log_level, message)
        
        # Отправляем в UI
        log_to_ui(message, level)
    
    def debug(self, message: str):
        """Debug сообщение"""
        self.log(message, "DEBUG")
    
    def info(self, message: str):
        """Info сообщение"""
        self.log(message, "INFO")
    
    def warning(self, message: str):
        """Warning сообщение"""
        self.log(message, "WARNING")
    
    def error(self, message: str):
        """Error сообщение"""
        self.log(message, "ERROR")
    
    def success(self, message: str):
        """Success сообщение"""
        self.log(message, "SUCCESS")
    
    def transaction(self, message: str):
        """Сообщение о транзакции"""
        self.log(f"[MONEY] {message}", "INFO")
    
    def network(self, message: str):
        """Сообщение о сетевой операции"""
        self.log(f"[WEB] {message}", "INFO")
    
    def action(self, message: str):
        """Сообщение о действии пользователя"""
        self.log(f"▶ {message}", "INFO")
