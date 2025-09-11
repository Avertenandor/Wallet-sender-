"""
Модуль аналитики для WalletSender v2.1.1
SQL-запросы и агрегация данных для вкладки аналитики
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import json
import logging

from .models import AnalyticsData

logger = logging.getLogger(__name__)


class Analytics:
    """Класс для аналитических запросов к БД"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def _get_connection(self) -> sqlite3.Connection:
        """Получить соединение с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def get_summary(self, 
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> AnalyticsData:
        """
        Получить общую статистику за период
        
        Args:
            start_date: Начало периода (None = 30 дней назад)
            end_date: Конец периода (None = сейчас)
            
        Returns:
            AnalyticsData с агрегированными данными
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
            
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Общая статистика транзакций
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'mined' THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN status IN ('failed', 'canceled') THEN 1 ELSE 0 END) as failed,
                    SUM(amount_wei) as total_volume,
                    SUM(gas_price_wei * gas_used) as total_gas,
                    COUNT(DISTINCT from_addr) as unique_senders,
                    COUNT(DISTINCT to_addr) as unique_receivers,
                    AVG(gas_price_wei) as avg_gas_price
                FROM tx_history
                WHERE ts BETWEEN ? AND ?
            """, (start_date, end_date))
            
            row = cursor.fetchone()
            
            analytics = AnalyticsData(
                period_start=start_date,
                period_end=end_date,
                total_tx=row['total'] or 0,
                success_tx=row['success'] or 0,
                failed_tx=row['failed'] or 0,
                total_volume_wei=row['total_volume'] or 0,
                total_gas_wei=row['total_gas'] or 0,
                unique_senders=row['unique_senders'] or 0,
                unique_receivers=row['unique_receivers'] or 0,
                avg_gas_price=row['avg_gas_price'] or 0.0
            )
            
            # Статистика по токенам
            cursor.execute("""
                SELECT 
                    COALESCE(token, 'BNB') as token,
                    COUNT(*) as count
                FROM tx_history
                WHERE ts BETWEEN ? AND ?
                GROUP BY token
            """, (start_date, end_date))
            
            for row in cursor.fetchall():
                analytics.tokens_used[row['token']] = row['count']
                
            # Расчет перцентилей задержки (если есть данные о задержках)
            # Для простоты используем время между created и mined статусом
            cursor.execute("""
                SELECT 
                    (julianday(ts) - julianday(LAG(ts) OVER (PARTITION BY tx_hash ORDER BY ts))) * 86400000 as latency_ms
                FROM tx_history
                WHERE ts BETWEEN ? AND ?
                    AND status = 'mined'
                    AND tx_hash IS NOT NULL
            """, (start_date, end_date))
            
            latencies = [row['latency_ms'] for row in cursor.fetchall() if row['latency_ms']]
            if latencies:
                latencies.sort()
                n = len(latencies)
                analytics.p50_latency_ms = latencies[n // 2] if n > 0 else 0
                analytics.p95_latency_ms = latencies[int(n * 0.95)] if n > 0 else 0
                
            return analytics
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return AnalyticsData(start_date, end_date)
        finally:
            conn.close()
            
    def get_daily_stats(self, days: int = 7) -> List[Dict]:
        """
        Получить статистику по дням
        
        Args:
            days: Количество дней для анализа
            
        Returns:
            Список словарей с данными по дням
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    DATE(ts) as date,
                    COUNT(*) as total_tx,
                    SUM(CASE WHEN status = 'mined' THEN 1 ELSE 0 END) as success_tx,
                    SUM(amount_wei) as volume_wei,
                    SUM(gas_price_wei * gas_used) as gas_wei,
                    COUNT(DISTINCT from_addr) as unique_senders
                FROM tx_history
                WHERE ts >= DATE('now', '-' || ? || ' days')
                GROUP BY DATE(ts)
                ORDER BY date DESC
            """, (days,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'date': row['date'],
                    'total_tx': row['total_tx'],
                    'success_tx': row['success_tx'],
                    'volume_wei': row['volume_wei'] or 0,
                    'gas_wei': row['gas_wei'] or 0,
                    'unique_senders': row['unique_senders'],
                    'success_rate': (row['success_tx'] / row['total_tx'] * 100) if row['total_tx'] > 0 else 0
                })
                
            return results
            
        except Exception as e:
            logger.error(f"Ошибка получения дневной статистики: {e}")
            return []
        finally:
            conn.close()
            
    def get_top_receivers(self, limit: int = 10, days: int = 30) -> List[Dict]:
        """
        Получить топ получателей по количеству транзакций
        
        Args:
            limit: Максимальное количество результатов
            days: Период анализа в днях
            
        Returns:
            Список словарей с данными по получателям
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    to_addr,
                    COUNT(*) as tx_count,
                    SUM(amount_wei) as total_received,
                    COUNT(DISTINCT from_addr) as unique_senders,
                    MIN(ts) as first_tx,
                    MAX(ts) as last_tx
                FROM tx_history
                WHERE ts >= DATE('now', '-' || ? || ' days')
                    AND status = 'mined'
                GROUP BY to_addr
                ORDER BY tx_count DESC
                LIMIT ?
            """, (days, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'address': row['to_addr'],
                    'tx_count': row['tx_count'],
                    'total_received': row['total_received'],
                    'unique_senders': row['unique_senders'],
                    'first_tx': row['first_tx'],
                    'last_tx': row['last_tx']
                })
                
            return results
            
        except Exception as e:
            logger.error(f"Ошибка получения топ получателей: {e}")
            return []
        finally:
            conn.close()
            
    def get_job_stats(self) -> List[Dict]:
        """
        Получить статистику по заданиям
        
        Returns:
            Список словарей с данными по заданиям
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    j.job_id,
                    j.title,
                    j.state,
                    j.created_ts,
                    j.total_items,
                    j.done,
                    j.failed,
                    COUNT(t.id) as actual_tx,
                    SUM(CASE WHEN t.status = 'mined' THEN 1 ELSE 0 END) as success_tx,
                    SUM(t.amount_wei) as total_volume,
                    SUM(t.gas_price_wei * t.gas_used) as total_gas
                FROM jobs j
                LEFT JOIN tx_history t ON j.job_id = t.job_id
                GROUP BY j.job_id
                ORDER BY j.created_ts DESC
            """)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'job_id': row['job_id'],
                    'title': row['title'],
                    'state': row['state'],
                    'created_ts': row['created_ts'],
                    'total_items': row['total_items'],
                    'done': row['done'],
                    'failed': row['failed'],
                    'actual_tx': row['actual_tx'] or 0,
                    'success_tx': row['success_tx'] or 0,
                    'total_volume': row['total_volume'] or 0,
                    'total_gas': row['total_gas'] or 0,
                    'progress': ((row['done'] + row['failed']) / row['total_items'] * 100) if row['total_items'] > 0 else 0
                })
                
            return results
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики заданий: {e}")
            return []
        finally:
            conn.close()
            
    def get_token_distribution(self, days: int = 30) -> Dict[str, Dict]:
        """
        Получить распределение по токенам
        
        Args:
            days: Период анализа в днях
            
        Returns:
            Словарь с данными по каждому токену
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COALESCE(token, 'BNB') as token,
                    COUNT(*) as tx_count,
                    SUM(CASE WHEN status = 'mined' THEN 1 ELSE 0 END) as success_count,
                    SUM(amount_wei) as total_volume,
                    AVG(amount_wei) as avg_amount,
                    MIN(amount_wei) as min_amount,
                    MAX(amount_wei) as max_amount
                FROM tx_history
                WHERE ts >= DATE('now', '-' || ? || ' days')
                GROUP BY token
                ORDER BY tx_count DESC
            """, (days,))
            
            results = {}
            for row in cursor.fetchall():
                token = row['token']
                results[token] = {
                    'tx_count': row['tx_count'],
                    'success_count': row['success_count'],
                    'total_volume': row['total_volume'] or 0,
                    'avg_amount': row['avg_amount'] or 0,
                    'min_amount': row['min_amount'] or 0,
                    'max_amount': row['max_amount'] or 0,
                    'success_rate': (row['success_count'] / row['tx_count'] * 100) if row['tx_count'] > 0 else 0
                }
                
            return results
            
        except Exception as e:
            logger.error(f"Ошибка получения распределения по токенам: {e}")
            return {}
        finally:
            conn.close()
            
    def get_gas_analytics(self, hours: int = 24) -> Dict:
        """
        Получить аналитику по газу
        
        Args:
            hours: Период анализа в часах
            
        Returns:
            Словарь с данными по газу
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    AVG(gas_price_wei) as avg_gas_price,
                    MIN(gas_price_wei) as min_gas_price,
                    MAX(gas_price_wei) as max_gas_price,
                    AVG(gas_used) as avg_gas_used,
                    MIN(gas_used) as min_gas_used,
                    MAX(gas_used) as max_gas_used,
                    AVG(gas_price_wei * gas_used) as avg_gas_cost,
                    SUM(gas_price_wei * gas_used) as total_gas_cost
                FROM tx_history
                WHERE ts >= datetime('now', '-' || ? || ' hours')
                    AND gas_price_wei IS NOT NULL
                    AND gas_used IS NOT NULL
            """, (hours,))
            
            row = cursor.fetchone()
            
            # Расчет перцентилей для gas_price
            cursor.execute("""
                SELECT gas_price_wei
                FROM tx_history
                WHERE ts >= datetime('now', '-' || ? || ' hours')
                    AND gas_price_wei IS NOT NULL
                ORDER BY gas_price_wei
            """, (hours,))
            
            prices = [row['gas_price_wei'] for row in cursor.fetchall()]
            
            result = {
                'avg_gas_price': row['avg_gas_price'] or 0,
                'min_gas_price': row['min_gas_price'] or 0,
                'max_gas_price': row['max_gas_price'] or 0,
                'avg_gas_used': row['avg_gas_used'] or 0,
                'min_gas_used': row['min_gas_used'] or 0,
                'max_gas_used': row['max_gas_used'] or 0,
                'avg_gas_cost': row['avg_gas_cost'] or 0,
                'total_gas_cost': row['total_gas_cost'] or 0
            }
            
            if prices:
                n = len(prices)
                result['p25_gas_price'] = prices[n // 4] if n > 3 else prices[0]
                result['p50_gas_price'] = prices[n // 2] if n > 1 else prices[0]
                result['p75_gas_price'] = prices[3 * n // 4] if n > 3 else prices[-1]
                result['p95_gas_price'] = prices[int(n * 0.95)] if n > 19 else prices[-1]
            else:
                result['p25_gas_price'] = 0
                result['p50_gas_price'] = 0
                result['p75_gas_price'] = 0
                result['p95_gas_price'] = 0
                
            return result
            
        except Exception as e:
            logger.error(f"Ошибка получения аналитики газа: {e}")
            return {}
        finally:
            conn.close()
