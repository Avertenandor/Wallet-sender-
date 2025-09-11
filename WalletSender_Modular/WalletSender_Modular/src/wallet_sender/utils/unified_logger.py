#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Единый менеджер логирования для WalletSender
Обеспечивает синхронизацию логов между всеми окнами
"""

from typing import List, Callable, Optional
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal

class UnifiedLogManager(QObject):
    """Единый менеджер логирования"""
    
    # Сигнал для оповещения всех подписчиков о новом логе
    log_added = pyqtSignal(str, str)  # message, level
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Проверяем флаг на уровне класса, а не экземпляра
        if not UnifiedLogManager._initialized:
            # Инициализируем родительский класс
            super(UnifiedLogManager, self).__init__()
            UnifiedLogManager._initialized = True
            self.subscribers: List[Callable] = []
            self.log_history: List[tuple] = []  # (timestamp, message, level)
            self.max_history = 1000
    
    def add_log(self, message: str, level: str = "INFO"):
        """Добавляет лог и уведомляет всех подписчиков"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Сохраняем в историю
        self.log_history.append((timestamp, message, level))
        if len(self.log_history) > self.max_history:
            self.log_history.pop(0)
        
        # Отправляем сигнал всем подписчикам
        self.log_added.emit(message, level)
        
        # Вызываем callback'и подписчиков
        for subscriber in self.subscribers:
            try:
                subscriber(message, level)
            except Exception as e:
                print(f"Ошибка вызова подписчика: {e}")
    
    def subscribe(self, callback: Callable):
        """Подписаться на получение логов"""
        if callback not in self.subscribers:
            self.subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable):
        """Отписаться от получения логов"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
    
    def get_history(self) -> List[tuple]:
        """Получить историю логов"""
        return self.log_history.copy()
    
    def clear_history(self):
        """Очистить историю логов"""
        self.log_history.clear()

# Глобальный экземпляр менеджера
_log_manager = None

def get_log_manager() -> UnifiedLogManager:
    """Получить единый менеджер логирования"""
    global _log_manager
    if _log_manager is None:
        _log_manager = UnifiedLogManager()
    return _log_manager

def unified_log(message: str, level: str = "INFO"):
    """Быстрый доступ к логированию"""
    get_log_manager().add_log(message, level)
