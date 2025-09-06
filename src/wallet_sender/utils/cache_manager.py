"""
Менеджер кеширования для оптимизации запросов к блокчейну
"""

import time
import threading
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class CacheEntry:
    """Запись в кеше"""
    value: Any
    timestamp: float
    ttl: float  # Time to live в секундах

class CacheManager:
    """Менеджер кеширования с TTL и автоматической очисткой"""
    
    def __init__(self, default_ttl: float = 10.0):
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
        self._cleanup_thread = None
        self._running = False
        
    def start_cleanup(self):
        """Запускает фоновую очистку кеша"""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._running = True
            self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self._cleanup_thread.start()
    
    def stop_cleanup(self):
        """Останавливает фоновую очистку кеша"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=1)
    
    def _cleanup_loop(self):
        """Цикл очистки устаревших записей"""
        while self._running:
            try:
                self._cleanup_expired()
                time.sleep(5)  # Очистка каждые 5 секунд
            except Exception:
                pass
    
    def _cleanup_expired(self):
        """Удаляет устаревшие записи из кеша"""
        with self._lock:
            current_time = time.time()
            expired_keys = []
            
            for key, entry in self._cache.items():
                if current_time - entry.timestamp > entry.ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
    
    def get(self, key: str) -> Optional[Any]:
        """Получает значение из кеша"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() - entry.timestamp <= entry.ttl:
                    return entry.value
                else:
                    # Запись устарела, удаляем
                    del self._cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Сохраняет значение в кеш"""
        with self._lock:
            if ttl is None:
                ttl = self._default_ttl
            
            self._cache[key] = CacheEntry(
                value=value,
                timestamp=time.time(),
                ttl=ttl
            )
    
    def invalidate(self, key: str) -> None:
        """Удаляет запись из кеша"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self) -> None:
        """Очищает весь кеш"""
        with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кеша"""
        with self._lock:
            current_time = time.time()
            total_entries = len(self._cache)
            expired_entries = sum(
                1 for entry in self._cache.values()
                if current_time - entry.timestamp > entry.ttl
            )
            
            return {
                'total_entries': total_entries,
                'expired_entries': expired_entries,
                'active_entries': total_entries - expired_entries,
                'memory_usage': sum(
                    len(str(entry.value)) for entry in self._cache.values()
                )
            }

class TokenCacheManager:
    """Специализированный менеджер кеша для токенов"""
    
    def __init__(self):
        self.cache = CacheManager(default_ttl=30.0)  # 30 секунд для токенов
        self.cache.start_cleanup()
        
        # Разные TTL для разных типов данных
        self.balance_ttl = 10.0      # Балансы - 10 секунд
        self.token_info_ttl = 300.0  # Информация о токенах - 5 минут
        self.gas_price_ttl = 15.0    # Цены газа - 15 секунд
        
    def get_token_balance(self, token_address: str, wallet_address: str) -> Optional[float]:
        """Получает баланс токена из кеша"""
        key = f"balance:{token_address}:{wallet_address}"
        return self.cache.get(key)
    
    def set_token_balance(self, token_address: str, wallet_address: str, balance: float) -> None:
        """Сохраняет баланс токена в кеш"""
        key = f"balance:{token_address}:{wallet_address}"
        self.cache.set(key, balance, self.balance_ttl)
    
    def get_token_info(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о токене из кеша"""
        key = f"token_info:{token_address}"
        return self.cache.get(key)
    
    def set_token_info(self, token_address: str, info: Dict[str, Any]) -> None:
        """Сохраняет информацию о токене в кеш"""
        key = f"token_info:{token_address}"
        self.cache.set(key, info, self.token_info_ttl)
    
    def get_gas_price(self, network: str = "bsc") -> Optional[int]:
        """Получает цену газа из кеша"""
        key = f"gas_price:{network}"
        return self.cache.get(key)
    
    def set_gas_price(self, gas_price: int, network: str = "bsc") -> None:
        """Сохраняет цену газа в кеш"""
        key = f"gas_price:{network}"
        self.cache.set(key, gas_price, self.gas_price_ttl)
    
    def invalidate_token_balance(self, token_address: str, wallet_address: str) -> None:
        """Инвалидирует кеш баланса токена"""
        key = f"balance:{token_address}:{wallet_address}"
        self.cache.invalidate(key)
    
    def invalidate_all_balances(self, wallet_address: str) -> None:
        """Инвалидирует все балансы для кошелька"""
        with self.cache._lock:
            keys_to_remove = []
            for key in self.cache._cache.keys():
                if key.startswith("balance:") and key.endswith(f":{wallet_address}"):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self.cache.invalidate(key)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кеша"""
        return self.cache.get_stats()
    
    def cleanup(self):
        """Очищает кеш"""
        self.cache.stop_cleanup()
        self.cache.clear()

# Глобальный экземпляр менеджера кеша
token_cache = TokenCacheManager()
