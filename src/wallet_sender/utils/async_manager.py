"""
Менеджер для асинхронных операций с блокчейном
"""

import asyncio
import threading
import time
from typing import Dict, Any, List, Optional, Callable, Union
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from queue import Queue, Empty
import weakref

@dataclass
class AsyncTask:
    """Задача для асинхронного выполнения"""
    task_id: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: int = 0
    created_at: float = 0
    callback: Optional[Callable] = None
    error_callback: Optional[Callable] = None

class AsyncManager:
    """Менеджер асинхронных операций"""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = Queue()
        self.running_tasks: Dict[str, Future] = {}
        self.completed_tasks: Dict[str, Any] = {}
        self.task_results: Dict[str, Any] = {}
        self.task_errors: Dict[str, Exception] = {}
        
        self._running = False
        self._worker_thread = None
        self._lock = threading.RLock()
        
        # Статистика
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'active_tasks': 0
        }
    
    def start(self):
        """Запускает менеджер асинхронных задач"""
        if not self._running:
            self._running = True
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()
    
    def stop(self):
        """Останавливает менеджер асинхронных задач"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        self.executor.shutdown(wait=True)
    
    def _worker_loop(self):
        """Основной цикл обработки задач"""
        while self._running:
            try:
                # Получаем задачу из очереди
                try:
                    task = self.task_queue.get(timeout=1)
                except Empty:
                    continue
                
                # Проверяем, есть ли свободные воркеры
                if len(self.running_tasks) >= self.max_workers:
                    # Возвращаем задачу в очередь
                    self.task_queue.put(task)
                    time.sleep(0.1)
                    continue
                
                # Запускаем задачу
                self._execute_task(task)
                
            except Exception as e:
                print(f"Ошибка в worker loop: {e}")
                time.sleep(1)
    
    def _execute_task(self, task: AsyncTask):
        """Выполняет задачу асинхронно"""
        with self._lock:
            self.stats['total_tasks'] += 1
            self.stats['active_tasks'] += 1
        
        # Запускаем задачу в executor
        future = self.executor.submit(self._run_task, task)
        self.running_tasks[task.task_id] = future
        
        # Добавляем callback для завершения
        future.add_done_callback(lambda f: self._task_completed(task.task_id, f))
    
    def _run_task(self, task: AsyncTask) -> Any:
        """Выполняет задачу"""
        try:
            result = task.func(*task.args, **task.kwargs)
            return result
        except Exception as e:
            raise e
    
    def _task_completed(self, task_id: str, future: Future):
        """Обрабатывает завершение задачи"""
        with self._lock:
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            
            self.stats['active_tasks'] -= 1
            
            try:
                result = future.result()
                self.task_results[task_id] = result
                self.completed_tasks[task_id] = result
                self.stats['completed_tasks'] += 1
                
                # Вызываем callback если есть
                # Находим задачу по ID (это упрощенная версия)
                # В реальности нужно хранить задачи отдельно
                
            except Exception as e:
                self.task_errors[task_id] = e
                self.stats['failed_tasks'] += 1
    
    def submit_task(self, task_id: str, func: Callable, *args, 
                   callback: Optional[Callable] = None,
                   error_callback: Optional[Callable] = None,
                   priority: int = 0, **kwargs) -> str:
        """Добавляет задачу в очередь"""
        task = AsyncTask(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            created_at=time.time(),
            callback=callback,
            error_callback=error_callback
        )
        
        self.task_queue.put(task)
        return task_id
    
    def get_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """Получает результат задачи"""
        start_time = time.time()
        
        while True:
            with self._lock:
                if task_id in self.task_results:
                    return self.task_results[task_id]
                elif task_id in self.task_errors:
                    raise self.task_errors[task_id]
            
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Задача {task_id} не завершилась за {timeout} секунд")
            
            time.sleep(0.1)
    
    def is_task_completed(self, task_id: str) -> bool:
        """Проверяет, завершена ли задача"""
        with self._lock:
            return task_id in self.task_results or task_id in self.task_errors
    
    def get_task_error(self, task_id: str) -> Optional[Exception]:
        """Получает ошибку задачи"""
        with self._lock:
            return self.task_errors.get(task_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику"""
        with self._lock:
            return self.stats.copy()
    
    def clear_completed_tasks(self):
        """Очищает завершенные задачи"""
        with self._lock:
            self.completed_tasks.clear()
            self.task_results.clear()
            self.task_errors.clear()

