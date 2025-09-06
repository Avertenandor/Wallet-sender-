"""
Управление пулом RPC соединений с Web3 - v2.1.x
Реализует health check, failover, hedging, ретраи, таймауты и троттлинг
"""

import time
import random
import threading
import asyncio
from typing import List, Optional, Any, Dict, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, TimeoutError, Future, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import statistics

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


@dataclass
class EndpointStats:
    """Статистика для RPC endpoint"""
    url: str
    name: str
    priority: int
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0
    latencies: deque = field(default_factory=lambda: deque(maxlen=100))
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    failure_reason: Optional[str] = None
    is_healthy: bool = True
    consecutive_failures: int = 0
    
    @property
    def success_rate(self) -> float:
        """Процент успешных запросов"""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def avg_latency_ms(self) -> float:
        """Средняя задержка"""
        if not self.latencies:
            return 0
        return statistics.mean(self.latencies)
    
    @property
    def p95_latency_ms(self) -> float:
        """95-й перцентиль задержки"""
        if len(self.latencies) < 2:
            return self.avg_latency_ms
        sorted_latencies = sorted(self.latencies)
        index = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[index]
    
    def record_success(self, latency_ms: float):
        """Запись успешного запроса"""
        self.total_requests += 1
        self.successful_requests += 1
        self.total_latency_ms += latency_ms
        self.latencies.append(latency_ms)
        self.last_success = datetime.now()
        self.consecutive_failures = 0
        self.is_healthy = True
    
    def record_failure(self, reason: str):
        """Запись неудачного запроса"""
        self.total_requests += 1
        self.failed_requests += 1
        self.last_failure = datetime.now()
        self.failure_reason = reason
        self.consecutive_failures += 1
        
        # Помечаем как нездоровый после 3 последовательных ошибок
        if self.consecutive_failures >= 3:
            self.is_healthy = False


