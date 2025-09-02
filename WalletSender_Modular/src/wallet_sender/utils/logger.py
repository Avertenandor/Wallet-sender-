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
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root_logger.addHandler(console_handler)
    
    # Файловый обработчик (если указан)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
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
