"""
Глобальный API Rate Limiter для управления лимитами запросов
"""

import time
import threading
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from contextlib import contextmanager
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Конфигурация rate limiter"""
    per_key_rps: float = 4.0  # Запросов в секунду на ключ
    global_rps: float = 8.0   # Глобальный лимит запросов в секунду
    burst_size: int = 10     # Размер burst bucket
    backoff_ms: List[int] = field(default_factory=lambda: [500, 1000, 2000])
    request_timeout_s: float = 10.0


class TokenBucket:
    """Token bucket для rate limiting"""
    
    def __init__(self, rate: float, capacity: int):
        """
        Args:
            rate: Скорость пополнения токенов в секунду
            capacity: Максимальная вместимость корзины
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = threading.Lock()
    
    def acquire(self, tokens: int = 1, timeout: float = None) -> bool:
        """
        Попытка получить токены
        
        Args:
            tokens: Количество токенов
            timeout: Максимальное время ожидания
            
        Returns:
            True если токены получены, False если таймаут
        """
        start_time = time.time()
        
        while True:
            with self.lock:
                now = time.time()
                # Пополняем токены
                elapsed = now - self.last_update
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_update = now
                
                # Проверяем доступность
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
            
            # Проверяем таймаут
            if timeout and (time.time() - start_time) >= timeout:
                return False
            
            # Ждем перед следующей попыткой
            wait_time = tokens / self.rate
            time.sleep(min(0.1, wait_time))
    
    def try_acquire(self, tokens: int = 1) -> bool:
        """Попытка получить токены без ожидания"""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


class RequestToken:
    """Токен запроса для отслеживания"""
    
    def __init__(self, key: Optional[str], cost: float, timestamp: float):
        self.key = key
        self.cost = cost
        self.timestamp = timestamp
        self.completed = False