class HealthChecker:
    """Health checker для RPC endpoints"""
    
    def __init__(self, check_interval: int = 30, timeout: int = 5):
        """
        Args:
            check_interval: Интервал проверки в секундах
            timeout: Таймаут для health check
        """
        self.check_interval = check_interval
        self.timeout = timeout
        self.is_running = False
        self.check_thread = None
        self.endpoints_stats: Dict[str, EndpointStats] = {}
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    def start(self, endpoints: List[Dict]):
        """Запуск health checker"""
        if self.is_running:
            return
        
        # Инициализируем статистику для endpoints
        for ep in endpoints:
            self.endpoints_stats[ep['url']] = EndpointStats(
                url=ep['url'],
                name=ep['name'],
                priority=ep['priority']
            )
        
        self.is_running = True
        self.check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.check_thread.start()
        logger.info(f"Health checker started for {len(endpoints)} endpoints")
    
    def stop(self):
        """Остановка health checker"""
        self.is_running = False
        if self.check_thread:
            self.check_thread.join(timeout=5)
        self.executor.shutdown(wait=False)
        logger.info("Health checker stopped")
    
    def _health_check_loop(self):
        """Основной цикл проверки здоровья"""
        while self.is_running:
            try:
                self._check_all_endpoints()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Health check error: {e}")
                time.sleep(5)
    
    def _check_all_endpoints(self):
        """Проверка всех endpoints"""
        futures = []
        
        for url, stats in self.endpoints_stats.items():
            future = self.executor.submit(self._check_endpoint, url)
            futures.append((url, future))
        
        # Ждем завершения всех проверок
        for url, future in futures:
            try:
                result = future.result(timeout=self.timeout)
                stats = self.endpoints_stats[url]
                
                if result['success']:
                    stats.record_success(result['latency_ms'])
                else:
                    stats.record_failure(result['error'])
                    
            except Exception as e:
                stats = self.endpoints_stats[url]
                stats.record_failure(str(e))
    
    def _check_endpoint(self, url: str) -> Dict:
        """Проверка одного endpoint"""
        start_time = time.time()
        
        try:
            w3 = Web3(Web3.HTTPProvider(
                url,
                request_kwargs={'timeout': self.timeout}
            ))
            
            if not w3.is_connected():
                return {
                    'success': False,
                    'error': 'Not connected'
                }
            
            # Проверяем базовые вызовы
            block_number = w3.eth.block_number
            chain_id = w3.eth.chain_id
            
            latency_ms = (time.time() - start_time) * 1000
            
            return {
                'success': True,
                'block_number': block_number,
                'chain_id': chain_id,
                'latency_ms': latency_ms
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_healthy_endpoints(self) -> List[EndpointStats]:
        """Получение списка здоровых endpoints"""
        healthy = [stats for stats in self.endpoints_stats.values() 
                  if stats.is_healthy]
        
        # Сортируем по приоритету, затем по средней задержке
        healthy.sort(key=lambda x: (x.priority, x.avg_latency_ms))
        
        return healthy
    
    def get_best_endpoint(self) -> Optional[EndpointStats]:
        """Получение лучшего endpoint"""
        healthy = self.get_healthy_endpoints()
        
        if not healthy:
            # Если нет здоровых, пробуем восстановить
            self._try_recover_endpoints()
            healthy = self.get_healthy_endpoints()
        
        return healthy[0] if healthy else None
    
    def _try_recover_endpoints(self):
        """Попытка восстановления endpoints"""
        for stats in self.endpoints_stats.values():
            if not stats.is_healthy:
                # Если прошло больше 60 секунд с последней ошибки
                if stats.last_failure:
                    elapsed = (datetime.now() - stats.last_failure).total_seconds()
                    if elapsed > 60:
                        stats.is_healthy = True
                        stats.consecutive_failures = 0
                        logger.info(f"Trying to recover endpoint: {stats.name}")


class RPCManager:
    """Улучшенный менеджер RPC соединений с health check и failover"""
    
    def __init__(self):
        """Инициализация менеджера"""
        self.config = get_config()
        self.endpoints = []
        self.health_checker = HealthChecker()
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Настройки
        self.max_rps = self.config.get('rpc', {}).get('max_rps', 5)
        self.hedge_enabled = self.config.get('rpc', {}).get('hedge', {}).get('enabled', False)
        self.hedge_threshold_ms = self.config.get('rpc', {}).get('hedge', {}).get('threshold_ms', 800)
        
        # Троттлинг
        self.last_request_times = {}
        self.throttle_lock = threading.Lock()
        
        self._init_endpoints()
        self.health_checker.start(self.endpoints)
    
    def _init_endpoints(self):
        """Инициализация списка RPC endpoints"""
        # Получаем список из конфига
        rpc_list = self.config.get('rpc', {}).get('list', [])
        
        if not rpc_list:
            # Используем дефолтные BSC endpoints
            rpc_list = [
                'https://bsc-dataseed.binance.org/',
                'https://bsc-dataseed1.binance.org/',
                'https://bsc-dataseed2.binance.org/',
                'https://bsc-dataseed3.binance.org/',
            ]
        
        # Создаем список endpoints с приоритетами
        for i, url in enumerate(rpc_list):
            self.endpoints.append({
                'url': url,
                'priority': i,
                'name': f'RPC #{i+1}'
            })
        
        logger.info(f"Initialized {len(self.endpoints)} RPC endpoints")
    
    def current_primary(self) -> Optional[str]:
        """Получение текущего основного RPC"""
        best = self.health_checker.get_best_endpoint()
        return best.url if best else None
    
    def get_client(self, force_url: Optional[str] = None) -> Optional[Web3]:
        """
        Получение Web3 клиента
        
        Args:
            force_url: Принудительный URL endpoint
            
        Returns:
            Web3 экземпляр
        """
        url = force_url or self.current_primary()
        
        if not url:
            logger.error("No healthy RPC endpoints available")
            return None
        
        try:
            # Применяем троттлинг
            self._apply_throttling(url)
            
            # Создаем Web3 экземпляр
            w3 = Web3(Web3.HTTPProvider(
                url,
                request_kwargs={'timeout': self.config.get('connection_timeout', 30)}
            ))
            
            # Добавляем middleware для BSC (POA)
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            # Проверяем подключение
            if not w3.is_connected():
                raise ConnectionError(f"Failed to connect to {url}")
            
            return w3
            
        except Exception as e:
            logger.error(f"Error connecting to {url}: {e}")
            self.record_result(url, False, 0, str(e))
            
            # Пробуем failover
            return self._failover_connect()
    
    def _failover_connect(self) -> Optional[Web3]:
        """Failover подключение к резервным RPC"""
        healthy = self.health_checker.get_healthy_endpoints()
        
        for stats in healthy[1:]:  # Пропускаем первый (он уже не работал)
            try:
                logger.info(f"Failover to {stats.name}")
                
                w3 = Web3(Web3.HTTPProvider(
                    stats.url,
                    request_kwargs={'timeout': 10}
                ))
                
                w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                
                if w3.is_connected():
                    return w3
                    
            except Exception as e:
                logger.warning(f"Failover failed for {stats.name}: {e}")
                continue
        
        logger.error("All failover attempts failed")
        return None
    
    def execute_with_hedge(self, func: Callable, *args, **kwargs) -> Any:
        """
        Выполнение с hedging (параллельные запросы)
        
        Args:
            func: Функция для выполнения
            
        Returns:
            Результат первого успешного запроса
        """
        if not self.hedge_enabled:
            return self.execute_with_retry(func, *args, **kwargs)
        
        healthy = self.health_checker.get_healthy_endpoints()
        
        if len(healthy) < 2:
            # Недостаточно endpoints для hedging
            return self.execute_with_retry(func, *args, **kwargs)
        
        # Запускаем основной запрос
        primary_future = self.executor.submit(
            self._execute_single, healthy[0].url, func, *args, **kwargs
        )
        
        # Ждем hedge_threshold_ms
        try:
            result = primary_future.result(timeout=self.hedge_threshold_ms / 1000)
            return result
        except TimeoutError:
            # Запускаем резервный запрос
            logger.debug(f"Hedging: launching backup request after {self.hedge_threshold_ms}ms")
            
            backup_future = self.executor.submit(
                self._execute_single, healthy[1].url, func, *args, **kwargs
            )
            
            # Ждем первый успешный результат
            futures = [primary_future, backup_future]
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    # Отменяем оставшиеся
                    for f in futures:
                        if f != future and not f.done():
                            f.cancel()
                    return result
                except Exception as e:
                    logger.warning(f"Hedged request failed: {e}")
                    continue
            
            raise Exception("All hedged requests failed")
    
    def _execute_single(self, url: str, func: Callable, *args, **kwargs) -> Any:
        """Выполнение одного запроса"""
        start_time = time.time()
        
        try:
            w3 = Web3(Web3.HTTPProvider(
                url,
                request_kwargs={'timeout': 30}
            ))
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            result = func(w3, *args, **kwargs)
            
            latency_ms = (time.time() - start_time) * 1000
            self.record_result(url, True, latency_ms)
            
            return result
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self.record_result(url, False, latency_ms, str(e))
            raise
    
    def execute_with_retry(self, func: Callable, *args, max_retries: int = None,
                          backoff_factor: float = 1.0, **kwargs) -> Any:
        """
        Выполнение с повторными попытками и failover
        
        Args:
            func: Функция для выполнения
            max_retries: Максимум попыток
            backoff_factor: Фактор экспоненциального отката
            
        Returns:
            Результат функции
        """
        if max_retries is None:
            max_retries = self.config.get('retry_count', 3)
        
        last_exception = None
        healthy_endpoints = self.health_checker.get_healthy_endpoints()
        
        for attempt in range(max_retries):
            # Выбираем endpoint для этой попытки
            if attempt < len(healthy_endpoints):
                endpoint = healthy_endpoints[attempt]
                url = endpoint.url
            else:
                # Используем лучший доступный
                best = self.health_checker.get_best_endpoint()
                if not best:
                    raise ConnectionError("No healthy endpoints available")
                url = best.url
            
            try:
                start_time = time.time()
                
                # Получаем Web3
                w3 = self.get_client(force_url=url)
                if w3 is None:
                    raise ConnectionError(f"Failed to get Web3 for {url}")
                
                # Выполняем функцию
                result = func(w3, *args, **kwargs)
                
                # Записываем успех
                latency_ms = (time.time() - start_time) * 1000
                self.record_result(url, True, latency_ms)
                
                return result
                
            except Exception as e:
                last_exception = e
                latency_ms = (time.time() - start_time) * 1000 if 'start_time' in locals() else 0
                self.record_result(url, False, latency_ms, str(e))
                
                if attempt < max_retries - 1:
                    # Экспоненциальный откат
                    sleep_time = backoff_factor * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                    logger.info(f"Retrying in {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"All {max_retries} attempts failed: {e}")
        
        raise last_exception if last_exception else Exception("Unknown error")
    
    def record_result(self, url: str, success: bool, latency_ms: float, error: str = None):
        """
        Запись результата запроса
        
        Args:
            url: URL endpoint
            success: Успешность запроса
            latency_ms: Задержка в миллисекундах
            error: Текст ошибки
        """
        stats = self.health_checker.endpoints_stats.get(url)
        
        if stats:
            if success:
                stats.record_success(latency_ms)
            else:
                stats.record_failure(error or "Unknown error")
    
    def _apply_throttling(self, url: str):
        """Применение ограничения скорости запросов"""
        with self.throttle_lock:
            current_time = time.time()
            
            # Очищаем старые записи
            if url in self.last_request_times:
                self.last_request_times[url] = [
                    t for t in self.last_request_times[url]
                    if current_time - t < 1.0
                ]
            else:
                self.last_request_times[url] = []
            
            # Проверяем количество запросов
            request_count = len(self.last_request_times[url])
            
            if request_count >= self.max_rps:
                # Ждем до следующей секунды
                sleep_time = 1.0 - (current_time - self.last_request_times[url][0])
                if sleep_time > 0:
                    logger.debug(f"Throttling: waiting {sleep_time:.2f}s for {url}")
                    time.sleep(sleep_time)
                    current_time = time.time()
            
            # Записываем время запроса
            self.last_request_times[url].append(current_time)
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        endpoints_stats = []
        
        for stats in self.health_checker.endpoints_stats.values():
            endpoints_stats.append({
                'name': stats.name,
                'url': stats.url,
                'is_healthy': stats.is_healthy,
                'total_requests': stats.total_requests,
                'success_rate': f"{stats.success_rate:.1f}%",
                'avg_latency_ms': round(stats.avg_latency_ms, 2),
                'p95_latency_ms': round(stats.p95_latency_ms, 2),
                'consecutive_failures': stats.consecutive_failures,
                'last_success': stats.last_success.isoformat() if stats.last_success else None,
                'last_failure': stats.last_failure.isoformat() if stats.last_failure else None,
                'failure_reason': stats.failure_reason
            })
        
        # Сортируем по приоритету
        endpoints_stats.sort(key=lambda x: x['url'])
        
        healthy_count = len(self.health_checker.get_healthy_endpoints())
        
        return {
            'total_endpoints': len(self.endpoints),
            'healthy_endpoints': healthy_count,
            'current_primary': self.current_primary(),
            'hedge_enabled': self.hedge_enabled,
            'hedge_threshold_ms': self.hedge_threshold_ms,
            'max_rps': self.max_rps,
            'endpoints': endpoints_stats
        }
    
    def close(self):
        """Закрытие менеджера"""
        self.health_checker.stop()
        self.executor.shutdown(wait=True)
        logger.info("RPC Manager closed")


# Сохраняем обратную совместимость
class RPCPool(RPCManager):
    """Обратная совместимость с старым API"""
    
    def get_web3(self, endpoint: Dict = None) -> Optional[Web3]:
        """Старый метод для совместимости"""
        url = endpoint['url'] if endpoint else None
        return self.get_client(force_url=url)
    
    def test_all_endpoints(self) -> Dict[str, Dict]:
        """Тестирование всех endpoints"""
        results = {}
        
        for ep_stats in self.health_checker.endpoints_stats.values():
            result = self.health_checker._check_endpoint(ep_stats.url)
            
            results[ep_stats.name] = {
                'status': 'online' if result['success'] else 'offline',
                'block_number': result.get('block_number'),
                'chain_id': result.get('chain_id'),
                'response_time_ms': round(result.get('latency_ms', 0), 2),
                'url': ep_stats.url,
                'error': result.get('error')
            }
        
        return results
    
    def get_statistics(self) -> Dict:
        """Старый метод для совместимости"""
        return self.get_stats()
    
    def set_max_rps(self, max_rps: int):
        """Установка максимального RPS"""
        self.max_rps = max_rps
        logger.info(f"Set max RPS: {max_rps}")


# Глобальный экземпляр
_rpc_manager: Optional[RPCManager] = None


def get_rpc_pool() -> RPCManager:
    """Получение глобального экземпляра (совместимость)"""
    global _rpc_manager
    
    if _rpc_manager is None:
        _rpc_manager = RPCManager()
    
    return _rpc_manager


def get_rpc_manager() -> RPCManager:
    """Получение глобального RPC Manager"""
    return get_rpc_pool()


def close_rpc_pool():
    """Закрытие глобального пула"""
    global _rpc_manager
    
    if _rpc_manager:
        _rpc_manager.close()
        _rpc_manager = None


# Удобные функции для быстрого доступа (обратная совместимость)
def get_web3() -> Optional[Web3]:
    """Быстрое получение Web3 экземпляра"""
    manager = get_rpc_manager()
    return manager.get_client()


def execute_with_retry(func: Callable, *args, **kwargs) -> Any:
    """Быстрое выполнение функции с ретраями"""
    manager = get_rpc_manager()
    return manager.execute_with_retry(func, *args, **kwargs)


def get_receipts_batch(tx_hashes: List[str]) -> Dict[str, Optional[dict]]:
    """Получение чеков для батча транзакций"""
    manager = get_rpc_manager()
    results = {}
    
    def get_receipt(w3: Web3, tx_hash: str):
        try:
            return w3.eth.get_transaction_receipt(HexStr(tx_hash))
        except TransactionNotFound:
            return None
    
    for tx_hash in tx_hashes:
        try:
            receipt = manager.execute_with_retry(get_receipt, tx_hash, max_retries=1)
            results[tx_hash] = dict(receipt) if receipt else None
        except Exception as e:
            logger.error(f"Error getting receipt {tx_hash}: {e}")
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
    manager = get_rpc_manager()
    
    def estimate(w3: Web3, transaction: dict):
        try:
            gas_estimate = w3.eth.estimate_gas(transaction)
            # Добавляем 20% запас
            return int(gas_estimate * 1.2)
        except Exception as e:
            logger.warning(f"Gas estimation error: {e}, using default")
            # Возвращаем дефолтные значения
            if 'data' in transaction and transaction['data']:
                return 100000  # Для контрактных вызовов
            return 21000  # Для простых переводов
    
    return manager.execute_with_retry(estimate, tx)


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
    manager = get_rpc_manager()
    
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
        
        logger.info(f"BNB transaction sent: {tx_hash.hex()}")
        return tx_hash.hex()
    
    # Используем hedging для критичных транзакций
    if manager.hedge_enabled:
        return manager.execute_with_hedge(send_tx)
    else:
        return manager.execute_with_retry(send_tx)


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
    manager = get_rpc_manager()
    
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
        
        logger.info(f"ERC20 transaction sent: {tx_hash.hex()}")
        return tx_hash.hex()
    
    # Используем hedging для критичных транзакций
    if manager.hedge_enabled:
        return manager.execute_with_hedge(send_tx)
    else:
        return manager.execute_with_retry(send_tx)


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
