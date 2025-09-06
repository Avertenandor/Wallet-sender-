"""
Единое хранилище данных для WalletSender
Реализует SQLite схему с FTS5 поиском
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager

from ..utils.logger import get_logger

logger = get_logger(__name__)


class Store:
    """Единое хранилище данных с SQLite и FTS5"""
    
    def __init__(self, db_path: str = None):
        """
        Инициализация хранилища
        
        Args:
            db_path: Путь к файлу базы данных
        """
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'wallet_sender_store.db')
            
        self.db_path = db_path
        self._init_database()
        
    def _init_database(self):
        """Инициализация структуры базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица настроек
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    category TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица задач (jobs)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    mode TEXT NOT NULL,  -- distribution, auto_buy, auto_sell, rewards
                    state TEXT NOT NULL,  -- pending, running, paused, completed, failed
                    total INTEGER DEFAULT 0,
                    done INTEGER DEFAULT 0,
                    failed INTEGER DEFAULT 0,
                    eta DATETIME,
                    config TEXT,  -- JSON с конфигурацией задачи
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    started_at DATETIME,
                    completed_at DATETIME,
                    error_message TEXT
                )
            ''')
            
            # Таблица истории транзакций
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tx_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tx_hash TEXT UNIQUE,
                    from_address TEXT NOT NULL,
                    to_address TEXT NOT NULL,
                    token_address TEXT,
                    token_symbol TEXT,
                    amount REAL,
                    gas_price REAL,
                    gas_used INTEGER,
                    gas_limit INTEGER,
                    status TEXT,  -- pending, success, failed
                    type TEXT,  -- transfer, reward, distribution, buy, sell
                    job_id INTEGER,
                    note TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at DATETIME,
                    block_number INTEGER,
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
                )
            ''')
            
            # Таблица наград
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rewards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    address TEXT NOT NULL,
                    token TEXT NOT NULL,
                    amount REAL NOT NULL,
                    source_job INTEGER,
                    source_tx TEXT,
                    note TEXT,
                    status TEXT DEFAULT 'pending',  -- pending, sent, failed
                    sent_tx_hash TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    sent_at DATETIME,
                    FOREIGN KEY (source_job) REFERENCES jobs(job_id)
                )
            ''')
            
            # Таблица найденных транзакций (для анализа)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS found_tx (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tx_hash TEXT UNIQUE,
                    from_address TEXT,
                    to_address TEXT,
                    token_address TEXT,
                    token_symbol TEXT,
                    amount REAL,
                    block_number INTEGER,
                    timestamp DATETIME,
                    method TEXT,  -- transfer, swap, mint, burn
                    found_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    analyzed BOOLEAN DEFAULT 0,
                    note TEXT
                )
            ''')
            
            # FTS5 таблица для полнотекстового поиска
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS tx_search USING fts5(
                    tx_hash,
                    from_address,
                    to_address,
                    note,
                    content=tx_history,
                    content_rowid=id
                )
            ''')
            
            # Триггеры для синхронизации FTS5
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS tx_history_ai AFTER INSERT ON tx_history BEGIN
                    INSERT INTO tx_search(rowid, tx_hash, from_address, to_address, note)
                    VALUES (new.id, new.tx_hash, new.from_address, new.to_address, new.note);
                END
            ''')
            
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS tx_history_au AFTER UPDATE ON tx_history BEGIN
                    UPDATE tx_search 
                    SET tx_hash = new.tx_hash,
                        from_address = new.from_address,
                        to_address = new.to_address,
                        note = new.note
                    WHERE rowid = new.id;
                END
            ''')
            
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS tx_history_ad AFTER DELETE ON tx_history BEGIN
                    DELETE FROM tx_search WHERE rowid = old.id;
                END
            ''')
            
            # Создание индексов для оптимизации
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tx_hash ON tx_history(tx_hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_from_address ON tx_history(from_address)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_to_address ON tx_history(to_address)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON tx_history(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_type ON tx_history(type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_id ON tx_history(job_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON tx_history(created_at)')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_rewards_address ON rewards(address)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_rewards_status ON rewards(status)')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_mode ON jobs(mode)')
            
            conn.commit()
            logger.info(f"База данных инициализирована: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для получения соединения с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    # Методы для работы с настройками
    def save_settings(self, settings: Dict[str, Any]):
        """Сохранение настроек"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for key, value in settings.items():
                if isinstance(value, dict):
                    value = json.dumps(value)
                elif not isinstance(value, str):
                    value = str(value)
                    
                cursor.execute('''
                    INSERT OR REPLACE INTO settings (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (key, value))
            conn.commit()
            logger.info("Настройки сохранены")
    
    def load_settings(self) -> Dict[str, Any]:
        """Загрузка всех настроек"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM settings')
            settings = {}
            for row in cursor.fetchall():
                key = row['key']
                value = row['value']
                # Пытаемся распарсить JSON
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass
                settings[key] = value
            return settings
    
    def get_setting(self, key: str, default=None):
        """Получение конкретной настройки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            if row:
                value = row['value']
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return default
    
    # Методы для работы с задачами (jobs)
    def create_job(self, title: str, mode: str, config: Dict = None) -> int:
        """Создание новой задачи"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            config_json = json.dumps(config) if config else '{}'
            cursor.execute('''
                INSERT INTO jobs (title, mode, state, config)
                VALUES (?, ?, 'pending', ?)
            ''', (title, mode, config_json))
            conn.commit()
            job_id = cursor.lastrowid
            logger.info(f"Создана задача #{job_id}: {title}")
            return job_id
    
    def update_job(self, job_id: int, **kwargs):
        """Обновление задачи"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Формируем SQL запрос динамически
            set_clauses = []
            values = []
            for key, value in kwargs.items():
                if key == 'config' and isinstance(value, dict):
                    value = json.dumps(value)
                set_clauses.append(f"{key} = ?")
                values.append(value)
            
            if set_clauses:
                values.append(job_id)
                query = f"UPDATE jobs SET {', '.join(set_clauses)} WHERE job_id = ?"
                cursor.execute(query, values)
                conn.commit()
    
    def get_job(self, job_id: int) -> Optional[Dict]:
        """Получение информации о задаче"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM jobs WHERE job_id = ?', (job_id,))
            row = cursor.fetchone()
            if row:
                job = dict(row)
                if job.get('config'):
                    try:
                        job['config'] = json.loads(job['config'])
                    except json.JSONDecodeError:
                        job['config'] = {}
                return job
            return None
    
    def get_jobs(self, state: str = None, mode: str = None, limit: int = 100) -> List[Dict]:
        """Получение списка задач"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM jobs WHERE 1=1'
            params = []
            
            if state:
                query += ' AND state = ?'
                params.append(state)
            if mode:
                query += ' AND mode = ?'
                params.append(mode)
                
            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            jobs = []
            for row in cursor.fetchall():
                job = dict(row)
                if job.get('config'):
                    try:
                        job['config'] = json.loads(job['config'])
                    except json.JSONDecodeError:
                        job['config'] = {}
                jobs.append(job)
            return jobs
    
    # Методы для работы с историей транзакций
    def add_transaction(self, **kwargs) -> int:
        """Добавление транзакции в историю"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Подготавливаем поля
            fields = ['tx_hash', 'from_address', 'to_address', 'token_address', 
                     'token_symbol', 'amount', 'gas_price', 'gas_used', 'gas_limit',
                     'status', 'type', 'job_id', 'note', 'block_number']
            
            columns = []
            placeholders = []
            values = []
            
            for field in fields:
                if field in kwargs:
                    columns.append(field)
                    placeholders.append('?')
                    values.append(kwargs[field])
            
            if columns:
                query = f"INSERT INTO tx_history ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                cursor.execute(query, values)
                conn.commit()
                tx_id = cursor.lastrowid
                logger.info(f"Добавлена транзакция #{tx_id}: {kwargs.get('tx_hash', 'N/A')}")
                return tx_id
            return 0
    
    def update_transaction(self, tx_hash: str, **kwargs):
        """Обновление транзакции"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            set_clauses = []
            values = []
            for key, value in kwargs.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)
            
            if set_clauses:
                values.append(tx_hash)
                query = f"UPDATE tx_history SET {', '.join(set_clauses)} WHERE tx_hash = ?"
                cursor.execute(query, values)
                conn.commit()
    
    def get_transactions(self, filters: Dict = None, limit: int = 100, offset: int = 0) -> Tuple[List[Dict], int]:
        """
        Получение транзакций с фильтрацией и пагинацией
        
        Returns:
            Tuple[List[Dict], int]: Список транзакций и общее количество
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Базовый запрос
            query = 'SELECT * FROM tx_history WHERE 1=1'
            count_query = 'SELECT COUNT(*) FROM tx_history WHERE 1=1'
            params = []
            
            # Применяем фильтры
            if filters:
                if 'status' in filters:
                    query += ' AND status = ?'
                    count_query += ' AND status = ?'
                    params.append(filters['status'])
                    
                if 'type' in filters:
                    query += ' AND type = ?'
                    count_query += ' AND type = ?'
                    params.append(filters['type'])
                    
                if 'from_address' in filters:
                    query += ' AND from_address = ?'
                    count_query += ' AND from_address = ?'
                    params.append(filters['from_address'])
                    
                if 'to_address' in filters:
                    query += ' AND to_address = ?'
                    count_query += ' AND to_address = ?'
                    params.append(filters['to_address'])
                    
                if 'job_id' in filters:
                    query += ' AND job_id = ?'
                    count_query += ' AND job_id = ?'
                    params.append(filters['job_id'])
                    
                if 'date_from' in filters:
                    query += ' AND created_at >= ?'
                    count_query += ' AND created_at >= ?'
                    params.append(filters['date_from'])
                    
                if 'date_to' in filters:
                    query += ' AND created_at <= ?'
                    count_query += ' AND created_at <= ?'
                    params.append(filters['date_to'])
            
            # Получаем общее количество
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]
            
            # Добавляем сортировку и пагинацию
            query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            # Получаем транзакции
            cursor.execute(query, params)
            transactions = [dict(row) for row in cursor.fetchall()]
            
            return transactions, total_count
    
    def search_transactions(self, search_text: str, limit: int = 100) -> List[Dict]:
        """Полнотекстовый поиск транзакций"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Поиск через FTS5
            cursor.execute('''
                SELECT h.* FROM tx_history h
                JOIN tx_search s ON h.id = s.rowid
                WHERE tx_search MATCH ?
                ORDER BY h.created_at DESC
                LIMIT ?
            ''', (search_text, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # Методы для работы с наградами
    def add_reward(self, address: str, token: str, amount: float, 
                  source_job: int = None, source_tx: str = None, note: str = None) -> int:
        """Добавление награды"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO rewards (address, token, amount, source_job, source_tx, note)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (address, token, amount, source_job, source_tx, note))
            conn.commit()
            reward_id = cursor.lastrowid
            logger.info(f"Добавлена награда #{reward_id}: {amount} {token} для {address}")
            return reward_id
    
    def get_rewards(self, status: str = None, address: str = None, limit: int = 100) -> List[Dict]:
        """Получение списка наград"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM rewards WHERE 1=1'
            params = []
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            if address:
                query += ' AND address = ?'
                params.append(address)
                
            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_reward(self, reward_id: int, **kwargs):
        """Обновление награды"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            set_clauses = []
            values = []
            for key, value in kwargs.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)
            
            if set_clauses:
                values.append(reward_id)
                query = f"UPDATE rewards SET {', '.join(set_clauses)} WHERE id = ?"
                cursor.execute(query, values)
                conn.commit()
    
    # Методы для работы с найденными транзакциями
    def add_found_tx(self, **kwargs) -> int:
        """Добавление найденной транзакции"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            fields = ['tx_hash', 'from_address', 'to_address', 'token_address',
                     'token_symbol', 'amount', 'block_number', 'timestamp', 
                     'method', 'note']
            
            columns = []
            placeholders = []
            values = []
            
            for field in fields:
                if field in kwargs:
                    columns.append(field)
                    placeholders.append('?')
                    values.append(kwargs[field])
            
            if columns:
                query = f"INSERT OR IGNORE INTO found_tx ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                cursor.execute(query, values)
                conn.commit()
                return cursor.lastrowid
            return 0
    
    def get_found_tx(self, analyzed: bool = None, limit: int = 100) -> List[Dict]:
        """Получение найденных транзакций"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM found_tx WHERE 1=1'
            params = []
            
            if analyzed is not None:
                query += ' AND analyzed = ?'
                params.append(1 if analyzed else 0)
                
            query += ' ORDER BY found_at DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_found_tx_analyzed(self, tx_hash: str):
        """Пометить транзакцию как проанализированную"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE found_tx SET analyzed = 1 WHERE tx_hash = ?', (tx_hash,))
            conn.commit()
    
    # Статистика и аналитика
    def get_statistics(self) -> Dict[str, Any]:
        """Получение общей статистики"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Общее количество транзакций
            cursor.execute('SELECT COUNT(*) FROM tx_history')
            stats['total_transactions'] = cursor.fetchone()[0]
            
            # Транзакции по статусам
            cursor.execute('''
                SELECT status, COUNT(*) as count 
                FROM tx_history 
                GROUP BY status
            ''')
            stats['transactions_by_status'] = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Транзакции по типам
            cursor.execute('''
                SELECT type, COUNT(*) as count 
                FROM tx_history 
                GROUP BY type
            ''')
            stats['transactions_by_type'] = {row['type']: row['count'] for row in cursor.fetchall()}
            
            # Задачи по статусам
            cursor.execute('''
                SELECT state, COUNT(*) as count 
                FROM jobs 
                GROUP BY state
            ''')
            stats['jobs_by_state'] = {row['state']: row['count'] for row in cursor.fetchall()}
            
            # Награды
            cursor.execute('SELECT COUNT(*) FROM rewards')
            stats['total_rewards'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM rewards WHERE status = "sent"')
            stats['sent_rewards'] = cursor.fetchone()[0]
            
            # Найденные транзакции
            cursor.execute('SELECT COUNT(*) FROM found_tx')
            stats['total_found_tx'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM found_tx WHERE analyzed = 1')
            stats['analyzed_found_tx'] = cursor.fetchone()[0]
            
            return stats
    
    def get_transaction_volume(self, days: int = 7) -> List[Dict]:
        """Получение объема транзакций по дням"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as count,
                    SUM(amount) as volume
                FROM tx_history
                WHERE created_at >= datetime('now', '-' || ? || ' days')
                GROUP BY DATE(created_at)
                ORDER BY date
            ''', (days,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # Утилиты
    def vacuum(self):
        """Оптимизация базы данных"""
        with self.get_connection() as conn:
            conn.execute('VACUUM')
            logger.info("База данных оптимизирована")
    
    def get_db_size(self) -> int:
        """Получение размера базы данных в байтах"""
        return os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
    
    def export_to_csv(self, table: str, output_path: str):
        """Экспорт таблицы в CSV"""
        import csv
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT * FROM {table}')
            
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Заголовки
                writer.writerow([description[0] for description in cursor.description])
                
                # Данные
                writer.writerows(cursor.fetchall())
                
        logger.info(f"Таблица {table} экспортирована в {output_path}")


# Глобальный экземпляр хранилища
_store_instance: Optional[Store] = None


def get_store() -> Store:
    """Получение глобального экземпляра хранилища"""
    global _store_instance
    
    if _store_instance is None:
        _store_instance = Store()
        
    return _store_instance


def close_store():
    """Закрытие глобального хранилища"""
    global _store_instance
    _store_instance = None