class ApiRateLimiter:
    """Глобальный rate limiter для API запросов"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Args:
            config: Конфигурация rate limiter
        """
        self.config = config or RateLimitConfig()
        
        # Глобальный bucket
        self.global_bucket = TokenBucket(
            rate=self.config.global_rps,
            capacity=self.config.burst_size
        )
        
        # Per-key buckets
        self.key_buckets: Dict[str, TokenBucket] = {}
        self.key_locks = threading.Lock()
        
        # История запросов для аналитики
        self.request_history = deque(maxlen=1000)
        self.stats_lock = threading.Lock()
        
        # Счетчики
        self.total_requests = 0
        self.blocked_requests = 0
        self.timeout_requests = 0
    
    def get_key_bucket(self, key: str) -> TokenBucket:
        """Получение bucket для ключа"""
        with self.key_locks:
            if key not in self.key_buckets:
                self.key_buckets[key] = TokenBucket(
                    rate=self.config.per_key_rps,
                    capacity=self.config.burst_size
                )
            return self.key_buckets[key]
    
    def acquire(self, key: Optional[str] = None, cost: float = 1.0, 
                timeout_s: Optional[float] = None) -> Optional[RequestToken]:
        """
        Получение разрешения на запрос
        
        Args:
            key: Ключ API (опционально)
            cost: Стоимость запроса в токенах
            timeout_s: Таймаут ожидания
            
        Returns:
            RequestToken если разрешение получено, None при таймауте
        """
        timeout = timeout_s or self.config.request_timeout_s
        start_time = time.time()
        
        with self.stats_lock:
            self.total_requests += 1
        
        # Сначала проверяем глобальный лимит
        if not self.global_bucket.acquire(cost, timeout):
            with self.stats_lock:
                self.timeout_requests += 1
            logger.warning(f"Global rate limit timeout after {timeout}s")
            return None
        
        # Если есть ключ, проверяем per-key лимит
        if key:
            remaining_timeout = timeout - (time.time() - start_time)
            if remaining_timeout <= 0:
                with self.stats_lock:
                    self.timeout_requests += 1
                return None
            
            key_bucket = self.get_key_bucket(key)
            if not key_bucket.acquire(cost, remaining_timeout):
                # Возвращаем токены в глобальный bucket
                self.global_bucket.tokens += cost
                with self.stats_lock:
                    self.timeout_requests += 1
                logger.warning(f"Per-key rate limit timeout for {key}")
                return None
        
        # Создаем токен
        token = RequestToken(key, cost, time.time())
        
        # Добавляем в историю
        with self.stats_lock:
            self.request_history.append(token)
        
        logger.debug(f"Rate limit acquired: key={key}, cost={cost}")
        return token
    
    def release(self, token: RequestToken):
        """
        Освобождение токена (для возврата при ошибке)
        
        Args:
            token: Токен запроса
        """
        if token.completed:
            return
        
        # Возвращаем токены
        self.global_bucket.tokens += token.cost
        
        if token.key:
            key_bucket = self.get_key_bucket(token.key)
            key_bucket.tokens += token.cost
        
        token.completed = True
        logger.debug(f"Rate limit released: key={token.key}, cost={token.cost}")
    
    @contextmanager
    def rate_limit(self, key: Optional[str] = None, cost: float = 1.0,
                   timeout_s: Optional[float] = None):
        """
        Context manager для rate limiting
        
        Usage:
            with limiter.rate_limit(key="api_key_1"):
                # выполнить API запрос
        """
        token = self.acquire(key, cost, timeout_s)
        if not token:
            raise TimeoutError(f"Rate limit timeout after {timeout_s or self.config.request_timeout_s}s")
        
        try:
            yield token
        finally:
            # Токен автоматически считается использованным
            token.completed = True
    
    def try_acquire_nowait(self, key: Optional[str] = None, cost: float = 1.0) -> bool:
        """
        Попытка получить разрешение без ожидания
        
        Returns:
            True если разрешение получено сразу
        """
        # Проверяем глобальный лимит
        if not self.global_bucket.try_acquire(cost):
            with self.stats_lock:
                self.blocked_requests += 1
            return False
        
        # Проверяем per-key лимит
        if key:
            key_bucket = self.get_key_bucket(key)
            if not key_bucket.try_acquire(cost):
                # Возвращаем токены в глобальный bucket
                self.global_bucket.tokens += cost
                with self.stats_lock:
                    self.blocked_requests += 1
                return False
        
        # Добавляем в историю
        token = RequestToken(key, cost, time.time())
        token.completed = True
        with self.stats_lock:
            self.request_history.append(token)
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики rate limiter"""
        with self.stats_lock:
            recent_requests = [r for r in self.request_history 
                             if time.time() - r.timestamp < 60]
            
            per_key_stats = {}
            for req in recent_requests:
                if req.key:
                    if req.key not in per_key_stats:
                        per_key_stats[req.key] = {'count': 0, 'cost': 0}
                    per_key_stats[req.key]['count'] += 1
                    per_key_stats[req.key]['cost'] += req.cost
            
            return {
                'total_requests': self.total_requests,
                'blocked_requests': self.blocked_requests,
                'timeout_requests': self.timeout_requests,
                'recent_rps': len(recent_requests) / 60.0 if recent_requests else 0,
                'global_tokens': self.global_bucket.tokens,
                'per_key_stats': per_key_stats,
                'config': {
                    'per_key_rps': self.config.per_key_rps,
                    'global_rps': self.config.global_rps,
                    'burst_size': self.config.burst_size
                }
            }
    
    def update_config(self, config: RateLimitConfig):
        """Обновление конфигурации"""
        self.config = config
        
        # Обновляем глобальный bucket
        self.global_bucket.rate = config.global_rps
        self.global_bucket.capacity = config.burst_size
        
        # Обновляем существующие per-key buckets
        with self.key_locks:
            for bucket in self.key_buckets.values():
                bucket.rate = config.per_key_rps
                bucket.capacity = config.burst_size
        
        logger.info(f"Rate limiter config updated: global={config.global_rps}rps, per_key={config.per_key_rps}rps")
    
    def reset_key(self, key: str):
        """Сброс лимитов для конкретного ключа"""
        with self.key_locks:
            if key in self.key_buckets:
                self.key_buckets[key].tokens = self.key_buckets[key].capacity
                logger.info(f"Rate limits reset for key: {key}")
    
    def reset_all(self):
        """Сброс всех лимитов"""
        self.global_bucket.tokens = self.global_bucket.capacity
        
        with self.key_locks:
            for bucket in self.key_buckets.values():
                bucket.tokens = bucket.capacity
        
        with self.stats_lock:
            self.blocked_requests = 0
            self.timeout_requests = 0
        
        logger.info("All rate limits reset")


# Глобальный экземпляр
_global_limiter: Optional[ApiRateLimiter] = None


def get_rate_limiter(config: Optional[RateLimitConfig] = None) -> ApiRateLimiter:
    """Получение глобального rate limiter"""
    global _global_limiter
    
    if _global_limiter is None:
        _global_limiter = ApiRateLimiter(config)
    elif config:
        _global_limiter.update_config(config)
    
    return _global_limiter


def reset_rate_limiter():
    """Сброс глобального rate limiter"""
    global _global_limiter
    _global_limiter = None
