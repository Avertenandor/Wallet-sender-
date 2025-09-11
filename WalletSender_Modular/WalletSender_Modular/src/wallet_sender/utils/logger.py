"""
Logging utilities for WalletSender
"""

import logging
import sys
from typing import Optional
from pathlib import Path


# Настройка формата логов
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class UnicodeFormatter(logging.Formatter):
    """Форматтер логов с поддержкой Unicode и безопасной обработкой эмодзи"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Сначала заменяем эмодзи в самом сообщении до форматирования
        if hasattr(record, 'msg') and record.msg:
            # Заменяем проблемные Unicode символы на безопасные альтернативы
            emoji_replacements = {
                '[START]': '[START]',
                '[OK]': '[OK]',
                '[ERROR]': '[ERROR]',
                '[WARN]': '[WARN]',
                '[THEME]': '[THEME]',
                '[CONFIG]': '[CONFIG]',
                '[INFO]': '[INFO]',
                '[CONNECT]': '[CONNECT]',
                '[DISCONNECT]': '[DISCONNECT]',
                '[MONEY]': '[MONEY]',
                '[BUY]': '[BUY]',
                '[SEND]': '[SEND]',
                '[MASS]': '[MASS]',
                '[SEARCH]': '[SEARCH]',
                '[HISTORY]': '[HISTORY]',
                '[SETTINGS]': '[SETTINGS]',
                '[BYE]': '[BYE]',
                '[STATS]': '[STATS]',
                '[TARGET]': '[TARGET]',
                '[FINISH]': '[FINISH]'
            }
            
            # Преобразуем сообщение в строку если нужно
            msg = str(record.msg)
            for emoji, replacement in emoji_replacements.items():
                msg = msg.replace(emoji, replacement)
            record.msg = msg
        
        # Теперь форматируем обычным способом
        try:
            formatted = super().format(record)
            # Дополнительная очистка для Windows консоли
            formatted = formatted.encode('cp1251', errors='replace').decode('cp1251')
            return formatted
        except UnicodeEncodeError:
            # Если все еще проблема с кодировкой - делаем полную очистку
            formatted = super().format(record)
            return formatted.encode('ascii', errors='replace').decode('ascii')
        
        # Дополнительная очистка от других Unicode символов
        try:
            # Пытаемся закодировать в cp1251 для проверки совместимости
            formatted.encode('cp1251')
        except UnicodeEncodeError:
            # Если не получается, используем ASCII с заменой
            formatted = formatted.encode('ascii', errors='replace').decode('ascii')
        
        return formatted


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """
    Настройка системы логирования
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Путь к файлу для сохранения логов
    """
    # Получаем числовой уровень
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    # Получаем корневой логгер
    root_logger = logging.getLogger()
    
    # Если логгер уже настроен (есть хендлеры), проверяем необходимость обновления
    if root_logger.handlers:
        # Проверяем, есть ли уже файловый хендлер с нужным путем
        has_file_handler = False
        has_console_handler = False
        
        for handler in root_logger.handlers:
            if isinstance(handler, logging.FileHandler):
                has_file_handler = True
            elif isinstance(handler, logging.StreamHandler):
                has_console_handler = True
        
        # Если все хендлеры уже есть, просто обновляем уровень
        if (has_console_handler and (not log_file or has_file_handler)):
            root_logger.setLevel(numeric_level)
            return
        
        # Иначе очищаем старые хендлеры
        root_logger.handlers.clear()
    
    # Настраиваем новые хендлеры
    root_logger.setLevel(numeric_level)
    
    # Консольный обработчик с UTF-8 поддержкой
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(UnicodeFormatter(LOG_FORMAT, DATE_FORMAT))
    root_logger.addHandler(console_handler)
    
    # Файловый обработчик (если указан)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))  # В файл записываем с эмодзи
        root_logger.addHandler(file_handler)
    
    # Устанавливаем уровень для библиотек
    logging.getLogger("web3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Получение логгера для модуля
    
    Args:
        name: Имя модуля (обычно __name__)
        
    Returns:
        Настроенный логгер
    """
    return logging.getLogger(name)


def setup_logger(name: str = "WalletSender", log_file: Optional[str] = None, 
                 log_level: str = "INFO") -> logging.Logger:
    """
    Создание и настройка логгера (для совместимости с run_app.py)
    
    Args:
        name: Имя логгера
        log_file: Путь к файлу логов
        log_level: Уровень логирования
        
    Returns:
        Настроенный логгер
    """
    # Настраиваем систему логирования
    setup_logging(log_level, log_file)
    
    # Возвращаем логгер с указанным именем
    return get_logger(name)


# Глобальная настройка при импорте
setup_logging()
