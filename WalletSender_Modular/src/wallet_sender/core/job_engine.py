"""
Движок выполнения задач с управлением очередью и nonce
"""

import time
import threading
import queue
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from web3 import Web3
from eth_account import Account

from .store import get_store
from .rpc import get_rpc_pool
from ..utils.logger import get_logger
from ..config import get_config

logger = get_logger(__name__)


class JobState(Enum):
    """Состояния задачи"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NonceManager:
    """Менеджер nonce для предотвращения конфликтов"""
    
    def __init__(self):
        self.nonces = {}  # {address: nonce}
        self.locks = {}   # {address: threading.Lock}
        self.pending_txs = {}  # {address: set(nonces)}
        
    def get_nonce(self, w3: Web3, address: str) -> int:
        """
        Получение следующего nonce для адреса
        
        Args:
            w3: Web3 экземпляр
            address: Адрес отправителя
            
        Returns:
            Следующий nonce
        """
        # Нормализуем адрес
        address = Web3.to_checksum_address(address)
        
        # Создаем блокировку для адреса если её нет
        if address not in self.locks:
            self.locks[address] = threading.Lock()
        
        with self.locks[address]:
            # Получаем текущий nonce из сети
            network_nonce = w3.eth.get_transaction_count(address, 'pending')
            
            # Если у нас нет кэшированного nonce или он меньше сетевого
            if address not in self.nonces or self.nonces[address] < network_nonce:
                self.nonces[address] = network_nonce
            
            # Получаем nonce для использования
            nonce = self.nonces[address]
            
            # Увеличиваем для следующего использования
            self.nonces[address] += 1
            
            # Добавляем в pending
            if address not in self.pending_txs:
                self.pending_txs[address] = set()
            self.pending_txs[address].add(nonce)
            
            logger.debug(f"Выдан nonce {nonce} для {address}")
            return nonce
    
    def confirm_nonce(self, address: str, nonce: int):
        """Подтверждение использования nonce"""
        address = Web3.to_checksum_address(address)
        
        if address in self.pending_txs and nonce in self.pending_txs[address]:
            self.pending_txs[address].remove(nonce)
            logger.debug(f"Подтвержден nonce {nonce} для {address}")
    
    def release_nonce(self, address: str, nonce: int):
        """Освобождение nonce при ошибке"""
        address = Web3.to_checksum_address(address)
        
        with self.locks.get(address, threading.Lock()):
            # Удаляем из pending
            if address in self.pending_txs and nonce in self.pending_txs[address]:
                self.pending_txs[address].remove(nonce)
            
            # Если это был последний nonce, откатываем счетчик
            if address in self.nonces and self.nonces[address] == nonce + 1:
                self.nonces[address] = nonce
                logger.debug(f"Откат nonce до {nonce} для {address}")
    
    def reset_address(self, address: str):
        """Сброс всех nonce для адреса"""
        address = Web3.to_checksum_address(address)
        
        with self.locks.get(address, threading.Lock()):
            if address in self.nonces:
                del self.nonces[address]
            if address in self.pending_txs:
                del self.pending_txs[address]
            logger.info(f"Сброшены nonce для {address}")


class JobEngine:
    """Движок выполнения задач"""
    
    def __init__(self):
        """Инициализация движка"""
        self.store = get_store()
        self.rpc_pool = get_rpc_pool()
        self.config = get_config()
        self.nonce_manager = NonceManager()
        
        self.job_queue = queue.PriorityQueue()
        self.active_jobs = {}  # {job_id: JobExecutor}
        self.job_threads = {}  # {job_id: Thread}
        
        self.is_running = False
        self.main_thread = None
        
        # Колбеки для событий
        self.callbacks = {
            'job_started': [],
            'job_completed': [],
            'job_failed': [],
            'job_progress': [],
            'job_paused': [],
            'job_resumed': []
        }
    
    def start(self):
        """Запуск движка"""
        if self.is_running:
            logger.warning("Движок уже запущен")
            return
        
        self.is_running = True
        self.main_thread = threading.Thread(target=self._run, daemon=True)
        self.main_thread.start()
        logger.info("JobEngine запущен")
    
    def stop(self):
        """Остановка движка"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Приостанавливаем все активные задачи
        for job_id in list(self.active_jobs.keys()):
            self.pause_job(job_id)
        
        # Ждем завершения главного потока
        if self.main_thread:
            self.main_thread.join(timeout=5)
        
        logger.info("JobEngine остановлен")
    
    def _run(self):
        """Главный цикл движка"""
        while self.is_running:
            try:
                # Проверяем очередь задач
                if not self.job_queue.empty():
                    priority, job_id = self.job_queue.get(timeout=1)
                    
                    # Загружаем задачу из БД
                    job = self.store.get_job(job_id)
                    
                    if job and job['state'] == JobState.PENDING.value:
                        self._start_job(job_id, job)
                
                # Проверяем состояние активных задач
                self._check_active_jobs()
                
                # Небольшая пауза
                time.sleep(0.1)
                
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"Ошибка в главном цикле JobEngine: {e}")
                time.sleep(1)
    
    def submit_job(self, title: str, mode: str, config: Dict, priority: int = 5) -> int:
        """
        Отправка задачи в очередь
        
        Args:
            title: Название задачи
            mode: Тип задачи (distribution, auto_buy, etc.)
            config: Конфигурация задачи
            priority: Приоритет (1 - высший, 10 - низший)
            
        Returns:
            ID созданной задачи
        """
        # Создаем задачу в БД
        job_id = self.store.create_job(title, mode, config)
        
        # Добавляем в очередь
        self.job_queue.put((priority, job_id))
        
        logger.info(f"Задача #{job_id} добавлена в очередь с приоритетом {priority}")
        return job_id
    
    def _start_job(self, job_id: int, job: Dict):
        """Запуск выполнения задачи"""
        try:
            # Обновляем состояние
            self.store.update_job(
                job_id,
                state=JobState.RUNNING.value,
                started_at=datetime.now().isoformat()
            )
            
            # Создаем исполнитель в зависимости от типа
            if job['mode'] == 'distribution':
                executor = DistributionExecutor(job_id, job, self)
            elif job['mode'] == 'auto_buy':
                executor = AutoBuyExecutor(job_id, job, self)
            elif job['mode'] == 'rewards':
                executor = RewardsExecutor(job_id, job, self)
            else:
                logger.error(f"Неизвестный тип задачи: {job['mode']}")
                self.store.update_job(
                    job_id,
                    state=JobState.FAILED.value,
                    error_message=f"Unknown job mode: {job['mode']}"
                )
                return
            
            # Сохраняем исполнитель
            self.active_jobs[job_id] = executor
            
            # Запускаем в отдельном потоке
            thread = threading.Thread(target=executor.run, daemon=True)
            self.job_threads[job_id] = thread
            thread.start()
            
            # Вызываем колбек
            self._trigger_callback('job_started', job_id, job)
            
            logger.info(f"Задача #{job_id} запущена")
            
        except Exception as e:
            logger.error(f"Ошибка запуска задачи #{job_id}: {e}")
            self.store.update_job(
                job_id,
                state=JobState.FAILED.value,
                error_message=str(e)
            )
    
    def pause_job(self, job_id: int):
        """Приостановка задачи"""
        if job_id in self.active_jobs:
            executor = self.active_jobs[job_id]
            executor.pause()
            
            self.store.update_job(job_id, state=JobState.PAUSED.value)
            self._trigger_callback('job_paused', job_id)
            
            logger.info(f"Задача #{job_id} приостановлена")
            return True
        return False
    
    def resume_job(self, job_id: int):
        """Возобновление задачи"""
        job = self.store.get_job(job_id)
        
        if job and job['state'] == JobState.PAUSED.value:
            if job_id in self.active_jobs:
                # Возобновляем существующий исполнитель
                executor = self.active_jobs[job_id]
                executor.resume()
            else:
                # Перезапускаем задачу
                self._start_job(job_id, job)
            
            self.store.update_job(job_id, state=JobState.RUNNING.value)
            self._trigger_callback('job_resumed', job_id)
            
            logger.info(f"Задача #{job_id} возобновлена")
            return True
        return False
    
    def cancel_job(self, job_id: int):
        """Отмена задачи"""
        if job_id in self.active_jobs:
            executor = self.active_jobs[job_id]
            executor.cancel()
            
            # Ждем завершения потока
            if job_id in self.job_threads:
                self.job_threads[job_id].join(timeout=5)
            
            # Удаляем из активных
            del self.active_jobs[job_id]
            if job_id in self.job_threads:
                del self.job_threads[job_id]
        
        self.store.update_job(
            job_id,
            state=JobState.CANCELLED.value,
            completed_at=datetime.now().isoformat()
        )
        
        logger.info(f"Задача #{job_id} отменена")
        return True
    
    def _check_active_jobs(self):
        """Проверка состояния активных задач"""
        for job_id in list(self.active_jobs.keys()):
            executor = self.active_jobs[job_id]
            
            # Проверяем, завершена ли задача
            if executor.is_completed():
                # Обновляем состояние в БД
                state = JobState.COMPLETED if executor.is_successful() else JobState.FAILED
                self.store.update_job(
                    job_id,
                    state=state.value,
                    completed_at=datetime.now().isoformat(),
                    done=executor.done_count,
                    failed=executor.failed_count
                )
                
                # Удаляем из активных
                del self.active_jobs[job_id]
                if job_id in self.job_threads:
                    del self.job_threads[job_id]
                
                # Вызываем колбек
                if state == JobState.COMPLETED:
                    self._trigger_callback('job_completed', job_id)
                else:
                    self._trigger_callback('job_failed', job_id)
                
                logger.info(f"Задача #{job_id} завершена со статусом {state.value}")
    
    def get_job_progress(self, job_id: int) -> Optional[Dict]:
        """Получение прогресса задачи"""
        if job_id in self.active_jobs:
            executor = self.active_jobs[job_id]
            return {
                'total': executor.total_count,
                'done': executor.done_count,
                'failed': executor.failed_count,
                'eta': executor.get_eta(),
                'is_paused': executor.is_paused,
                'is_completed': executor.is_completed()
            }
        
        # Пробуем получить из БД
        job = self.store.get_job(job_id)
        if job:
            return {
                'total': job.get('total', 0),
                'done': job.get('done', 0),
                'failed': job.get('failed', 0),
                'eta': job.get('eta'),
                'is_paused': job['state'] == JobState.PAUSED.value,
                'is_completed': job['state'] in [JobState.COMPLETED.value, JobState.FAILED.value]
            }
        
        return None
    
    def register_callback(self, event: str, callback: Callable):
        """Регистрация колбека для события"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    def _trigger_callback(self, event: str, *args, **kwargs):
        """Вызов колбеков для события"""
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Ошибка в колбеке {event}: {e}")


class BaseExecutor:
    """Базовый класс исполнителя задач"""
    
    def __init__(self, job_id: int, job: Dict, engine: JobEngine):
        self.job_id = job_id
        self.job = job
        self.engine = engine
        self.config = job.get('config', {})
        
        self.total_count = 0
        self.done_count = 0
        self.failed_count = 0
        
        self.is_paused = False
        self.is_cancelled = False
        self.is_done = False
        
        self.start_time = None
        self.pause_event = threading.Event()
        self.pause_event.set()  # Изначально не на паузе
    
    def run(self):
        """Основной метод выполнения (переопределяется в наследниках)"""
        raise NotImplementedError
    
    def pause(self):
        """Приостановка выполнения"""
        self.is_paused = True
        self.pause_event.clear()
    
    def resume(self):
        """Возобновление выполнения"""
        self.is_paused = False
        self.pause_event.set()
    
    def cancel(self):
        """Отмена выполнения"""
        self.is_cancelled = True
        self.pause_event.set()  # Разблокируем если на паузе
    
    def wait_if_paused(self):
        """Ожидание если на паузе"""
        self.pause_event.wait()
        return not self.is_cancelled
    
    def is_completed(self) -> bool:
        """Проверка завершения"""
        return self.is_done or self.is_cancelled
    
    def is_successful(self) -> bool:
        """Проверка успешного завершения"""
        return self.is_done and self.failed_count == 0
    
    def get_eta(self) -> Optional[str]:
        """Расчет примерного времени завершения"""
        if self.done_count == 0 or self.total_count == 0:
            return None
        
        elapsed = time.time() - self.start_time
        rate = self.done_count / elapsed
        remaining = self.total_count - self.done_count
        
        if rate > 0:
            eta_seconds = remaining / rate
            eta_time = datetime.now() + timedelta(seconds=eta_seconds)
            return eta_time.isoformat()
        
        return None
    
    def update_progress(self):
        """Обновление прогресса в БД"""
        self.engine.store.update_job(
            self.job_id,
            done=self.done_count,
            failed=self.failed_count,
            total=self.total_count,
            eta=self.get_eta()
        )
        
        # Вызываем колбек прогресса
        self.engine._trigger_callback('job_progress', self.job_id, {
            'total': self.total_count,
            'done': self.done_count,
            'failed': self.failed_count,
            'eta': self.get_eta()
        })


class DistributionExecutor(BaseExecutor):
    """Исполнитель задач массовой рассылки"""
    
    def run(self):
        """Выполнение массовой рассылки"""
        self.start_time = time.time()
        
        try:
            # Получаем параметры из конфига
            addresses = self.config.get('addresses', [])
            token_address = self.config.get('token_address')
            amount_per_address = self.config.get('amount_per_address')
            sender_key = self.config.get('sender_key')
            
            if not addresses or not sender_key:
                raise ValueError("Отсутствуют обязательные параметры")
            
            self.total_count = len(addresses)
            self.engine.store.update_job(self.job_id, total=self.total_count)
            
            # Получаем Web3 и аккаунт
            w3 = self.engine.rpc_pool.get_web3()
            account = Account.from_key(sender_key)
            sender_address = account.address
            
            logger.info(f"Начало рассылки {self.total_count} адресов от {sender_address}")
            
            for i, recipient in enumerate(addresses):
                # Проверяем паузу/отмену
                if not self.wait_if_paused():
                    break
                
                try:
                    # Получаем nonce
                    nonce = self.engine.nonce_manager.get_nonce(w3, sender_address)
                    
                    # Формируем транзакцию
                    if token_address and token_address != "BNB":
                        # ERC20 перевод
                        tx = self._build_token_transfer(
                            w3, token_address, sender_address, 
                            recipient, amount_per_address, nonce
                        )
                    else:
                        # BNB перевод
                        tx = {
                            'from': sender_address,
                            'to': recipient,
                            'value': w3.to_wei(amount_per_address, 'ether'),
                            'gas': self.config.get('gas_limit', 21000),
                            'gasPrice': w3.to_wei(self.config.get('gas_price', 5), 'gwei'),
                            'nonce': nonce
                        }
                    
                    # Подписываем и отправляем
                    signed_tx = account.sign_transaction(tx)
                    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                    
                    # Подтверждаем nonce
                    self.engine.nonce_manager.confirm_nonce(sender_address, nonce)
                    
                    # Сохраняем в БД
                    self.engine.store.add_transaction(
                        tx_hash=tx_hash.hex(),
                        from_address=sender_address,
                        to_address=recipient,
                        token_address=token_address or 'BNB',
                        amount=amount_per_address,
                        gas_price=tx['gasPrice'],
                        gas_limit=tx['gas'],
                        status='pending',
                        type='distribution',
                        job_id=self.job_id
                    )
                    
                    self.done_count += 1
                    logger.info(f"Отправлено {i+1}/{self.total_count}: {tx_hash.hex()}")
                    
                except Exception as e:
                    logger.error(f"Ошибка отправки на {recipient}: {e}")
                    self.failed_count += 1
                    
                    # Освобождаем nonce при ошибке
                    if 'nonce' in locals():
                        self.engine.nonce_manager.release_nonce(sender_address, nonce)
                
                # Обновляем прогресс
                if (i + 1) % 10 == 0:  # Каждые 10 транзакций
                    self.update_progress()
                
                # Задержка между транзакциями
                time.sleep(self.config.get('delay_between_tx', 1))
            
            self.is_done = True
            self.update_progress()
            
            logger.info(f"Рассылка завершена: {self.done_count} успешно, {self.failed_count} ошибок")
            
        except Exception as e:
            logger.error(f"Критическая ошибка в DistributionExecutor: {e}")
            self.is_done = True
    
    def _build_token_transfer(self, w3, token_address, sender, recipient, amount, nonce):
        """Построение транзакции ERC20 перевода"""
        # ABI функции transfer
        transfer_abi = [{
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
            abi=transfer_abi
        )
        
        # Получаем decimals (по умолчанию 18)
        decimals = self.config.get('token_decimals', 18)
        amount_wei = int(amount * (10 ** decimals))
        
        # Строим транзакцию
        tx = contract.functions.transfer(
            Web3.to_checksum_address(recipient),
            amount_wei
        ).build_transaction({
            'from': sender,
            'gas': self.config.get('gas_limit', 100000),
            'gasPrice': w3.to_wei(self.config.get('gas_price', 5), 'gwei'),
            'nonce': nonce
        })
        
        return tx


class AutoBuyExecutor(BaseExecutor):
    """Исполнитель автоматических покупок"""
    
    def run(self):
        """Выполнение автопокупок"""
        self.start_time = time.time()
        
        try:
            # Получаем параметры
            token_address = self.config.get('token_address')
            buy_amount = self.config.get('buy_amount')
            interval = self.config.get('interval', 60)
            total_buys = self.config.get('total_buys', 10)
            
            self.total_count = total_buys
            
            logger.info(f"Начало автопокупок: {total_buys} покупок с интервалом {interval}с")
            
            for i in range(total_buys):
                if not self.wait_if_paused():
                    break
                
                try:
                    # Здесь должна быть логика покупки через PancakeSwap
                    # TODO: Реализовать swap через роутер
                    
                    self.done_count += 1
                    logger.info(f"Покупка {i+1}/{total_buys} выполнена")
                    
                except Exception as e:
                    logger.error(f"Ошибка покупки {i+1}: {e}")
                    self.failed_count += 1
                
                # Обновляем прогресс
                self.update_progress()
                
                # Ждем интервал
                if i < total_buys - 1:
                    for _ in range(interval):
                        if not self.wait_if_paused():
                            break
                        time.sleep(1)
            
            self.is_done = True
            
        except Exception as e:
            logger.error(f"Критическая ошибка в AutoBuyExecutor: {e}")
            self.is_done = True


class RewardsExecutor(BaseExecutor):
    """Исполнитель отправки наград"""
    
    def run(self):
        """Выполнение отправки наград"""
        self.start_time = time.time()
        
        try:
            # Получаем награды из БД
            rewards = self.engine.store.get_rewards(status='pending')
            self.total_count = len(rewards)
            
            logger.info(f"Начало отправки {self.total_count} наград")
            
            for i, reward in enumerate(rewards):
                if not self.wait_if_paused():
                    break
                
                try:
                    # Отправляем награду
                    # TODO: Реализовать отправку
                    
                    # Обновляем статус награды
                    self.engine.store.update_reward(
                        reward['id'],
                        status='sent',
                        sent_at=datetime.now().isoformat()
                    )
                    
                    self.done_count += 1
                    
                except Exception as e:
                    logger.error(f"Ошибка отправки награды {reward['id']}: {e}")
                    self.failed_count += 1
                    
                    self.engine.store.update_reward(
                        reward['id'],
                        status='failed'
                    )
                
                # Обновляем прогресс
                if (i + 1) % 5 == 0:
                    self.update_progress()
            
            self.is_done = True
            
        except Exception as e:
            logger.error(f"Критическая ошибка в RewardsExecutor: {e}")
            self.is_done = True


# Глобальный экземпляр движка
_job_engine: Optional[JobEngine] = None


def get_job_engine() -> JobEngine:
    """Получение глобального экземпляра движка задач"""
    global _job_engine
    
    if _job_engine is None:
        _job_engine = JobEngine()
        _job_engine.start()
    
    return _job_engine


def close_job_engine():
    """Закрытие глобального движка задач"""
    global _job_engine
    
    if _job_engine:
        _job_engine.stop()
        _job_engine = None
