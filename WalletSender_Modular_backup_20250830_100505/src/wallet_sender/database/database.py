"""
Управление подключением к базе данных
"""

import os
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from .models import Base
from ..utils.logger import get_logger

logger = get_logger(__name__)


class Database:
    """Класс для управления подключением к базе данных"""
    
    def __init__(self, db_url: Optional[str] = None):
        """
        Инициализация подключения к БД
        
        Args:
            db_url: URL подключения к БД (по умолчанию SQLite)
        """
        if db_url is None:
            # По умолчанию используем SQLite
            db_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'wallet_sender.db')
            db_url = f'sqlite:///{db_path}'
            
        self.db_url = db_url
        self.engine = None
        self.SessionLocal = None
        
        self._init_database()
        
    def _init_database(self):
        """Инициализация базы данных"""
        try:
            # Создаем engine
            self.engine = create_engine(
                self.db_url,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                echo=False  # Установить True для отладки SQL запросов
            )
            
            # Создаем таблицы если их нет
            Base.metadata.create_all(bind=self.engine)
            
            # Создаем фабрику сессий
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info(f"База данных инициализирована: {self.db_url}")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
            raise
            
    def get_session(self) -> Session:
        """
        Получение сессии базы данных
        
        Returns:
            Session: Сессия SQLAlchemy
        """
        if self.SessionLocal is None:
            raise RuntimeError("База данных не инициализирована")
            
        return self.SessionLocal()
        
    def close(self):
        """Закрытие подключения к БД"""
        if self.engine:
            self.engine.dispose()
            logger.info("Подключение к базе данных закрыто")
            
    def __enter__(self):
        """Контекстный менеджер - вход"""
        self.session = self.get_session()
        return self.session
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход"""
        try:
            if exc_type is None:
                self.session.commit()
            else:
                self.session.rollback()
        finally:
            self.session.close()
            
    def drop_all_tables(self):
        """Удаление всех таблиц (ОСТОРОЖНО!)"""
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("Все таблицы удалены из базы данных")
        
    def recreate_tables(self):
        """Пересоздание всех таблиц"""
        self.drop_all_tables()
        Base.metadata.create_all(bind=self.engine)
        logger.info("Таблицы пересозданы")


# Глобальный экземпляр базы данных
_database_instance: Optional[Database] = None


def get_database() -> Database:
    """
    Получение глобального экземпляра базы данных
    
    Returns:
        Database: Экземпляр базы данных
    """
    global _database_instance
    
    if _database_instance is None:
        _database_instance = Database()
        
    return _database_instance


def close_database():
    """Закрытие глобального подключения к БД"""
    global _database_instance
    
    if _database_instance:
        _database_instance.close()
        _database_instance = None
