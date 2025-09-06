"""
Управление пулом RPC соединений с Web3
Реализует ретраи, таймауты, троттлинг и fallback endpoints
"""

import time
import random
from typing import List, Optional, Any, Dict, Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from web3 import Web3
from web3.exceptions import BlockNotFound, TransactionNotFound
from web3.middleware import geth_poa_middleware
from eth_account import Account
from eth_typing import HexStr
from hexbytes import HexBytes

from ..utils.logger import get_logger
from ..config import get_config
from .models import Settings

logger = get_logger(__name__)


class RPCPool:
    """Пул RPC соединений с балансировкой нагрузки"""
    
    def __init__(self):
        """Инициализация пула RPC"""
        self.config = get_config()
        self.endpoints = []
        self.current_index = 0
        self.max_rps = 5  # Максимум запросов в секунду
        self.last_request_times = {}
        self.request_counts = {}
        self.failed_endpoints = set()
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        self._init_endpoints()
        
    def _init_endpoints(self):
        """Инициализация списка RPC endpoints"""
        # Основные RPC URLs
        rpc_urls = self.config.get('rpc_urls', {})
        
        # BSC Mainnet
        if 'bsc_mainnet' in rpc_urls:
            self.endpoints.append({
                'url': rpc_urls['bsc_mainnet'],
                'priority': 1,
                'name': 'BSC Mainnet Primary'
            })
        
        # BSC Testnet
        if 'bsc_testnet' in rpc_urls:
            self.endpoints.append({
                'url': rpc_urls['bsc_testnet'],
                'priority': 2,
                'name': 'BSC Testnet'
            })
        
        # Дополнительные RPC endpoints
        additional_rpcs = self.config.get('additional_rpcs', [])
        for i, rpc_url in enumerate(additional_rpcs):
            self.endpoints.append({
                'url': rpc_url,
                'priority': 3 + i,
                'name': f'Additional RPC #{i+1}'
            })
        
        # Fallback endpoints (публичные RPC)
        fallback_endpoints = [
            'https://bsc-dataseed.binance.org/',
            'https://bsc-dataseed1.binance.org/',
            'https://bsc-dataseed2.binance.org/',
            'https://bsc-dataseed3.binance.org/',
            'https://bsc-dataseed4.binance.org/',
        ]
        
        for i, url in enumerate(fallback_endpoints):
            self.endpoints.append({
                'url': url,
                'priority': 100 + i,
                'name': f'Fallback RPC #{i+1}'
            })
        
        # Сортируем по приоритету
        self.endpoints.sort(key=lambda x: x['priority'])
        
        logger.info(f"Инициализирован пул из {len(self.endpoints)} RPC endpoints")
    
    def get_web3(self, endpoint: Dict = None) -> Optional[Web3]:
        """
        Получение экземпляра Web3
        
        Args:
            endpoint: Конкретный endpoint или None для автоматического выбора
            
        Returns:
            Web3 экземпляр или None при ошибке
        """
        if endpoint is None:
            endpoint = self._get_next_endpoint()
            
        if endpoint is None:
            logger.error("Нет доступных RPC endpoints")
            return None
        
        try:
            # Применяем троттлинг
            self._apply_throttling(endpoint['url'])
            
            # Создаем Web3 экземпляр
            w3 = Web3(Web3.HTTPProvider(
                endpoint['url'],
                request_kwargs={'timeout': self.config.get('connection_timeout', 30)}
            ))
            
            # Добавляем middleware для BSC (POA)
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            # Проверяем подключение
            if not w3.is_connected():
                raise ConnectionError(f"Не удалось подключиться к {endpoint['name']}")
            
            return w3
            
        except Exception as e:
            logger.error(f"Ошибка подключения к {endpoint['name']}: {e}")
            self._mark_endpoint_failed(endpoint)
            return None
    
    def _get_next_endpoint(self) -> Optional[Dict]:
        """Получение следующего доступного endpoint"""
        available_endpoints = [
            ep for ep in self.endpoints 
            if ep['url'] not in self.failed_endpoints
        ]
        
        if not available_endpoints:
            # Сбрасываем список неудачных и пробуем снова
            logger.warning("Все endpoints недоступны, сброс списка неудачных")
            self.failed_endpoints.clear()
            available_endpoints = self.endpoints.copy()
        
        if not available_endpoints:
            return None
        
        # Round-robin выбор
        if self.current_index >= len(available_endpoints):
            self.current_index = 0
            
        endpoint = available_endpoints[self.current_index]
        self.current_index += 1
        
        return endpoint
    
    def _apply_throttling(self, url: str):
        """Применение ограничения скорости запросов"""
        current_time = time.time()
        
        # Очищаем старые записи (старше 1 секунды)
        if url in self.last_request_times:
            self.last_request_times[url] = [
                t for t in self.last_request_times[url]
                if current_time - t < 1.0
            ]
        else:
            self.last_request_times[url] = []
        
        # Проверяем количество запросов за последнюю секунду
        request_count = len(self.last_request_times[url])
        
        if request_count >= self.max_rps:
            # Ждем до следующей секунды
            sleep_time = 1.0 - (current_time - self.last_request_times[url][0])
            if sleep_time > 0:
                logger.debug(f"Троттлинг: ожидание {sleep_time:.2f}с для {url}")
                time.sleep(sleep_time)
                current_time = time.time()
        
        # Записываем время запроса
        self.last_request_times[url].append(current_time)
    
    def _mark_endpoint_failed(self, endpoint: Dict):
        """Пометить endpoint как неудачный"""
        self.failed_endpoints.add(endpoint['url'])
        logger.warning(f"Endpoint {endpoint['name']} помечен как недоступный")
        
        # Автоматическое восстановление через 60 секунд
        def recover():
            time.sleep(60)
            if endpoint['url'] in self.failed_endpoints:
                self.failed_endpoints.remove(endpoint['url'])
                logger.info(f"Endpoint {endpoint['name']} восстановлен")
        
        self.executor.submit(recover)
    
    def execute_with_retry(self, func: Callable, *args, max_retries: int = None, 
                          backoff_factor: float = 1.0, **kwargs) -> Any:
        """
        Выполнение функции с повторными попытками
        
        Args:
            func: Функция для выполнения
            max_retries: Максимум попыток
            backoff_factor: Фактор экспоненциального отката
            
        Returns:
            Результат функции или None при ошибке
        """
        if max_retries is None:
            max_retries = self.config.get('retry_count', 3)
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                # Получаем новый Web3 для каждой попытки
                w3 = self.get_web3()
                if w3 is None:
                    raise ConnectionError("Не удалось получить Web3 соединение")
                
                # Выполняем функцию
                result = func(w3, *args, **kwargs)
                return result
                
            except (ConnectionError, TimeoutError, BlockNotFound, TransactionNotFound) as e:
                last_exception = e
                
                if attempt < max_retries - 1:
                    # Экспоненциальный откат
                    sleep_time = backoff_factor * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Попытка {attempt + 1}/{max_retries} неудачна: {e}")
                    logger.info(f"Повтор через {sleep_time:.2f}с...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Все {max_retries} попыток неудачны: {e}")
            
            except Exception as e:
                logger.error(f"Неожиданная ошибка при выполнении функции: {e}")
                last_exception = e
                break
        
        raise last_exception if last_exception else Exception("Неизвестная ошибка")
    
    async def execute_batch(self, requests: List[Dict]) -> List[Any]:
        """
        Выполнение пакета запросов
        
        Args:
            requests: Список запросов вида {'method': str, 'params': list}
            
        Returns:
            Список результатов
        """
        results = []
        
        for request in requests:
            try:
                w3 = self.get_web3()
                if w3 is None:
                    results.append({'error': 'No Web3 connection'})
                    continue
                
                # Выполняем запрос
                method = request.get('method')
                params = request.get('params', [])
                
                if hasattr(w3.eth, method):
                    func = getattr(w3.eth, method)
                    result = func(*params)
                    results.append({'result': result})
                else:
                    results.append({'error': f'Unknown method: {method}'})
                    
            except Exception as e:
                results.append({'error': str(e)})
        
        return results
    
    def test_all_endpoints(self) -> Dict[str, Dict]:
        """Тестирование всех endpoints"""
        results = {}
        
        for endpoint in self.endpoints:
            try:
                start_time = time.time()
                
                w3 = Web3(Web3.HTTPProvider(
                    endpoint['url'],
                    request_kwargs={'timeout': 5}
                ))
                
                if w3.is_connected():
                    block_number = w3.eth.block_number
                    chain_id = w3.eth.chain_id
                    response_time = (time.time() - start_time) * 1000
                    
                    results[endpoint['name']] = {
                        'status': 'online',
                        'block_number': block_number,
                        'chain_id': chain_id,
                        'response_time_ms': round(response_time, 2),
                        'url': endpoint['url']
                    }
                else:
                    results[endpoint['name']] = {
                        'status': 'offline',
                        'error': 'Connection failed',
                        'url': endpoint['url']
                    }
                    
            except Exception as e:
                results[endpoint['name']] = {
                    'status': 'error',
                    'error': str(e),
                    'url': endpoint['url']
                }
        
        return results
    
    def get_statistics(self) -> Dict:
        """Получение статистики использования RPC"""
        stats = {
            'total_endpoints': len(self.endpoints),
            'active_endpoints': len(self.endpoints) - len(self.failed_endpoints),
            'failed_endpoints': list(self.failed_endpoints),
            'request_counts': dict(self.request_counts),
            'max_rps': self.max_rps
        }
        
        # Тестируем текущую скорость
        try:
            w3 = self.get_web3()
            if w3:
                start = time.time()
                _ = w3.eth.block_number
                stats['current_latency_ms'] = round((time.time() - start) * 1000, 2)
        except:
            stats['current_latency_ms'] = None
        
        return stats
    
    def set_max_rps(self, max_rps: int):
        """Установка максимального RPS"""
        self.max_rps = max_rps
        logger.info(f"Установлен максимальный RPS: {max_rps}")
    
    def close(self):
        """Закрытие пула"""
        self.executor.shutdown(wait=True)
        logger.info("RPC пул закрыт")


