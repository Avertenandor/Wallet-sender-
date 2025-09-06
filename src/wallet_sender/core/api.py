"""
BscScan/Etherscan API клиент с поддержкой V2 API и rate limiting
"""

import time
import logging
import random
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import aiohttp
import asyncio
import json
from urllib.parse import urlencode

from .limiter import ApiRateLimiter, get_rate_limiter

logger = logging.getLogger(__name__)


@dataclass
class ApiKeyPool:
    """Пул API ключей для ротации"""
    keys: List[str]
    current_index: int = 0
    failures: Dict[str, int] = None
    
    def __post_init__(self):
        if self.failures is None:
            self.failures = {key: 0 for key in self.keys}
    
    def get_next_key(self) -> Optional[str]:
        """Получение следующего рабочего ключа"""
        if not self.keys:
            return None
        
        # Ищем ключ с минимальным количеством ошибок
        working_keys = [(key, failures) for key, failures in self.failures.items() 
                       if failures < 3]  # Максимум 3 ошибки
        
        if not working_keys:
            # Сбрасываем счетчики если все ключи заблокированы
            self.failures = {key: 0 for key in self.keys}
            working_keys = [(key, 0) for key in self.keys]
        
        # Round-robin среди рабочих ключей
        working_keys.sort(key=lambda x: x[1])  # Сортируем по количеству ошибок
        key = working_keys[0][0]
        
        return key
    
    def mark_failure(self, key: str):
        """Отметка ошибки для ключа"""
        if key in self.failures:
            self.failures[key] += 1
            logger.warning(f"API key failure marked: {key[:8]}... (failures: {self.failures[key]})")
    
    def mark_success(self, key: str):
        """Отметка успеха для ключа"""
        if key in self.failures:
            self.failures[key] = max(0, self.failures[key] - 1)


