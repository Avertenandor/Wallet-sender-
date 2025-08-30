"""BSCScan/Etherscan API Service для поиска и анализа транзакций"""

import aiohttp
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import time
import logging

logger = logging.getLogger(__name__)


class BSCScanService:
    """Сервис для работы с Etherscan V2 API (для BSC)"""
    
    # Etherscan V2 API endpoints
    BASE_URL = "https://api.etherscan.io/v2/api"
    BSC_CHAIN_ID = 56
    
    def __init__(self, api_keys: List[str]):
        """
        Инициализация сервиса
        
        Args:
            api_keys: Список Etherscan API ключей для ротации
        """
        self.api_keys = api_keys if api_keys else []
        self.current_key_index = 0
        self.last_request_time = {}  # Для ограничения частоты запросов
        self.rate_limit = 5  # Запросов в секунду на ключ
        
        if not self.api_keys:
            logger.warning("No Etherscan API keys provided. Please add keys in config.")
        
    def _get_next_api_key(self) -> str:
        """Получение следующего API ключа с ротацией"""
        if not self.api_keys:
            raise ValueError("Нет доступных API ключей. Добавьте Etherscan API ключи в конфигурацию.")
        
        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return key
    
    async def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполнение асинхронного запроса к Etherscan V2 API
        
        Args:
            params: Параметры запроса
            
        Returns:
            Ответ API в виде словаря
        """
        api_key = self._get_next_api_key()
        params['apikey'] = api_key
        params['chainid'] = self.BSC_CHAIN_ID  # Обязательный параметр для V2 API
        
        # Ограничение частоты запросов
        current_time = time.time()
        if api_key in self.last_request_time:
            time_since_last = current_time - self.last_request_time[api_key]
            if time_since_last < 1 / self.rate_limit:
                await asyncio.sleep(1 / self.rate_limit - time_since_last)
        
        self.last_request_time[api_key] = time.time()
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.BASE_URL, params=params, timeout=30) as response:
                    data = await response.json()
                    
                    # Проверка на ошибку миграции
                    if data.get('status') == '0':
                        error_msg = data.get('message', '').lower()
                        if 'migrate' in error_msg or 'v2' in error_msg:
                            logger.error("BSCScan V1 API is deprecated. Already using V2 API.")
                        elif 'rate limit' in data.get('result', '').lower():
                            # Если достигнут лимит, ждем и пробуем другой ключ
                            await asyncio.sleep(1)
                            return await self._make_request(params)
                    
                    return data
                    
            except asyncio.TimeoutError:
                return {'status': '0', 'message': 'Request timeout', 'result': []}
            except Exception as e:
                logger.error(f"API request error: {e}")
                return {'status': '0', 'message': str(e), 'result': []}
    
    async def get_token_transfers(
        self, 
        address: str, 
        contract_address: Optional[str] = None,
        start_block: int = 0,
        end_block: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = 'desc'
    ) -> List[Dict[str, Any]]:
        """
        Получение токен-трансферов для адреса
        
        Args:
            address: Адрес кошелька
            contract_address: Адрес контракта токена (опционально)
            start_block: Начальный блок
            end_block: Конечный блок
            page: Номер страницы
            offset: Количество записей на странице
            sort: Сортировка (asc/desc)
            
        Returns:
            Список транзакций
        """
        params = {
            'module': 'account',
            'action': 'tokentx',
            'address': address,
            'startblock': start_block,
            'endblock': end_block,
            'page': page,
            'offset': offset,
            'sort': sort
        }
        
        if contract_address:
            params['contractaddress'] = contract_address
        
        result = await self._make_request(params)
        
        if result.get('status') == '1':
            return result.get('result', [])
        return []
    
    async def get_normal_transactions(
        self,
        address: str,
        start_block: int = 0,
        end_block: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = 'desc'
    ) -> List[Dict[str, Any]]:
        """
        Получение обычных транзакций для адреса
        
        Args:
            address: Адрес кошелька
            start_block: Начальный блок
            end_block: Конечный блок
            page: Номер страницы
            offset: Количество записей на странице
            sort: Сортировка (asc/desc)
            
        Returns:
            Список транзакций
        """
        params = {
            'module': 'account',
            'action': 'txlist',
            'address': address,
            'startblock': start_block,
            'endblock': end_block,
            'page': page,
            'offset': offset,
            'sort': sort
        }
        
        result = await self._make_request(params)
        
        if result.get('status') == '1':
            return result.get('result', [])
        return []
    
    async def get_token_balance(
        self,
        address: str,
        contract_address: str,
        tag: str = 'latest'
    ) -> int:
        """
        Получение баланса токена
        
        Args:
            address: Адрес кошелька
            contract_address: Адрес контракта токена
            tag: Тег блока (latest, earliest, pending)
            
        Returns:
            Баланс в Wei
        """
        params = {
            'module': 'account',
            'action': 'tokenbalance',
            'contractaddress': contract_address,
            'address': address,
            'tag': tag
        }
        
        result = await self._make_request(params)
        
        if result.get('status') == '1':
            return int(result.get('result', '0'))
        return 0
    
    async def get_bnb_balance(
        self,
        address: str,
        tag: str = 'latest'
    ) -> int:
        """
        Получение баланса BNB
        
        Args:
            address: Адрес кошелька
            tag: Тег блока (latest, earliest, pending)
            
        Returns:
            Баланс в Wei
        """
        params = {
            'module': 'account',
            'action': 'balance',
            'address': address,
            'tag': tag
        }
        
        result = await self._make_request(params)
        
        if result.get('status') == '1':
            return int(result.get('result', '0'))
        return 0
    
    async def get_token_holders(
        self,
        contract_address: str,
        page: int = 1,
        offset: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Получение списка держателей токена (V2 API feature)
        
        Args:
            contract_address: Адрес контракта токена
            page: Номер страницы
            offset: Количество записей на странице
            
        Returns:
            Список держателей
        """
        params = {
            'module': 'token',
            'action': 'tokenholderlist',
            'contractaddress': contract_address,
            'page': page,
            'offset': offset
        }
        
        result = await self._make_request(params)
        
        if result.get('status') == '1':
            return result.get('result', [])
        return []
    
    async def get_token_info(self, contract_address: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации о токене (V2 API feature)
        
        Args:
            contract_address: Адрес контракта токена
            
        Returns:
            Информация о токене
        """
        params = {
            'module': 'token',
            'action': 'tokeninfo',
            'contractaddress': contract_address
        }
        
        result = await self._make_request(params)
        
        if result.get('status') == '1' and result.get('result'):
            return result.get('result')
        return None
    
    async def get_transaction_by_hash(
        self,
        tx_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Получение информации о транзакции по хешу
        
        Args:
            tx_hash: Хеш транзакции
            
        Returns:
            Информация о транзакции
        """
        params = {
            'module': 'proxy',
            'action': 'eth_getTransactionByHash',
            'txhash': tx_hash
        }
        
        result = await self._make_request(params)
        
        if result.get('result'):
            return result.get('result')
        return None
    
    async def get_transaction_receipt(
        self,
        tx_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Получение квитанции транзакции
        
        Args:
            tx_hash: Хеш транзакции
            
        Returns:
            Квитанция транзакции
        """
        params = {
            'module': 'proxy',
            'action': 'eth_getTransactionReceipt',
            'txhash': tx_hash
        }
        
        result = await self._make_request(params)
        
        if result.get('result'):
            return result.get('result')
        return None
    
    async def get_block_number(self) -> int:
        """
        Получение текущего номера блока
        
        Returns:
            Номер последнего блока
        """
        params = {
            'module': 'proxy',
            'action': 'eth_blockNumber'
        }
        
        result = await self._make_request(params)
        
        if result.get('result'):
            return int(result.get('result'), 16)
        return 0
    
    async def get_gas_price(self) -> int:
        """
        Получение текущей цены газа
        
        Returns:
            Цена газа в Wei
        """
        params = {
            'module': 'proxy',
            'action': 'eth_gasPrice'
        }
        
        result = await self._make_request(params)
        
        if result.get('result'):
            return int(result.get('result'), 16)
        return 5000000000  # 5 Gwei по умолчанию
    
    async def get_block_by_timestamp(
        self,
        timestamp: int,
        closest: str = 'before'
    ) -> Optional[int]:
        """
        Получение номера блока по временной метке
        
        Args:
            timestamp: Unix timestamp
            closest: 'before' или 'after'
            
        Returns:
            Номер блока
        """
        params = {
            'module': 'block',
            'action': 'getblocknobytime',
            'timestamp': timestamp,
            'closest': closest
        }
        
        result = await self._make_request(params)
        
        if result.get('status') == '1':
            return int(result.get('result', 0))
        return None
    
    async def get_event_logs(
        self,
        from_block: int,
        to_block: int,
        address: Optional[str] = None,
        topics: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение логов событий
        
        Args:
            from_block: Начальный блок
            to_block: Конечный блок
            address: Адрес контракта (опционально)
            topics: Список топиков для фильтрации (опционально)
            
        Returns:
            Список логов
        """
        params = {
            'module': 'logs',
            'action': 'getLogs',
            'fromBlock': from_block,
            'toBlock': to_block
        }
        
        if address:
            params['address'] = address
        
        if topics:
            for i, topic in enumerate(topics):
                if topic:
                    params[f'topic{i}'] = topic
        
        result = await self._make_request(params)
        
        if result.get('status') == '1':
            return result.get('result', [])
        return []
    
    def format_transaction(self, tx: Dict[str, Any], is_token: bool = False) -> Dict[str, Any]:
        """
        Форматирование транзакции для отображения
        
        Args:
            tx: Данные транзакции
            is_token: Является ли транзакция токеновой
            
        Returns:
            Отформатированные данные
        """
        formatted = {
            'hash': tx.get('hash', ''),
            'from': tx.get('from', ''),
            'to': tx.get('to', ''),
            'value': tx.get('value', '0'),
            'gas': tx.get('gas', '0'),
            'gasPrice': tx.get('gasPrice', '0'),
            'timestamp': datetime.fromtimestamp(int(tx.get('timeStamp', 0))).strftime('%Y-%m-%d %H:%M:%S') if tx.get('timeStamp') else '',
            'blockNumber': tx.get('blockNumber', '0'),
            'status': 'Success' if tx.get('isError', '0') == '0' else 'Failed'
        }
        
        if is_token:
            formatted['tokenName'] = tx.get('tokenName', '')
            formatted['tokenSymbol'] = tx.get('tokenSymbol', '')
            formatted['tokenDecimal'] = tx.get('tokenDecimal', '18')
            formatted['contractAddress'] = tx.get('contractAddress', '')
        
        return formatted
    
    async def search_transactions(
        self,
        address: str,
        token_filter: Optional[str] = None,
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        Расширенный поиск транзакций с фильтрацией
        
        Args:
            address: Адрес для поиска
            token_filter: Фильтр по токену
            amount_min: Минимальная сумма
            amount_max: Максимальная сумма
            date_from: Начальная дата
            date_to: Конечная дата
            page: Номер страницы
            page_size: Размер страницы
            
        Returns:
            Результаты поиска с метаданными
        """
        # Получаем транзакции
        if token_filter and token_filter != 'ALL':
            transactions = await self.get_token_transfers(
                address=address,
                contract_address=token_filter,
                page=page,
                offset=page_size
            )
            is_token = True
        else:
            # Получаем обычные и токеновые транзакции
            normal_txs = await self.get_normal_transactions(
                address=address,
                page=page,
                offset=page_size
            )
            token_txs = await self.get_token_transfers(
                address=address,
                page=page,
                offset=page_size
            )
            
            # Объединяем и сортируем по времени
            transactions = normal_txs + token_txs
            transactions.sort(key=lambda x: int(x.get('timeStamp', 0)), reverse=True)
            is_token = False
        
        # Применяем фильтры
        filtered = []
        for tx in transactions:
            # Фильтр по дате
            if date_from or date_to:
                tx_time = datetime.fromtimestamp(int(tx.get('timeStamp', 0)))
                if date_from and tx_time < date_from:
                    continue
                if date_to and tx_time > date_to:
                    continue
            
            # Фильтр по сумме
            if amount_min or amount_max:
                value = float(tx.get('value', '0')) / (10 ** int(tx.get('tokenDecimal', 18)))
                if amount_min and value < amount_min:
                    continue
                if amount_max and value > amount_max:
                    continue
            
            filtered.append(self.format_transaction(tx, is_token))
        
        # Пагинация
        total_count = len(filtered)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = filtered[start_idx:end_idx]
        
        return {
            'transactions': paginated,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size
        }