# Глобальный экземпляр пула
_rpc_pool: Optional[RPCPool] = None


def get_rpc_pool() -> RPCPool:
    """Получение глобального экземпляра пула RPC"""
    global _rpc_pool
    
    if _rpc_pool is None:
        _rpc_pool = RPCPool()
    
    return _rpc_pool


def close_rpc_pool():
    """Закрытие глобального пула RPC"""
    global _rpc_pool
    
    if _rpc_pool:
        _rpc_pool.close()
        _rpc_pool = None


# Удобные функции для быстрого доступа
def get_web3() -> Optional[Web3]:
    """Быстрое получение Web3 экземпляра"""
    pool = get_rpc_pool()
    return pool.get_web3()


def execute_with_retry(func: Callable, *args, **kwargs) -> Any:
    """Быстрое выполнение функции с ретраями"""
    pool = get_rpc_pool()
    return pool.execute_with_retry(func, *args, **kwargs)


def get_receipts_batch(tx_hashes: List[str]) -> Dict[str, Optional[dict]]:
    """Получение чеков для батча транзакций"""
    pool = get_rpc_pool()
    results = {}
    
    def get_receipt(w3: Web3, tx_hash: str):
        try:
            return w3.eth.get_transaction_receipt(HexStr(tx_hash))
        except TransactionNotFound:
            return None
    
    for tx_hash in tx_hashes:
        try:
            receipt = pool.execute_with_retry(get_receipt, tx_hash, max_retries=1)
            results[tx_hash] = dict(receipt) if receipt else None
        except Exception as e:
            logger.error(f"Ошибка получения чека {tx_hash}: {e}")
            results[tx_hash] = None
    
    return results