class BscScanClient:
    """Клиент для работы с BscScan/Etherscan API V2"""
    
    # Базовые URL для разных режимов
    BASE_URL_V2 = "https://api.etherscan.io/v2/api"
    BASE_URL_V1_BSC = "https://api.bscscan.com/api"  # Fallback для старого API
    
    # Chain ID для BSC
    BSC_CHAIN_ID = 56
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None,
                 limiter: Optional[ApiRateLimiter] = None,
                 key_pool: Optional[ApiKeyPool] = None,
                 use_v2: bool = True):
        """
        Args:
            session: Aiohttp сессия для запросов
            limiter: Rate limiter
            key_pool: Пул API ключей
            use_v2: Использовать Etherscan V2 API
        """
        self.session = session
        self.limiter = limiter or get_rate_limiter()
        self.key_pool = key_pool
        self.use_v2 = use_v2
        
        # Счетчики для статистики
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        # Конфигурация retry
        self.max_retries = 3
        self.retry_delays = [0.5, 1.0, 2.0]
    
    async def get(self, module: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполнение GET запроса к API
        
        Args:
            module: Модуль API (account, contract, transaction, etc.)
            action: Действие (balance, tokentx, etc.)
            params: Параметры запроса
            
        Returns:
            Ответ API в виде словаря
        """
        # Получаем API ключ
        if not self.key_pool or not self.key_pool.keys:
            raise ValueError("No API keys configured")
        
        api_key = self.key_pool.get_next_key()
        if not api_key:
            raise ValueError("No working API keys available")
        
        # Формируем URL и параметры
        if self.use_v2:
            base_url = self.BASE_URL_V2
            query_params = {
                'chainid': self.BSC_CHAIN_ID,
                'module': module,
                'action': action,
                'apikey': api_key,
                **params
            }
        else:
            # Fallback на V1 BSC API
            base_url = self.BASE_URL_V1_BSC
            query_params = {
                'module': module,
                'action': action,
                'apikey': api_key,
                **params
            }
        
        url = f"{base_url}?{urlencode(query_params)}"
        
        # Выполняем запрос с retry и rate limiting
        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                token = await self._acquire_rate_limit(api_key)
                if not token:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delays[attempt])
                        continue
                    raise TimeoutError("Rate limit timeout")
                
                # Выполняем запрос
                self.total_requests += 1
                
                if self.session:
                    response = await self._make_request_async(url)
                else:
                    response = await self._make_request_sync(url)
                
                # Проверяем ответ
                if response.get('status') == '1' or response.get('message') == 'OK':
                    self.successful_requests += 1
                    self.key_pool.mark_success(api_key)
                    return response
                
                # Обработка ошибок API
                error_message = response.get('message', 'Unknown error')
                
                if 'rate limit' in error_message.lower():
                    logger.warning(f"Rate limit hit for key {api_key[:8]}...")
                    self.key_pool.mark_failure(api_key)
                    
                    # Пробуем другой ключ
                    api_key = self.key_pool.get_next_key()
                    if not api_key:
                        raise Exception("All API keys rate limited")
                    
                elif 'invalid api key' in error_message.lower():
                    logger.error(f"Invalid API key: {api_key[:8]}...")
                    self.key_pool.mark_failure(api_key)
                    
                    # Пробуем другой ключ
                    api_key = self.key_pool.get_next_key()
                    if not api_key:
                        raise Exception("No valid API keys")
                
                elif 'migrated to v2' in error_message.lower() and not self.use_v2:
                    logger.warning("API requires V2, switching...")
                    self.use_v2 = True
                    # Повторяем запрос с V2
                    continue
                
                else:
                    logger.warning(f"API error: {error_message}")
                
                # Retry с задержкой
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delays[attempt])
                else:
                    self.failed_requests += 1
                    raise Exception(f"API error after {self.max_retries} attempts: {error_message}")
                
            except Exception as e:
                self.failed_requests += 1
                
                if attempt < self.max_retries - 1:
                    logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                    await asyncio.sleep(self.retry_delays[attempt])
                else:
                    logger.error(f"Request failed after {self.max_retries} attempts: {e}")
                    raise
        
        raise Exception("Max retries exceeded")
    
    async def _acquire_rate_limit(self, api_key: str) -> Optional[Any]:
        """Получение разрешения от rate limiter"""
        try:
            # Используем синхронный acquire в async контексте
            loop = asyncio.get_event_loop()
            token = await loop.run_in_executor(
                None, 
                self.limiter.acquire,
                api_key,
                1.0,  # cost
                5.0   # timeout
            )
            return token
        except Exception as e:
            logger.warning(f"Rate limit acquire failed: {e}")
            return None
    
    async def _make_request_async(self, url: str) -> Dict[str, Any]:
        """Асинхронный запрос через aiohttp"""
        async with self.session.get(url, timeout=10) as response:
            text = await response.text()
            return json.loads(text)
    
    async def _make_request_sync(self, url: str) -> Dict[str, Any]:
        """Синхронный запрос (fallback)"""
        import requests
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(url, timeout=10).json()
        )
        return response
    
    # Специализированные методы для часто используемых запросов
    
    async def get_block_by_timestamp(self, timestamp: int, closest: str = 'before') -> int:
        """
        Получение номера блока по временной метке
        
        Args:
            timestamp: Unix timestamp
            closest: 'before' или 'after'
            
        Returns:
            Номер блока
        """
        response = await self.get(
            module='block',
            action='getblocknobytime',
            params={
                'timestamp': timestamp,
                'closest': closest
            }
        )
        
        return int(response.get('result', 0))
    
    async def get_latest_block(self) -> int:
        """Получение последнего номера блока"""
        response = await self.get(
            module='proxy',
            action='eth_blockNumber',
            params={}
        )
        
        # Результат в hex формате
        hex_value = response.get('result', '0x0')
        return int(hex_value, 16)
    
    async def get_token_transfers(self, address: str, 
                                 contract_address: Optional[str] = None,
                                 start_block: int = 0,
                                 end_block: int = 999999999,
                                 page: int = 1,
                                 offset: int = 100,
                                 sort: str = 'desc') -> List[Dict]:
        """
        Получение ERC-20 переводов для адреса
        
        Args:
            address: Адрес кошелька
            contract_address: Адрес токена (опционально)
            start_block: Начальный блок
            end_block: Конечный блок
            page: Страница результатов
            offset: Количество результатов
            sort: Сортировка ('asc' или 'desc')
            
        Returns:
            Список транзакций
        """
        params = {
            'address': address,
            'startblock': start_block,
            'endblock': end_block,
            'page': page,
            'offset': offset,
            'sort': sort
        }
        
        if contract_address:
            params['contractaddress'] = contract_address
        
        response = await self.get(
            module='account',
            action='tokentx',
            params=params
        )
        
        return response.get('result', [])
    
    async def get_event_logs(self, address: str,
                           from_block: int,
                           to_block: int,
                           topic0: Optional[str] = None,
                           topic1: Optional[str] = None) -> List[Dict]:
        """
        Получение event logs контракта
        
        Args:
            address: Адрес контракта
            from_block: Начальный блок
            to_block: Конечный блок
            topic0: Первый topic (обычно хеш события)
            topic1: Второй topic (опционально)
            
        Returns:
            Список логов
        """
        params = {
            'address': address,
            'fromBlock': from_block,
            'toBlock': to_block
        }
        
        if topic0:
            params['topic0'] = topic0
        if topic1:
            params['topic1'] = topic1
        
        response = await self.get(
            module='logs',
            action='getLogs',
            params=params
        )
        
        return response.get('result', [])
    
    async def get_token_holders(self, contract_address: str,
                              page: int = 1,
                              offset: int = 100) -> List[Dict]:
        """
        Получение списка держателей токена (V2 API)
        
        Args:
            contract_address: Адрес токена
            page: Страница результатов
            offset: Количество результатов
            
        Returns:
            Список держателей
        """
        if not self.use_v2:
            logger.warning("Token holders requires V2 API, switching...")
            self.use_v2 = True
        
        response = await self.get(
            module='token',
            action='tokenholderlist',
            params={
                'contractaddress': contract_address,
                'page': page,
                'offset': offset
            }
        )
        
        return response.get('result', [])
    
    async def get_token_info(self, contract_address: str) -> Dict:
        """
        Получение информации о токене (V2 API)
        
        Args:
            contract_address: Адрес токена
            
        Returns:
            Информация о токене
        """
        if not self.use_v2:
            logger.warning("Token info requires V2 API, switching...")
            self.use_v2 = True
        
        response = await self.get(
            module='token',
            action='tokeninfo',
            params={
                'contractaddress': contract_address
            }
        )
        
        return response.get('result', {})
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики клиента"""
        success_rate = (self.successful_requests / self.total_requests * 100 
                       if self.total_requests > 0 else 0)
        
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': f"{success_rate:.1f}%",
            'using_v2': self.use_v2,
            'key_pool_stats': {
                'total_keys': len(self.key_pool.keys) if self.key_pool else 0,
                'key_failures': dict(self.key_pool.failures) if self.key_pool else {}
            },
            'rate_limiter_stats': self.limiter.get_stats() if self.limiter else {}
        }


# Глобальный клиент
_global_client: Optional[BscScanClient] = None


async def get_bscscan_client(keys: Optional[List[str]] = None) -> BscScanClient:
    """Получение глобального клиента BscScan"""
    global _global_client
    
    if _global_client is None:
        if not keys:
            raise ValueError("API keys required for first initialization")
        
        session = aiohttp.ClientSession()
        limiter = get_rate_limiter()
        key_pool = ApiKeyPool(keys=keys)
        
        _global_client = BscScanClient(
            session=session,
            limiter=limiter,
            key_pool=key_pool,
            use_v2=True  # По умолчанию используем V2
        )
    
    return _global_client


async def close_bscscan_client():
    """Закрытие глобального клиента"""
    global _global_client
    
    if _global_client and _global_client.session:
        await _global_client.session.close()
    
    _global_client = None
