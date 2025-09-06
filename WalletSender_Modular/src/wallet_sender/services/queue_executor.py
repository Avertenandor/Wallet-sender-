"""
Фоновый исполнитель задач очереди
"""

import threading
import time
from typing import Optional, Dict, Any
from datetime import datetime

from ..database.database import Database
from ..database.models import DistributionTask, DistributionAddress, Transaction
from ..core.web3_provider import Web3Provider
from ..core.wallet_manager import WalletManager
from ..services.token_service import TokenService
from ..config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class QueueExecutor:
    """Класс для фонового выполнения задач из очереди"""
    
    def __init__(self, wallet_manager: WalletManager = None):
        """
        Инициализация исполнителя
        
        Args:
            wallet_manager: Менеджер кошелька (опционально)
        """
        self.config = Config()
        self.db = Database()
        self.web3_provider = Web3Provider()
        
        # Менеджер кошелька
        self.wallet_manager = wallet_manager or WalletManager()
        
        # Сервис токенов
        self.token_service = TokenService(self.web3_provider)
        
        # Потоки и флаги
        self.worker_threads = []
        self.stop_flag = threading.Event()
        self.pause_flag = threading.Event()
        self.is_running = False
        
        # Параметры
        self.worker_count = 1  # Количество воркеров
        self.check_interval = 5  # Интервал проверки новых задач (сек)
        self.send_interval = 2  # Интервал между отправками (сек)
        
    def start(self, worker_count: int = 1):
        """
        Запуск исполнителя
        
        Args:
            worker_count: Количество воркеров (1-3)
        """
        if self.is_running:
            logger.warning("Исполнитель уже запущен")
            return
            
        if not self.wallet_manager.is_connected():
            logger.error("Кошелек не подключен")
            return
            
        self.worker_count = min(max(worker_count, 1), 3)
        self.stop_flag.clear()
        self.is_running = True
        
        # Запускаем воркеры
        for i in range(self.worker_count):
            thread = threading.Thread(
                target=self._worker_loop,
                args=(i,),
                daemon=True,
                name=f"QueueWorker-{i}"
            )
            thread.start()
            self.worker_threads.append(thread)
            
        logger.info(f"Исполнитель запущен с {self.worker_count} воркерами")
        
    def stop(self):
        """Остановка исполнителя"""
        if not self.is_running:
            return
            
        logger.info("Остановка исполнителя...")
        self.stop_flag.set()
        
        # Ждем завершения потоков
        for thread in self.worker_threads:
            thread.join(timeout=10)
            
        self.worker_threads.clear()
        self.is_running = False
        logger.info("Исполнитель остановлен")
        
    def pause(self):
        """Приостановка исполнителя"""
        self.pause_flag.set()
        logger.info("Исполнитель приостановлен")
        
    def resume(self):
        """Возобновление исполнителя"""
        self.pause_flag.clear()
        logger.info("Исполнитель возобновлен")
        
    def _worker_loop(self, worker_id: int):
        """
        Основной цикл воркера
        
        Args:
            worker_id: ID воркера
        """
        logger.info(f"Воркер {worker_id} запущен")
        
        while not self.stop_flag.is_set():
            try:
                # Проверка паузы
                if self.pause_flag.is_set():
                    time.sleep(1)
                    continue
                    
                # Получаем задачу для обработки
                task = self._get_next_task()
                
                if task:
                    logger.info(f"Воркер {worker_id} обрабатывает задачу #{task.id}")
                    self._process_task(task)
                else:
                    # Нет задач, ждем
                    time.sleep(self.check_interval)
                    
            except Exception as e:
                logger.error(f"Ошибка в воркере {worker_id}: {e}")
                time.sleep(5)
                
        logger.info(f"Воркер {worker_id} завершен")
        
    def _get_next_task(self) -> Optional[DistributionTask]:
        """
        Получение следующей задачи для обработки
        
        Returns:
            DistributionTask или None
        """
        try:
            with self.db as session:
                # Ищем задачу со статусом pending или running
                task = session.query(DistributionTask).filter(
                    DistributionTask.status.in_(['pending', 'running'])
                ).first()
                
                if task:
                    # Помечаем как running
                    if task.status == 'pending':
                        task.status = 'running'
                        task.started_at = datetime.utcnow()
                        
                    return task
                    
        except Exception as e:
            logger.error(f"Ошибка получения задачи: {e}")
            
        return None
        
    def _process_task(self, task: DistributionTask):
        """
        Обработка задачи рассылки
        
        Args:
            task: Задача для обработки
        """
        try:
            # Получаем приватный ключ
            private_key = self.wallet_manager.get_private_key()
            if not private_key:
                logger.error("Не удалось получить приватный ключ")
                self._mark_task_failed(task.id, "Нет приватного ключа")
                return
                
            # Обрабатываем адреса
            while not self.stop_flag.is_set():
                # Проверка паузы
                if self.pause_flag.is_set():
                    self._mark_task_paused(task.id)
                    return
                    
                # Получаем следующий адрес для обработки
                address = self._get_next_address(task.id)
                
                if not address:
                    # Все адреса обработаны
                    self._mark_task_completed(task.id)
                    break
                    
                # Отправляем токены
                result = self._send_tokens(
                    address,
                    task.token_address,
                    task.token_symbol,
                    task.amount_per_address,
                    private_key
                )
                
                # Обновляем статус адреса
                self._update_address_status(
                    address.id,
                    'sent' if result['success'] else 'failed',
                    result.get('tx_hash'),
                    result.get('error')
                )
                
                # Обновляем счетчики задачи
                self._update_task_counters(
                    task.id,
                    success=result['success']
                )
                
                # Пауза между отправками
                if not self.stop_flag.is_set():
                    time.sleep(self.send_interval)
                    
        except Exception as e:
            logger.error(f"Ошибка обработки задачи #{task.id}: {e}")
            self._mark_task_failed(task.id, str(e))
            
    def _get_next_address(self, task_id: int) -> Optional[DistributionAddress]:
        """
        Получение следующего адреса для обработки
        
        Args:
            task_id: ID задачи
            
        Returns:
            DistributionAddress или None
        """
        try:
            with self.db as session:
                address = session.query(DistributionAddress).filter(
                    DistributionAddress.task_id == task_id,
                    DistributionAddress.status == 'pending'
                ).first()
                
                if address:
                    # Помечаем как обрабатываемый
                    address.status = 'processing'
                    address.processed_at = datetime.utcnow()
                    
                return address
                
        except Exception as e:
            logger.error(f"Ошибка получения адреса: {e}")
            
        return None
        
    def _send_tokens(
        self,
        address: DistributionAddress,
        token_address: str,
        token_symbol: str,
        amount: float,
        private_key: str
    ) -> Dict[str, Any]:
        """
        Отправка токенов на адрес
        
        Args:
            address: Объект адреса
            token_address: Адрес контракта токена
            token_symbol: Символ токена
            amount: Сумма для отправки
            private_key: Приватный ключ
            
        Returns:
            Dict с результатом отправки
        """
        try:
            # Параметры газа из конфига
            gas_price = self.config.get('gas_settings.default_gas_price', 5) * 10**9
            gas_limit = self.config.get('gas_settings.default_gas_limit', 100000)
            
            # Отправляем через TokenService
            result = self.token_service.transfer(
                token_address=token_address,
                to_address=address.address,
                amount=amount,
                private_key=private_key,
                gas_price=gas_price,
                gas_limit=gas_limit,
                retry_count=2
            )
            
            if result['success']:
                logger.info(
                    f"✅ Отправлено {amount} {token_symbol} на {address.address[:10]}... "
                    f"TX: {result['tx_hash'][:10]}..."
                )
                
                # Сохраняем транзакцию в БД
                self._save_transaction(
                    tx_hash=result['tx_hash'],
                    from_address=self.wallet_manager.get_address(),
                    to_address=address.address,
                    token_address=token_address,
                    token_symbol=token_symbol,
                    amount=amount,
                    tx_type='distribution'
                )
            else:
                logger.error(
                    f"❌ Ошибка отправки на {address.address[:10]}...: "
                    f"{result.get('error', 'Unknown')}"
                )
                
            return result
            
        except Exception as e:
            logger.error(f"Ошибка отправки токенов: {e}")
            return {'success': False, 'error': str(e)}
            
    def _save_transaction(
        self,
        tx_hash: str,
        from_address: str,
        to_address: str,
        token_address: str,
        token_symbol: str,
        amount: float,
        tx_type: str = 'distribution'
    ):
        """Сохранение транзакции в БД"""
        try:
            with self.db as session:
                transaction = Transaction(
                    tx_hash=tx_hash,
                    from_address=from_address,
                    to_address=to_address,
                    token_address=token_address,
                    token_symbol=token_symbol,
                    amount=amount,
                    type=tx_type,
                    status='success',
                    created_at=datetime.utcnow()
                )
                session.add(transaction)
                
        except Exception as e:
            logger.error(f"Ошибка сохранения транзакции: {e}")
            
    def _update_address_status(
        self,
        address_id: int,
        status: str,
        tx_hash: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Обновление статуса адреса"""
        try:
            with self.db as session:
                address = session.query(DistributionAddress).filter_by(
                    id=address_id
                ).first()
                
                if address:
                    address.status = status
                    address.tx_hash = tx_hash
                    address.error_message = error
                    address.processed_at = datetime.utcnow()
                    
        except Exception as e:
            logger.error(f"Ошибка обновления статуса адреса: {e}")
            
    def _update_task_counters(self, task_id: int, success: bool):
        """Обновление счетчиков задачи"""
        try:
            with self.db as session:
                task = session.query(DistributionTask).filter_by(id=task_id).first()
                
                if task:
                    task.processed_addresses = (task.processed_addresses or 0) + 1
                    
                    if success:
                        task.successful_sends = (task.successful_sends or 0) + 1
                    else:
                        task.failed_sends = (task.failed_sends or 0) + 1
                        
        except Exception as e:
            logger.error(f"Ошибка обновления счетчиков: {e}")
            
    def _mark_task_completed(self, task_id: int):
        """Пометка задачи как завершенной"""
        try:
            with self.db as session:
                task = session.query(DistributionTask).filter_by(id=task_id).first()
                
                if task:
                    task.status = 'completed'
                    task.completed_at = datetime.utcnow()
                    logger.info(f"Задача #{task_id} завершена")
                    
        except Exception as e:
            logger.error(f"Ошибка завершения задачи: {e}")
            
    def _mark_task_failed(self, task_id: int, error: str):
        """Пометка задачи как неудачной"""
        try:
            with self.db as session:
                task = session.query(DistributionTask).filter_by(id=task_id).first()
                
                if task:
                    task.status = 'failed'
                    task.completed_at = datetime.utcnow()
                    logger.error(f"Задача #{task_id} завершена с ошибкой: {error}")
                    
        except Exception as e:
            logger.error(f"Ошибка пометки задачи как неудачной: {e}")
            
    def _mark_task_paused(self, task_id: int):
        """Пометка задачи как приостановленной"""
        try:
            with self.db as session:
                task = session.query(DistributionTask).filter_by(id=task_id).first()
                
                if task:
                    task.status = 'paused'
                    logger.info(f"Задача #{task_id} приостановлена")
                    
        except Exception as e:
            logger.error(f"Ошибка приостановки задачи: {e}")
            
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса исполнителя
        
        Returns:
            Dict со статусом
        """
        return {
            'is_running': self.is_running,
            'is_paused': self.pause_flag.is_set(),
            'worker_count': len(self.worker_threads),
            'active_workers': sum(1 for t in self.worker_threads if t.is_alive())
        }


# Глобальный экземпляр исполнителя
_executor_instance: Optional[QueueExecutor] = None


def get_executor() -> QueueExecutor:
    """Получение глобального экземпляра исполнителя"""
    global _executor_instance
    
    if _executor_instance is None:
        _executor_instance = QueueExecutor()
        
    return _executor_instance


def start_executor(wallet_manager: WalletManager = None, worker_count: int = 1):
    """Запуск глобального исполнителя"""
    executor = get_executor()
    
    if wallet_manager:
        executor.wallet_manager = wallet_manager
        
    executor.start(worker_count)
    

def stop_executor():
    """Остановка глобального исполнителя"""
    global _executor_instance
    
    if _executor_instance:
        _executor_instance.stop()
        _executor_instance = None