def estimate_gas_safely(tx: dict) -> int:
    """
    Безопасная оценка газа для транзакции
    
    Args:
        tx: Словарь транзакции
        
    Returns:
        Оценка газа с запасом 20%
    """
    pool = get_rpc_pool()
    
    def estimate(w3: Web3, transaction: dict):
        try:
            gas_estimate = w3.eth.estimate_gas(transaction)
            # Добавляем 20% запас
            return int(gas_estimate * 1.2)
        except Exception as e:
            logger.warning(f"Ошибка оценки газа: {e}, используем значение по умолчанию")
            # Возвращаем дефолтные значения
            if 'data' in transaction and transaction['data']:
                return 100000  # Для контрактных вызовов
            return 21000  # Для простых переводов
    
    return pool.execute_with_retry(estimate, tx)


def send_bnb(sender_key: str, to_address: str, amount_wei: int, 
            gas_price_wei: Optional[int] = None, gas_limit: Optional[int] = None,
            nonce: Optional[int] = None) -> str:
    """
    Отправка BNB
    
    Args:
        sender_key: Приватный ключ отправителя
        to_address: Адрес получателя
        amount_wei: Сумма в wei
        gas_price_wei: Цена газа в wei (None = автоматически)
        gas_limit: Лимит газа (None = автоматически)
        nonce: Nonce транзакции (None = автоматически)
        
    Returns:
        Хэш транзакции
    """
    pool = get_rpc_pool()
    
    def send_tx(w3: Web3):
        # Получаем аккаунт
        account = Account.from_key(sender_key)
        sender_address = account.address
        
        # Формируем транзакцию
        tx = {
            'from': sender_address,
            'to': Web3.to_checksum_address(to_address),
            'value': amount_wei,
            'chainId': w3.eth.chain_id
        }
        
        # Устанавливаем nonce
        if nonce is not None:
            tx['nonce'] = nonce
        else:
            tx['nonce'] = w3.eth.get_transaction_count(sender_address, 'pending')
        
        # Устанавливаем газ
        if gas_price_wei is not None:
            tx['gasPrice'] = gas_price_wei
        else:
            tx['gasPrice'] = w3.eth.gas_price
        
        if gas_limit is not None:
            tx['gas'] = gas_limit
        else:
            tx['gas'] = estimate_gas_safely(tx)
        
        # Подписываем и отправляем
        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        logger.info(f"BNB транзакция отправлена: {tx_hash.hex()}")
        return tx_hash.hex()
    
    return pool.execute_with_retry(send_tx)


