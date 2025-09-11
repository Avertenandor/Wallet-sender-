"""
Менеджер газа для динамического определения оптимальной цены
"""

import time
import requests
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

class GasPriority(Enum):
    """Приоритеты газа"""
    SLOW = "slow"
    STANDARD = "standard"
    FAST = "fast"
    INSTANT = "instant"

@dataclass
class GasEstimate:
    """Оценка газа"""
    slow: int
    standard: int
    fast: int
    instant: int
    timestamp: float

class GasManager:
    """Менеджер для работы с газом"""
    
    def __init__(self, web3_instance):
        self.web3 = web3_instance
        self._gas_cache = {}
        self._last_update = 0
        self._update_interval = 15  # Обновляем каждые 15 секунд
        
        # Fallback цены газа (в gwei) - понижены для экономии
        self.fallback_prices = {
            GasPriority.SLOW: 1,      # Очень низкий газ
            GasPriority.STANDARD: 3,  # Стандартный газ  
            GasPriority.FAST: 5,      # Быстрый газ
            GasPriority.INSTANT: 8    # Мгновенный газ
        }
        
        # Множители для разных типов операций
        self.operation_multipliers = {
            'transfer': 1.0,
            'approve': 1.0,
            'swap': 1.2,
            'complex_swap': 1.5
        }
    
    def get_optimal_gas_price(self, priority: GasPriority = GasPriority.STANDARD, 
                            operation_type: str = 'transfer') -> int:
        """Получает оптимальную цену газа"""
        try:
            # Получаем актуальные данные о газе
            gas_data = self._get_gas_data()
            
            # Выбираем цену по приоритету
            if priority == GasPriority.SLOW:
                base_price = gas_data.slow
            elif priority == GasPriority.STANDARD:
                base_price = gas_data.standard
            elif priority == GasPriority.FAST:
                base_price = gas_data.fast
            else:  # INSTANT
                base_price = gas_data.instant
            
            # Применяем множитель для типа операции
            multiplier = self.operation_multipliers.get(operation_type, 1.0)
            adjusted_price = int(base_price * multiplier)
            
            # Ограничиваем максимальную цену газа (защита от чрезмерно высоких цен)
            max_gas_price_gwei = 10  # Максимум 10 gwei
            adjusted_price = min(adjusted_price, max_gas_price_gwei)
            
            # Конвертируем в wei
            gas_price_wei = self.web3.to_wei(adjusted_price, 'gwei')
            
            return gas_price_wei
            
        except Exception:
            # Fallback на статичные цены
            fallback_price = self.fallback_prices[priority]
            multiplier = self.operation_multipliers.get(operation_type, 1.0)
            adjusted_price = int(fallback_price * multiplier)
            
            # Ограничиваем максимальную цену газа (защита от чрезмерно высоких цен)
            max_gas_price_gwei = 10  # Максимум 10 gwei
            adjusted_price = min(adjusted_price, max_gas_price_gwei)
            
            return self.web3.to_wei(adjusted_price, 'gwei')
    
    def _get_gas_data(self) -> GasEstimate:
        """Получает данные о газе из различных источников"""
        current_time = time.time()
        
        # Проверяем кеш
        if (current_time - self._last_update < self._update_interval and 
            'gas_estimate' in self._gas_cache):
            return self._gas_cache['gas_estimate']
        
        # Пробуем получить данные из разных источников
        gas_estimate = None
        
        # 1. Пробуем BSCScan API
        gas_estimate = self._get_gas_from_bscscan()
        
        # 2. Если не получилось, пробуем Web3
        if gas_estimate is None:
            gas_estimate = self._get_gas_from_web3()
        
        # 3. Если и это не сработало, используем fallback
        if gas_estimate is None:
            gas_estimate = self._get_fallback_gas()
        
        # Кешируем результат
        self._gas_cache['gas_estimate'] = gas_estimate
        self._last_update = current_time
        
        return gas_estimate
    
    def _get_gas_from_bscscan(self) -> Optional[GasEstimate]:
        """Получает данные о газе из BSCScan API"""
        try:
            # BSCScan не предоставляет API для газа, но можем попробовать другие источники
            return None
        except Exception:
            return None
    
    def _get_gas_from_web3(self) -> Optional[GasEstimate]:
        """Получает данные о газе из Web3"""
        try:
            # Получаем текущую цену газа
            current_gas_price = self.web3.eth.gas_price
            current_gas_gwei = self.web3.from_wei(current_gas_price, 'gwei')
            
            # Создаем оценки на основе текущей цены
            gas_estimate = GasEstimate(
                slow=max(1, int(current_gas_gwei * 0.8)),
                standard=int(current_gas_gwei),
                fast=int(current_gas_gwei * 1.2),
                instant=int(current_gas_gwei * 1.5),
                timestamp=time.time()
            )
            
            return gas_estimate
            
        except Exception:
            return None
    
    def _get_fallback_gas(self) -> GasEstimate:
        """Возвращает fallback данные о газе"""
        return GasEstimate(
            slow=self.fallback_prices[GasPriority.SLOW],
            standard=self.fallback_prices[GasPriority.STANDARD],
            fast=self.fallback_prices[GasPriority.FAST],
            instant=self.fallback_prices[GasPriority.INSTANT],
            timestamp=time.time()
        )
    
    def estimate_gas_for_transaction(self, transaction: Dict[str, Any]) -> int:
        """Оценивает необходимое количество газа для транзакции"""
        try:
            # Пробуем оценить газ
            estimated_gas = self.web3.eth.estimate_gas(transaction)
            
            # Добавляем 20% запас
            gas_with_buffer = int(estimated_gas * 1.2)
            
            return gas_with_buffer
            
        except Exception:
            # Fallback значения в зависимости от типа операции
            if 'value' in transaction and transaction['value'] > 0:
                return 21000  # Простой перевод ETH
            else:
                return 100000  # Контрактная операция
    
    def get_gas_info(self) -> Dict[str, Any]:
        """Возвращает информацию о текущем состоянии газа"""
        try:
            gas_data = self._get_gas_data()
            current_gas = self.web3.eth.gas_price
            current_gas_gwei = self.web3.from_wei(current_gas, 'gwei')
            
            return {
                'current_gas_gwei': current_gas_gwei,
                'estimated_slow': gas_data.slow,
                'estimated_standard': gas_data.standard,
                'estimated_fast': gas_data.fast,
                'estimated_instant': gas_data.instant,
                'last_update': gas_data.timestamp,
                'cache_age': time.time() - gas_data.timestamp
            }
        except Exception:
            return {
                'error': 'Не удалось получить информацию о газе',
                'fallback_prices': {k.value: v for k, v in self.fallback_prices.items()}
            }
    
    def adjust_gas_for_retry(self, original_gas_price: int, retry_count: int) -> int:
        """Увеличивает цену газа для повторной попытки"""
        # Увеличиваем на 10% за каждую попытку
        multiplier = 1.0 + (retry_count * 0.1)
        return int(original_gas_price * multiplier)
    
    def get_recommended_gas_limit(self, operation_type: str) -> int:
        """Возвращает рекомендуемый лимит газа для операции"""
        gas_limits = {
            'transfer': 21000,
            'approve': 100000,
            'swap': 300000,
            'complex_swap': 500000,
            'mint': 200000,
            'burn': 100000
        }
        
        return gas_limits.get(operation_type, 200000)
