"""
Система аналитики и отчетности
"""

import time
import json
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import threading

class OperationType(Enum):
    """Типы операций"""
    BUY = "buy"
    SELL = "sell"
    TRANSFER = "transfer"
    APPROVE = "approve"

class OperationStatus(Enum):
    """Статусы операций"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Operation:
    """Запись об операции"""
    id: str
    timestamp: float
    operation_type: OperationType
    status: OperationStatus
    token_address: str
    token_symbol: str
    amount: float
    price_usd: Optional[float] = None
    gas_used: Optional[int] = None
    gas_price: Optional[int] = None
    gas_cost_usd: Optional[float] = None
    tx_hash: Optional[str] = None
    error_message: Optional[str] = None
    wallet_address: str = ""
    target_token: Optional[str] = None
    slippage: Optional[float] = None

@dataclass
class PerformanceMetrics:
    """Метрики производительности"""
    total_operations: int
    successful_operations: int
    failed_operations: int
    success_rate: float
    total_gas_used: int
    total_gas_cost_usd: float
    average_gas_per_operation: float
    total_volume_usd: float
    average_operation_time: float

class AnalyticsManager:
    """Менеджер аналитики"""
    
    def __init__(self, db_path: str = "analytics.db"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_database()
        
        # Кеш для быстрого доступа
        self._cache = {}
        self._cache_ttl = 60.0  # 1 минута
        self._last_cache_update = 0
    
    def _init_database(self):
        """Инициализирует базу данных"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица операций
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS operations (
                    id TEXT PRIMARY KEY,
                    timestamp REAL,
                    operation_type TEXT,
                    status TEXT,
                    token_address TEXT,
                    token_symbol TEXT,
                    amount REAL,
                    price_usd REAL,
                    gas_used INTEGER,
                    gas_price INTEGER,
                    gas_cost_usd REAL,
                    tx_hash TEXT,
                    error_message TEXT,
                    wallet_address TEXT,
                    target_token TEXT,
                    slippage REAL
                )
            ''')
            
            # Таблица цен токенов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS token_prices (
                    token_address TEXT,
                    timestamp REAL,
                    price_usd REAL,
                    PRIMARY KEY (token_address, timestamp)
                )
            ''')
            
            # Таблица метрик производительности
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    date TEXT PRIMARY KEY,
                    total_operations INTEGER,
                    successful_operations INTEGER,
                    failed_operations INTEGER,
                    success_rate REAL,
                    total_gas_used INTEGER,
                    total_gas_cost_usd REAL,
                    average_gas_per_operation REAL,
                    total_volume_usd REAL,
                    average_operation_time REAL
                )
            ''')
            
            conn.commit()
    
    def record_operation(self, operation: Operation) -> None:
        """Записывает операцию в базу данных"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO operations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    operation.id,
                    operation.timestamp,
                    operation.operation_type.value,
                    operation.status.value,
                    operation.token_address,
                    operation.token_symbol,
                    operation.amount,
                    operation.price_usd,
                    operation.gas_used,
                    operation.gas_price,
                    operation.gas_cost_usd,
                    operation.tx_hash,
                    operation.error_message,
                    operation.wallet_address,
                    operation.target_token,
                    operation.slippage
                ))
                
                conn.commit()
            
            # Инвалидируем кеш
            self._invalidate_cache()
    
    def record_token_price(self, token_address: str, price_usd: float) -> None:
        """Записывает цену токена"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO token_prices VALUES (?, ?, ?)
                ''', (token_address, time.time(), price_usd))
                
                conn.commit()
    
    def get_operations(self, start_time: Optional[float] = None, 
                      end_time: Optional[float] = None,
                      operation_type: Optional[OperationType] = None,
                      status: Optional[OperationStatus] = None,
                      limit: int = 1000) -> List[Operation]:
        """Получает операции по фильтрам"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM operations WHERE 1=1"
                params = []
                
                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time)
                
                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time)
                
                if operation_type:
                    query += " AND operation_type = ?"
                    params.append(operation_type.value)
                
                if status:
                    query += " AND status = ?"
                    params.append(status.value)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                operations = []
                for row in rows:
                    operation = Operation(
                        id=row[0],
                        timestamp=row[1],
                        operation_type=OperationType(row[2]),
                        status=OperationStatus(row[3]),
                        token_address=row[4],
                        token_symbol=row[5],
                        amount=row[6],
                        price_usd=row[7],
                        gas_used=row[8],
                        gas_price=row[9],
                        gas_cost_usd=row[10],
                        tx_hash=row[11],
                        error_message=row[12],
                        wallet_address=row[13],
                        target_token=row[14],
                        slippage=row[15]
                    )
                    operations.append(operation)
                
                return operations
    
    def get_performance_metrics(self, days: int = 30) -> PerformanceMetrics:
        """Получает метрики производительности"""
        cache_key = f"metrics_{days}"
        
        # Проверяем кеш
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        with self._lock:
            end_time = time.time()
            start_time = end_time - (days * 24 * 3600)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Общее количество операций
                cursor.execute('''
                    SELECT COUNT(*) FROM operations 
                    WHERE timestamp >= ? AND timestamp <= ?
                ''', (start_time, end_time))
                total_operations = cursor.fetchone()[0]
                
                # Успешные операции
                cursor.execute('''
                    SELECT COUNT(*) FROM operations 
                    WHERE timestamp >= ? AND timestamp <= ? AND status = ?
                ''', (start_time, end_time, OperationStatus.SUCCESS.value))
                successful_operations = cursor.fetchone()[0]
                
                # Неудачные операции
                failed_operations = total_operations - successful_operations
                
                # Успешность
                success_rate = (successful_operations / total_operations * 100) if total_operations > 0 else 0
                
                # Газ
                cursor.execute('''
                    SELECT SUM(gas_used), SUM(gas_cost_usd) FROM operations 
                    WHERE timestamp >= ? AND timestamp <= ? AND gas_used IS NOT NULL
                ''', (start_time, end_time))
                gas_result = cursor.fetchone()
                total_gas_used = gas_result[0] or 0
                total_gas_cost_usd = gas_result[1] or 0
                
                # Средний газ на операцию
                average_gas_per_operation = (total_gas_used / total_operations) if total_operations > 0 else 0
                
                # Объем торгов
                cursor.execute('''
                    SELECT SUM(amount * COALESCE(price_usd, 0)) FROM operations 
                    WHERE timestamp >= ? AND timestamp <= ? AND status = ?
                ''', (start_time, end_time, OperationStatus.SUCCESS.value))
                total_volume_usd = cursor.fetchone()[0] or 0
                
                # Среднее время операции (упрощенная оценка)
                average_operation_time = 30.0  # 30 секунд по умолчанию
                
                metrics = PerformanceMetrics(
                    total_operations=total_operations,
                    successful_operations=successful_operations,
                    failed_operations=failed_operations,
                    success_rate=success_rate,
                    total_gas_used=total_gas_used,
                    total_gas_cost_usd=total_gas_cost_usd,
                    average_gas_per_operation=average_gas_per_operation,
                    total_volume_usd=total_volume_usd,
                    average_operation_time=average_operation_time
                )
                
                # Кешируем результат
                self._cache[cache_key] = metrics
                self._last_cache_update = time.time()
                
                return metrics
    
    def get_token_statistics(self, token_address: str, days: int = 30) -> Dict[str, Any]:
        """Получает статистику по токену"""
        with self._lock:
            end_time = time.time()
            start_time = end_time - (days * 24 * 3600)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Операции с токеном
                cursor.execute('''
                    SELECT operation_type, status, amount, price_usd, gas_used, gas_cost_usd
                    FROM operations 
                    WHERE token_address = ? AND timestamp >= ? AND timestamp <= ?
                ''', (token_address, start_time, end_time))
                operations = cursor.fetchall()
                
                # Статистика
                total_operations = len(operations)
                buy_operations = len([op for op in operations if op[0] == OperationType.BUY.value])
                sell_operations = len([op for op in operations if op[0] == OperationType.SELL.value])
                successful_operations = len([op for op in operations if op[1] == OperationStatus.SUCCESS.value])
                
                # Объемы
                total_volume = sum(op[2] for op in operations if op[1] == OperationStatus.SUCCESS.value)
                total_volume_usd = sum(op[2] * (op[3] or 0) for op in operations if op[1] == OperationStatus.SUCCESS.value)
                
                # Газ
                total_gas_used = sum(op[4] or 0 for op in operations)
                total_gas_cost_usd = sum(op[5] or 0 for op in operations)
                
                return {
                    'token_address': token_address,
                    'period_days': days,
                    'total_operations': total_operations,
                    'buy_operations': buy_operations,
                    'sell_operations': sell_operations,
                    'successful_operations': successful_operations,
                    'success_rate': (successful_operations / total_operations * 100) if total_operations > 0 else 0,
                    'total_volume': total_volume,
                    'total_volume_usd': total_volume_usd,
                    'total_gas_used': total_gas_used,
                    'total_gas_cost_usd': total_gas_cost_usd,
                    'average_volume_per_operation': total_volume / total_operations if total_operations > 0 else 0
                }
    
    def get_daily_summary(self, date: str) -> Dict[str, Any]:
        """Получает сводку за день"""
        with self._lock:
            start_time = datetime.strptime(date, "%Y-%m-%d").timestamp()
            end_time = start_time + 24 * 3600
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Операции за день
                cursor.execute('''
                    SELECT operation_type, status, amount, price_usd, gas_used, gas_cost_usd
                    FROM operations 
                    WHERE timestamp >= ? AND timestamp < ?
                ''', (start_time, end_time))
                operations = cursor.fetchall()
                
                # Группировка по типам
                by_type = {}
                for op in operations:
                    op_type = op[0]
                    if op_type not in by_type:
                        by_type[op_type] = {'count': 0, 'success': 0, 'volume': 0, 'gas_used': 0}
                    
                    by_type[op_type]['count'] += 1
                    if op[1] == OperationStatus.SUCCESS.value:
                        by_type[op_type]['success'] += 1
                        by_type[op_type]['volume'] += op[2] * (op[3] or 0)
                    by_type[op_type]['gas_used'] += op[4] or 0
                
                return {
                    'date': date,
                    'total_operations': len(operations),
                    'by_type': by_type,
                    'total_volume_usd': sum(op[2] * (op[3] or 0) for op in operations if op[1] == OperationStatus.SUCCESS.value),
                    'total_gas_used': sum(op[4] or 0 for op in operations),
                    'total_gas_cost_usd': sum(op[5] or 0 for op in operations)
                }
    
    def export_data(self, start_time: float, end_time: float, format: str = "json") -> str:
        """Экспортирует данные"""
        operations = self.get_operations(start_time, end_time)
        
        if format == "json":
            data = {
                'export_timestamp': time.time(),
                'period': {
                    'start': start_time,
                    'end': end_time
                },
                'operations': [asdict(op) for op in operations]
            }
            return json.dumps(data, indent=2, default=str)
        
        elif format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Заголовки
            writer.writerow([
                'ID', 'Timestamp', 'Type', 'Status', 'Token Address', 'Token Symbol',
                'Amount', 'Price USD', 'Gas Used', 'Gas Price', 'Gas Cost USD',
                'TX Hash', 'Error Message', 'Wallet Address', 'Target Token', 'Slippage'
            ])
            
            # Данные
            for op in operations:
                writer.writerow([
                    op.id, op.timestamp, op.operation_type.value, op.status.value,
                    op.token_address, op.token_symbol, op.amount, op.price_usd,
                    op.gas_used, op.gas_price, op.gas_cost_usd, op.tx_hash,
                    op.error_message, op.wallet_address, op.target_token, op.slippage
                ])
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Неподдерживаемый формат: {format}")
    
    def _is_cache_valid(self, key: str) -> bool:
        """Проверяет валидность кеша"""
        return (key in self._cache and 
                time.time() - self._last_cache_update < self._cache_ttl)
    
    def _invalidate_cache(self):
        """Инвалидирует кеш"""
        self._cache.clear()
        self._last_cache_update = 0
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Очищает старые данные"""
        with self._lock:
            cutoff_time = time.time() - (days_to_keep * 24 * 3600)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Удаляем старые операции
                cursor.execute('DELETE FROM operations WHERE timestamp < ?', (cutoff_time,))
                operations_deleted = cursor.rowcount
                
                # Удаляем старые цены
                cursor.execute('DELETE FROM token_prices WHERE timestamp < ?', (cutoff_time,))
                prices_deleted = cursor.rowcount
                
                conn.commit()
                
                return {
                    'operations_deleted': operations_deleted,
                    'prices_deleted': prices_deleted
                }

# Глобальный экземпляр
analytics_manager = AnalyticsManager()
