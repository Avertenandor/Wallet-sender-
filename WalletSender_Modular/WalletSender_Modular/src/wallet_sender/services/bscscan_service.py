"""
BSCScan/Etherscan API Service - единый сервис для работы с API через rate limiter и BscScanClient
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from ..core.api import BscScanClient, ApiKeyPool, get_bscscan_client
from ..core.limiter import ApiRateLimiter, RateLimitConfig, get_rate_limiter
from ..config import get_config

logger = logging.getLogger(__name__)


class BscScanService:
    """Единый сервис для работы с BSCScan/Etherscan API"""
    
    def __init__(self):
        """Инициализация сервиса"""
        config = get_config()
        
        # Получаем ключи из конфига - пробуем разные варианты
        # 1. Новый формат в секции api
        self.api_keys = config.get('api.bscscan_api_keys', [])
        
        # 2. Etherscan keys (текущий стандарт для V2 API)
        if not self.api_keys:
            self.api_keys = config.get('etherscan_api_keys', [])
        
        # 3. Legacy формат
        if not self.api_keys:
            self.api_keys = config.get('bscscan_api_keys', [])
        
        if not self.api_keys:
            logger.warning("No API keys found in config. Please add etherscan_api_keys or api.bscscan_api_keys.")
        
        # Настраиваем rate limiter
        rate_config = config.get('api', {}).get('rate_limit', {})
        self.rate_limit_config = RateLimitConfig(
            per_key_rps=rate_config.get('per_key_rps', 4.0),
            global_rps=rate_config.get('global_rps', 8.0),
            burst_size=rate_config.get('burst_size', 10),
            backoff_ms=rate_config.get('backoff_ms', [500, 1000, 2000]),
            request_timeout_s=rate_config.get('request_timeout_s', 10.0)
        )
        
        # Инициализируем компоненты
        self.limiter = get_rate_limiter(self.rate_limit_config)
        self.key_pool = ApiKeyPool(keys=self.api_keys) if self.api_keys else None
        self.client: Optional[BscScanClient] = None
        self._client_lock = asyncio.Lock()
    
    async def _get_client(self) -> BscScanClient:
        """Получение или создание клиента"""
        async with self._client_lock:
            if self.client is None:
                # Создаем сессию
                import aiohttp
                session = aiohttp.ClientSession()
                
                # Создаем клиент
                self.client = BscScanClient(
                    session=session,
                    limiter=self.limiter,
                    key_pool=self.key_pool,
                    use_v2=True
                )
            
            return self.client
    
    async def get_transactions(self, 
                              address: str, 
                              token_address: Optional[str] = None,
                              start_block: int = 0,
                              end_block: int = 999999999,
                              page: int = 1,
                              offset: int = 100,
                              sort: str = 'desc') -> List[Dict[str, Any]]:
        """
        Получение транзакций для адреса
        
        Args:
            address: Адрес кошелька
            token_address: Адрес токена (None для обычных транзакций)
            start_block: Начальный блок
            end_block: Конечный блок
            page: Страница результатов
            offset: Количество результатов
            sort: Сортировка
            
        Returns:
            Список транзакций
        """
        client = await self._get_client()
        
        try:
            if token_address:
                # Токеновые транзакции
                return await client.get_token_transfers(
                    address=address,
                    contract_address=token_address,
                    start_block=start_block,
                    end_block=end_block,
                    page=page,
                    offset=offset,
                    sort=sort
                )
            else:
                # Обычные транзакции
                response = await client.get(
                    module='account',
                    action='txlist',
                    params={
                        'address': address,
                        'startblock': start_block,
                        'endblock': end_block,
                        'page': page,
                        'offset': offset,
                        'sort': sort
                    }
                )
                return response.get('result', [])
                
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []
    
    async def get_token_balance(self, 
                              address: str, 
                              contract_address: str) -> int:
        """
        Получение баланса токена
        
        Args:
            address: Адрес кошелька
            contract_address: Адрес контракта токена
            
        Returns:
            Баланс в wei
        """
        client = await self._get_client()
        
        try:
            response = await client.get(
                module='account',
                action='tokenbalance',
                params={
                    'contractaddress': contract_address,
                    'address': address,
                    'tag': 'latest'
                }
            )
            return int(response.get('result', '0'))
            
        except Exception as e:
            logger.error(f"Error getting token balance: {e}")
            return 0
    
    async def get_bnb_balance(self, address: str) -> int:
        """
        Получение баланса BNB
        
        Args:
            address: Адрес кошелька
            
        Returns:
            Баланс в wei
        """
        client = await self._get_client()
        
        try:
            response = await client.get(
                module='account',
                action='balance',
                params={
                    'address': address,
                    'tag': 'latest'
                }
            )
            return int(response.get('result', '0'))
            
        except Exception as e:
            logger.error(f"Error getting BNB balance: {e}")
            return 0
    
    async def search_txs(self,
                        address: str,
                        token_filter: Optional[str] = None,
                        amount_min: Optional[float] = None,
                        amount_max: Optional[float] = None,
                        date_from: Optional[datetime] = None,
                        date_to: Optional[datetime] = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """
        Поиск транзакций с фильтрацией
        
        Args:
            address: Адрес для поиска
            token_filter: Фильтр по токену
            amount_min: Минимальная сумма
            amount_max: Максимальная сумма
            date_from: Начальная дата
            date_to: Конечная дата
            limit: Максимальное количество результатов
            
        Returns:
            Список отфильтрованных транзакций
        """
        # Преобразуем даты в блоки если указаны
        start_block = 0
        end_block = 999999999
        
        client = await self._get_client()
        
        if date_from:
            timestamp = int(date_from.timestamp())
            start_block = await client.get_block_by_timestamp(timestamp, 'after')
        
        if date_to:
            timestamp = int(date_to.timestamp())
            end_block = await client.get_block_by_timestamp(timestamp, 'before')
        
        # Получаем транзакции
        if token_filter and token_filter != 'ALL':
            transactions = await client.get_token_transfers(
                address=address,
                contract_address=token_filter,
                start_block=start_block,
                end_block=end_block,
                offset=min(limit, 10000)
            )
        else:
            # Получаем обе категории транзакций
            normal_txs_task = client.get(
                module='account',
                action='txlist',
                params={
                    'address': address,
                    'startblock': start_block,
                    'endblock': end_block,
                    'offset': min(limit, 10000),
                    'sort': 'desc'
                }
            )
            
            token_txs_task = client.get_token_transfers(
                address=address,
                start_block=start_block,
                end_block=end_block,
                offset=min(limit, 10000)
            )
            
            # Выполняем параллельно
            normal_response, token_txs = await asyncio.gather(
                normal_txs_task, token_txs_task
            )
            
            normal_txs = normal_response.get('result', [])
            
            # Объединяем и сортируем
            transactions = normal_txs + token_txs
            transactions.sort(key=lambda x: int(x.get('timeStamp', 0)), reverse=True)
        
        # Применяем фильтры по сумме
        if amount_min is not None or amount_max is not None:
            filtered = []
            for tx in transactions:
                # Получаем decimals (по умолчанию 18)
                decimals = int(tx.get('tokenDecimal', 18))
                value = float(tx.get('value', '0')) / (10 ** decimals)
                
                if amount_min and value < amount_min:
                    continue
                if amount_max and value > amount_max:
                    continue
                
                filtered.append(tx)
            
            transactions = filtered
        
        # Ограничиваем количество результатов
        return transactions[:limit]
    
    async def get_token_holders(self, 
                              contract_address: str,
                              limit: int = 100) -> List[Dict[str, Any]]:
        """
        Получение списка держателей токена
        
        Args:
            contract_address: Адрес контракта токена
            limit: Максимальное количество результатов
            
        Returns:
            Список держателей
        """
        client = await self._get_client()
        
        try:
            return await client.get_token_holders(
                contract_address=contract_address,
                offset=limit
            )
        except Exception as e:
            logger.error(f"Error getting token holders: {e}")
            return []
    
    async def get_token_info(self, contract_address: str) -> Dict[str, Any]:
        """
        Получение информации о токене
        
        Args:
            contract_address: Адрес контракта токена
            
        Returns:
            Информация о токене
        """
        client = await self._get_client()
        
        try:
            return await client.get_token_info(contract_address)
        except Exception as e:
            logger.error(f"Error getting token info: {e}")
            return {}
    
    async def get_event_logs(self,
                           address: str,
                           from_block: int,
                           to_block: int,
                           topic0: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получение event logs
        
        Args:
            address: Адрес контракта
            from_block: Начальный блок
            to_block: Конечный блок
            topic0: Topic фильтр
            
        Returns:
            Список логов
        """
        client = await self._get_client()
        
        try:
            return await client.get_event_logs(
                address=address,
                from_block=from_block,
                to_block=to_block,
                topic0=topic0
            )
        except Exception as e:
            logger.error(f"Error getting event logs: {e}")
            return []
    
    async def get_latest_block(self) -> int:
        """
        Получение последнего номера блока
        
        Returns:
            Номер блока
        """
        client = await self._get_client()
        
        try:
            return await client.get_latest_block()
        except Exception as e:
            logger.error(f"Error getting latest block: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получение статистики сервиса
        
        Returns:
            Статистика
        """
        stats = {
            'api_keys_count': len(self.api_keys),
            'rate_limiter': self.limiter.get_stats(),
        }
        
        if self.client:
            stats['client'] = self.client.get_stats()
        
        return stats
    
    async def close(self):
        """Закрытие сервиса и освобождение ресурсов"""
        if self.client and self.client.session:
            await self.client.session.close()
        self.client = None


# Глобальный экземпляр сервиса
_global_service: Optional[BscScanService] = None


def get_bscscan_service() -> BscScanService:
    """Получение глобального экземпляра сервиса"""
    global _global_service
    
    if _global_service is None:
        _global_service = BscScanService()
    
    return _global_service


async def close_bscscan_service():
    """Закрытие глобального сервиса"""
    global _global_service
    
    if _global_service:
        await _global_service.close()
        _global_service = None