class BlockchainAsyncManager:
    """Специализированный менеджер для блокчейн операций"""
    
    def __init__(self, web3_instance, max_workers: int = 3):
        self.web3 = web3_instance
        self.async_manager = AsyncManager(max_workers=max_workers)
        self.async_manager.start()
        
        # Кеш для результатов
        self.result_cache: Dict[str, Any] = {}
        self.cache_ttl = 30.0  # 30 секунд
    
    def get_balance_async(self, address: str, callback: Optional[Callable] = None) -> str:
        """Асинхронно получает баланс BNB"""
        task_id = f"balance_{address}_{int(time.time())}"
        
        def get_balance():
            return self.web3.eth.get_balance(address)
        
        return self.async_manager.submit_task(
            task_id=task_id,
            func=get_balance,
            callback=callback
        )
    
    def get_token_balance_async(self, token_address: str, wallet_address: str, 
                              callback: Optional[Callable] = None) -> str:
        """Асинхронно получает баланс токена"""
        task_id = f"token_balance_{token_address}_{wallet_address}_{int(time.time())}"
        
        def get_token_balance():
            from .cache_manager import token_cache
            
            # Проверяем кеш
            cached_balance = token_cache.get_token_balance(token_address, wallet_address)
            if cached_balance is not None:
                return cached_balance
            
            # Получаем баланс из блокчейна
            contract = self.web3.eth.contract(
                address=token_address,
                abi=[{"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"}]
            )
            
            balance_wei = contract.functions.balanceOf(wallet_address).call()
            decimals = contract.functions.decimals().call()
            balance = balance_wei / (10 ** decimals)
            
            # Сохраняем в кеш
            token_cache.set_token_balance(token_address, wallet_address, balance)
            
            return balance
        
        return self.async_manager.submit_task(
            task_id=task_id,
            func=get_token_balance,
            callback=callback
        )
    
    def get_token_info_async(self, token_address: str, callback: Optional[Callable] = None) -> str:
        """Асинхронно получает информацию о токене"""
        task_id = f"token_info_{token_address}_{int(time.time())}"
        
        def get_token_info():
            from .cache_manager import token_cache
            
            # Проверяем кеш
            cached_info = token_cache.get_token_info(token_address)
            if cached_info is not None:
                return cached_info
            
            # Получаем информацию из блокчейна
            contract = self.web3.eth.contract(
                address=token_address,
                abi=[
                    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
                    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
                    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
                    {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
                ]
            )
            
            info = {
                'name': contract.functions.name().call(),
                'symbol': contract.functions.symbol().call(),
                'decimals': contract.functions.decimals().call(),
                'total_supply': contract.functions.totalSupply().call()
            }
            
            # Сохраняем в кеш
            token_cache.set_token_info(token_address, info)
            
            return info
        
        return self.async_manager.submit_task(
            task_id=task_id,
            func=get_token_info,
            callback=callback
        )
    
    def get_gas_price_async(self, callback: Optional[Callable] = None) -> str:
        """Асинхронно получает цену газа"""
        task_id = f"gas_price_{int(time.time())}"
        
        def get_gas_price():
            from .cache_manager import token_cache
            
            # Проверяем кеш
            cached_price = token_cache.get_gas_price()
            if cached_price is not None:
                return cached_price
            
            # Получаем цену газа
            gas_price = self.web3.eth.gas_price
            
            # Сохраняем в кеш
            token_cache.set_gas_price(gas_price)
            
            return gas_price
        
        return self.async_manager.submit_task(
            task_id=task_id,
            func=get_gas_price,
            callback=callback
        )
    
    def wait_for_result(self, task_id: str, timeout: float = 30.0) -> Any:
        """Ждет результат задачи"""
        return self.async_manager.get_result(task_id, timeout)
    
    def is_task_ready(self, task_id: str) -> bool:
        """Проверяет, готов ли результат"""
        return self.async_manager.is_task_completed(task_id)
    
    def get_task_error(self, task_id: str) -> Optional[Exception]:
        """Получает ошибку задачи"""
        return self.async_manager.get_task_error(task_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику"""
        return self.async_manager.get_stats()
    
    def cleanup(self):
        """Очищает ресурсы"""
        self.async_manager.stop()
        self.result_cache.clear()

# Глобальный экземпляр менеджера
blockchain_async_manager = None

def get_async_manager(web3_instance) -> BlockchainAsyncManager:
    """Получает глобальный экземпляр асинхронного менеджера"""
    global blockchain_async_manager
    if blockchain_async_manager is None:
        blockchain_async_manager = BlockchainAsyncManager(web3_instance)
    return blockchain_async_manager
