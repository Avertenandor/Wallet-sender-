"""
Движок выполнения задач с управлением очередью и nonce
"""

import time
import threading
import queue
import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from web3 import Web3
from eth_account import Account

from .store import get_store
from .rpc import get_rpc_pool
from .nonce_manager import NonceManager, get_nonce_manager
from ..utils.logger import get_logger
from ..config import get_config
from ..constants import ERC20_ABI

logger = get_logger(__name__)


class JobState(Enum):
    """Состояния задачи"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobEngine:
    """Движок выполнения задач"""
    
    def __init__(self):
        """Инициализация движка"""
        self.store = get_store()
        self.rpc_pool = get_rpc_pool()
        self.config = get_config()
        self.nonce_manager = get_nonce_manager()  # Используем глобальный экземпляр
        
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
            elif job['mode'] == 'auto_sell':
                executor = AutoSellExecutor(job_id, job, self)
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
                    # Устанавливаем web3 в nonce manager если нужно
                    if not self.engine.nonce_manager.web3:
                        self.engine.nonce_manager.set_web3(w3)
                    
                    # Резервируем nonce
                    ticket = self.engine.nonce_manager.reserve(sender_address)
                    nonce = ticket.nonce
                    
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
                    
                    # Подтверждаем использование nonce
                    self.engine.nonce_manager.complete(ticket, tx_hash.hex())
                    
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
                    
                    # Отмечаем неудачу использования nonce
                    if 'ticket' in locals():
                        self.engine.nonce_manager.fail(ticket, str(e))
                
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


class AutoSellExecutor(BaseExecutor):
    """Исполнитель автопродаж токенов"""
    
    def run(self):
        """Выполнение автопродаж"""
        self.start_time = time.time()
        
        try:
            # Получаем параметры из конфигурации
            token_address = self.config.get('token_address')
            sell_percentage = self.config.get('sell_percentage', 100)  # % от баланса для продажи
            interval = self.config.get('interval', 60)  # Интервал между продажами в секундах
            total_sells = self.config.get('total_sells', 1)  # Количество продаж
            seller_keys = self.config.get('seller_keys', [])  # Список приватных ключей
            slippage = self.config.get('slippage', 5)  # Проскальзывание в %
            target_token = self.config.get('target_token', 'BNB')  # Во что продавать (BNB/USDT)
            
            # Проверяем обязательные параметры
            if not token_address:
                raise ValueError("Не указан адрес токена для продажи")
            if not seller_keys:
                raise ValueError("Не указаны ключи продавцов")
            
            self.total_count = total_sells * len(seller_keys)
            
            logger.info(f"Начало автопродаж: {total_sells} продаж на {len(seller_keys)} кошельках")
            logger.info(f"Токен: {token_address}, цель: {target_token}, проскальзывание: {slippage}%")
            
            # Адреса контрактов BSC (checksum format)
            WBNB_ADDRESS = Web3.to_checksum_address("0xbb4CdB9CBd36B01bD1cBaEF95b79eFD60Bb44cB")
            USDT_ADDRESS = Web3.to_checksum_address("0x55d398326f99059fF775485246999027B3197955")  # BSC USDT
            PANCAKE_ROUTER = Web3.to_checksum_address("0x10ED43C718714eb63d5aA57B78B54704E256024E")  # PancakeSwap V2
            
            # Выполняем продажи
            for sell_num in range(total_sells):
                for seller_idx, seller_key in enumerate(seller_keys):
                    if not self.wait_if_paused():
                        return
                    
                    try:
                        # Получаем Web3 и создаем аккаунт
                        w3 = self.engine.rpc_pool.get_client()
                        if not w3:
                            raise Exception("Не удалось получить Web3 соединение")
                        
                        account = Account.from_key(seller_key)
                        seller_address = account.address
                        
                        logger.info(f"Продажа {sell_num+1}/{total_sells} для {seller_address[:10]}...")
                        
                        # Получаем баланс токена
                        token_contract = w3.eth.contract(
                            address=Web3.to_checksum_address(token_address), 
                            abi=ERC20_ABI
                        )
                        token_balance = token_contract.functions.balanceOf(seller_address).call()
                        
                        if token_balance == 0:
                            logger.warning(f"Нулевой баланс токена у {seller_address[:10]}")
                            self.failed_count += 1
                            continue
                        
                        # Вычисляем количество для продажи
                        amount_to_sell = int(token_balance * sell_percentage / 100)
                        if amount_to_sell == 0:
                            logger.warning(f"Недостаточно токенов для продажи у {seller_address[:10]}")
                            self.failed_count += 1
                            continue
                        
                        # Определяем путь обмена
                        if target_token.upper() == 'BNB':
                            path = [token_address, WBNB_ADDRESS]
                        elif target_token.upper() == 'USDT':
                            path = [token_address, WBNB_ADDRESS, USDT_ADDRESS]
                        else:
                            raise ValueError(f"Неподдерживаемый токен назначения: {target_token}")
                        
                        # Получаем ожидаемое количество выхода
                        try:
                            router_contract = w3.eth.contract(address=PANCAKE_ROUTER, abi=[
                                {"name": "getAmountsOut", "type": "function", "stateMutability": "view",
                                 "inputs": [
                                     {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                                     {"internalType": "address[]", "name": "path", "type": "address[]"}
                                 ], "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}]}
                            ])
                            amounts_out = router_contract.functions.getAmountsOut(amount_to_sell, path).call()
                            expected_out = amounts_out[-1]
                            
                            # Применяем проскальзывание
                            min_out = int(expected_out * (100 - slippage) / 100)
                        except Exception as e:
                            logger.warning(f"Не удалось рассчитать amountOutMin, используем 0: {e}")
                            min_out = 0
                        
                        # Резервируем nonce
                        ticket = self.engine.nonce_manager.reserve(seller_address)
                        nonce = ticket.nonce
                        
                        # Проверяем allowance для роутера
                        allowance = token_contract.functions.allowance(seller_address, PANCAKE_ROUTER).call()
                        
                        if allowance < amount_to_sell:
                            # Нужен approve
                            logger.info(f"Выполняем approve для {seller_address[:10]}...")
                            
                            approve_tx = token_contract.functions.approve(
                                PANCAKE_ROUTER, 
                                amount_to_sell
                            ).build_transaction({
                                'from': seller_address,
                                'nonce': nonce,
                                'gas': 60000,
                                'gasPrice': w3.to_wei(5, 'gwei')
                            })
                            
                            # Подписываем и отправляем approve
                            signed_approve = account.sign_transaction(approve_tx)
                            approve_hash = w3.eth.send_raw_transaction(signed_approve.rawTransaction)
                            
                            # Ждем подтверждения approve
                            approve_receipt = w3.eth.wait_for_transaction_receipt(approve_hash, timeout=60)
                            if approve_receipt['status'] != 1:
                                raise Exception("Approve транзакция не удалась")
                            
                            # Обновляем nonce для swap транзакции
                            self.engine.nonce_manager.complete(ticket, approve_hash.hex())
                            ticket = self.engine.nonce_manager.reserve(seller_address)
                            nonce = ticket.nonce
                        
                        # Подготавливаем swap транзакцию
                        router_abi = [
                            {"name": "swapExactTokensForETH" if target_token.upper() == 'BNB' else "swapExactTokensForTokens",
                             "type": "function", "stateMutability": "nonpayable",
                             "inputs": [
                                 {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                                 {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                                 {"internalType": "address[]", "name": "path", "type": "address[]"},
                                 {"internalType": "address", "name": "to", "type": "address"},
                                 {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                             ], "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}]}
                        ]
                        
                        swap_contract = w3.eth.contract(address=PANCAKE_ROUTER, abi=router_abi)
                        
                        # Deadline через 10 минут
                        deadline = int(time.time()) + 600
                        
                        if target_token.upper() == 'BNB':
                            swap_function = swap_contract.functions.swapExactTokensForETH(
                                amount_to_sell,
                                min_out,
                                path,
                                seller_address,
                                deadline
                            )
                        else:
                            swap_function = swap_contract.functions.swapExactTokensForTokens(
                                amount_to_sell,
                                min_out,
                                path,
                                seller_address,
                                deadline
                            )
                        
                        # Создаем swap транзакцию
                        swap_tx = swap_function.build_transaction({
                            'from': seller_address,
                            'nonce': nonce,
                            'gas': 300000,
                            'gasPrice': w3.to_wei(5, 'gwei')
                        })
                        
                        # Подписываем и отправляем swap
                        signed_swap = account.sign_transaction(swap_tx)
                        tx_hash = w3.eth.send_raw_transaction(signed_swap.rawTransaction)
                        
                        # Подтверждаем использование nonce
                        self.engine.nonce_manager.complete(ticket, tx_hash.hex())
                        
                        # Сохраняем транзакцию в БД
                        self.engine.store.add_transaction(
                            tx_hash=tx_hash.hex(),
                            from_address=seller_address,
                            to_address=PANCAKE_ROUTER,
                            token_address=Web3.to_checksum_address(token_address),
                            amount=amount_to_sell / (10 ** 18),  # Конвертируем в читаемый формат
                            gas_price=swap_tx.get('gasPrice', 0),
                            gas_limit=swap_tx.get('gas', 0),
                            status='pending',
                            type='sell',
                            job_id=self.job_id
                        )
                        
                        self.done_count += 1
                        logger.info(f"Продажа выполнена: {tx_hash.hex()[:10]}... для {seller_address[:10]}...")
                        
                    except Exception as e:
                        logger.error(f"Ошибка продажи для {seller_address[:10] if 'seller_address' in locals() else 'unknown'}: {e}")
                        self.failed_count += 1
                        
                        # Отмечаем неудачу использования nonce
                        if 'ticket' in locals():
                            self.engine.nonce_manager.fail(ticket, str(e))
                    
                    # Обновляем прогресс
                    self.update_progress()
                    
                    # Задержка между продажами разных кошельков
                    if seller_idx < len(seller_keys) - 1:
                        time.sleep(2)
                
                # Ждем интервал между циклами продаж
                if sell_num < total_sells - 1:
                    logger.info(f"Ожидание {interval} секунд до следующего цикла...")
                    for _ in range(interval):
                        if not self.wait_if_paused():
                            return
                        time.sleep(1)
            
            self.is_done = True
            
        except Exception as e:
            logger.error(f"Критическая ошибка в AutoSellExecutor: {e}")
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