def send_erc20(sender_key: str, token_address: str, to_address: str, 
               amount_wei: int, gas_price_wei: Optional[int] = None,
               gas_limit: Optional[int] = None, nonce: Optional[int] = None) -> str:
    """
    Отправка ERC20 токенов
    
    Args:
        sender_key: Приватный ключ отправителя
        token_address: Адрес контракта токена
        to_address: Адрес получателя
        amount_wei: Сумма в wei (с учетом decimals)
        gas_price_wei: Цена газа в wei
        gas_limit: Лимит газа
        nonce: Nonce транзакции
        
    Returns:
        Хэш транзакции
    """
    pool = get_rpc_pool()
    
    def send_tx(w3: Web3):
        # Получаем аккаунт
        account = Account.from_key(sender_key)
        sender_address = account.address
        
        # ABI для ERC20 transfer
        erc20_abi = [{
            "constant": False,
            "inputs": [
                {"name": "_to", "type": "address"},
                {"name": "_value", "type": "uint256"}
            ],
            "name": "transfer",
            "outputs": [{"name": "", "type": "bool"}],
            "type": "function"
        }]
        
        # Создаем контракт
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=erc20_abi
        )
        
        # Формируем транзакцию
        tx = contract.functions.transfer(
            Web3.to_checksum_address(to_address),
            amount_wei
        ).build_transaction({
            'from': sender_address,
            'chainId': w3.eth.chain_id
        })
        
        # Устанавливаем nonce
        if nonce is not None:
            tx['nonce'] = nonce
        else:
            tx['nonce'] = w3.eth.get_transaction_count(sender_address, 'pending')
        
        # Устанавливаем газ
        if gas_price_wei is not None:
            tx['gasPrice'] = gas_price_wei
        else:
            tx['gasPrice'] = w3.eth.gas_price
        
        if gas_limit is not None:
            tx['gas'] = gas_limit
        else:
            tx['gas'] = estimate_gas_safely(tx)
        
        # Подписываем и отправляем
        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        logger.info(f"ERC20 транзакция отправлена: {tx_hash.hex()}")
        return tx_hash.hex()
    
    return pool.execute_with_retry(send_tx)


def normalize_error(error: Exception) -> str:
    """
    Нормализация ошибок в коды
    
    Args:
        error: Исключение
        
    Returns:
        Код ошибки
    """
    error_str = str(error).lower()
    
    if 'nonce too low' in error_str:
        return 'nonce_too_low'
    elif 'replacement transaction underpriced' in error_str:
        return 'replacement_underpriced'
    elif 'insufficient funds' in error_str:
        return 'insufficient_funds'
    elif 'transaction underpriced' in error_str:
        return 'tx_underpriced'
    elif 'timeout' in error_str:
        return 'timeout'
    elif 'connection' in error_str or 'rpc' in error_str:
        return 'rpc_unavailable'
    else:
        return 'unknown_error'
