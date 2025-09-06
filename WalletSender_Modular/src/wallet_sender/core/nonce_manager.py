"""
NonceManager для предотвращения коллизий при параллельной отправке транзакций
"""

import time
import threading
from typing import Dict, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from web3 import Web3
from collections import deque

logger = logging.getLogger(__name__)


class NonceStatus(Enum):
    """Статус nonce"""
    RESERVED = "reserved"     # Зарезервирован, но не использован
    PENDING = "pending"       # Транзакция отправлена
    CONFIRMED = "confirmed"   # Транзакция подтверждена
    FAILED = "failed"        # Транзакция отклонена
    EXPIRED = "expired"      # Истек срок резервирования


@dataclass
class NonceTicket:
    """Ticket для зарезервированного nonce"""
    id: str
    address: str
    nonce: int
    status: NonceStatus
    reserved_at: datetime
    tx_hash: Optional[str] = None
    error: Optional[str] = None
    
    def is_expired(self, timeout_seconds: int = 60) -> bool:
        """Проверка истечения срока резервирования"""
        elapsed = (datetime.now() - self.reserved_at).total_seconds()
        return elapsed > timeout_seconds


@dataclass
class AddressNonceState:
    """Состояние nonce для адреса"""
    address: str
    network_nonce: int  # Последний известный nonce из сети
    next_nonce: int     # Следующий nonce для выдачи
    last_sync: datetime
    pending_nonces: Set[int] = field(default_factory=set)
    failed_nonces: Set[int] = field(default_factory=set)
    confirmed_nonces: Set[int] = field(default_factory=set)
    tickets: Dict[str, NonceTicket] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)
    
    def needs_resync(self, max_age_seconds: int = 30) -> bool:
        """Проверка необходимости ресинхронизации"""
        age = (datetime.now() - self.last_sync).total_seconds()
        return age > max_age_seconds


class NonceManager:
    """Улучшенный менеджер nonce с поддержкой резервирования и восстановления"""
    
    def __init__(self, web3: Optional[Web3] = None):
        """
        Args:
            web3: Web3 экземпляр (может быть установлен позже)
        """
        self.web3 = web3
        self.states: Dict[str, AddressNonceState] = {}
        self.global_lock = threading.Lock()
        
        # Конфигурация
        self.reservation_timeout = 60  # Таймаут резервирования в секундах
        self.resync_interval = 30      # Интервал ресинхронизации
        self.max_pending_per_address = 20  # Максимум pending транзакций
        
        # Счетчики для статистики
        self.total_reserved = 0
        self.total_confirmed = 0
        self.total_failed = 0
        self.resync_count = 0
        
        # История для отладки
        self.history = deque(maxlen=1000)
        
        # Фоновый поток для очистки
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        self.is_running = True
    
    def set_web3(self, web3: Web3):
        """Установка Web3 экземпляра"""
        self.web3 = web3
    
    def _get_or_create_state(self, address: str) -> AddressNonceState:
        """Получение или создание состояния для адреса"""
        address = Web3.to_checksum_address(address)
        
        with self.global_lock:
            if address not in self.states:
                # Создаем новое состояние
                network_nonce = self._fetch_network_nonce(address)
                self.states[address] = AddressNonceState(
                    address=address,
                    network_nonce=network_nonce,
                    next_nonce=network_nonce,
                    last_sync=datetime.now()
                )
                logger.info(f"Created nonce state for {address}: starting nonce={network_nonce}")
            
            return self.states[address]
    
    def _fetch_network_nonce(self, address: str) -> int:
        """Получение текущего nonce из сети"""
        if not self.web3:
            raise ValueError("Web3 not configured")
        
        try:
            # Используем 'pending' для учета неподтвержденных транзакций
            nonce = self.web3.eth.get_transaction_count(address, 'pending')
            return nonce
        except Exception as e:
            logger.error(f"Failed to fetch network nonce for {address}: {e}")
            raise
    
    def reserve(self, address: str) -> NonceTicket:
        """
        Резервирование nonce для адреса
        
        Args:
            address: Адрес отправителя
            
        Returns:
            NonceTicket с зарезервированным nonce
            
        Raises:
            ValueError: Если достигнут лимит pending транзакций
        """
        address = Web3.to_checksum_address(address)
        state = self._get_or_create_state(address)
        
        with state.lock:
            # Проверяем необходимость ресинхронизации
            if state.needs_resync(self.resync_interval):
                self._resync_state(state)
            
            # Проверяем лимит pending транзакций
            if len(state.pending_nonces) >= self.max_pending_per_address:
                raise ValueError(f"Too many pending transactions ({len(state.pending_nonces)}) for {address}")
            
            # Получаем nonce для резервирования
            nonce = state.next_nonce
            
            # Создаем ticket
            ticket_id = f"{address}_{nonce}_{int(time.time() * 1000)}"
            ticket = NonceTicket(
                id=ticket_id,
                address=address,
                nonce=nonce,
                status=NonceStatus.RESERVED,
                reserved_at=datetime.now()
            )
            
            # Обновляем состояние
            state.next_nonce += 1
            state.pending_nonces.add(nonce)
            state.tickets[ticket_id] = ticket
            
            # Обновляем статистику
            self.total_reserved += 1
            
            # Добавляем в историю
            self._add_to_history('reserve', address, nonce, ticket_id)
            
            logger.debug(f"Reserved nonce {nonce} for {address} (ticket: {ticket_id})")
            return ticket
    
    def complete(self, ticket: NonceTicket, tx_hash: str):
        """
        Подтверждение использования nonce
        
        Args:
            ticket: Ticket с зарезервированным nonce
            tx_hash: Хеш отправленной транзакции
        """
        state = self._get_or_create_state(ticket.address)
        
        with state.lock:
            if ticket.id not in state.tickets:
                logger.warning(f"Ticket {ticket.id} not found")
                return
            
            # Обновляем ticket
            ticket.status = NonceStatus.PENDING
            ticket.tx_hash = tx_hash
            state.tickets[ticket.id] = ticket
            
            # Добавляем в историю
            self._add_to_history('complete', ticket.address, ticket.nonce, ticket.id, tx_hash)
            
            logger.debug(f"Completed nonce {ticket.nonce} for {ticket.address} with tx {tx_hash}")
    
    def confirm(self, ticket: NonceTicket):
        """
        Подтверждение транзакции (после майнинга)
        
        Args:
            ticket: Ticket с использованным nonce
        """
        state = self._get_or_create_state(ticket.address)
        
        with state.lock:
            if ticket.id not in state.tickets:
                logger.warning(f"Ticket {ticket.id} not found")
                return
            
            # Обновляем статус
            ticket.status = NonceStatus.CONFIRMED
            state.tickets[ticket.id] = ticket
            
            # Перемещаем из pending в confirmed
            if ticket.nonce in state.pending_nonces:
                state.pending_nonces.remove(ticket.nonce)
            state.confirmed_nonces.add(ticket.nonce)
            
            # Обновляем статистику
            self.total_confirmed += 1
            
            # Добавляем в историю
            self._add_to_history('confirm', ticket.address, ticket.nonce, ticket.id)
            
            logger.debug(f"Confirmed nonce {ticket.nonce} for {ticket.address}")
    
    def fail(self, ticket: NonceTicket, reason: str):
        """
        Отметка неудачи использования nonce
        
        Args:
            ticket: Ticket с зарезервированным nonce
            reason: Причина неудачи
        """
        state = self._get_or_create_state(ticket.address)
        
        with state.lock:
            if ticket.id not in state.tickets:
                logger.warning(f"Ticket {ticket.id} not found")
                return
            
            # Обновляем ticket
            ticket.status = NonceStatus.FAILED
            ticket.error = reason
            state.tickets[ticket.id] = ticket
            
            # Обрабатываем в зависимости от причины
            if 'nonce too low' in reason.lower():
                # Nonce уже использован, нужна ресинхронизация
                logger.warning(f"Nonce too low for {ticket.address}, resyncing...")
                self._resync_state(state)
                
            elif 'nonce too high' in reason.lower():
                # Есть пропущенные nonce
                logger.warning(f"Nonce too high for {ticket.address}, possible gap")
                # Откатываем next_nonce если это был последний
                if state.next_nonce == ticket.nonce + 1:
                    state.next_nonce = ticket.nonce
                    logger.info(f"Rolled back next_nonce to {ticket.nonce} for {ticket.address}")
            
            # Перемещаем в failed
            if ticket.nonce in state.pending_nonces:
                state.pending_nonces.remove(ticket.nonce)
            state.failed_nonces.add(ticket.nonce)
            
            # Обновляем статистику
            self.total_failed += 1
            
            # Добавляем в историю
            self._add_to_history('fail', ticket.address, ticket.nonce, ticket.id, reason)
            
            logger.warning(f"Failed nonce {ticket.nonce} for {ticket.address}: {reason}")
    
    def resync(self, address: str):
        """
        Принудительная ресинхронизация nonce для адреса
        
        Args:
            address: Адрес для ресинхронизации
        """
        address = Web3.to_checksum_address(address)
        state = self._get_or_create_state(address)
        
        with state.lock:
            self._resync_state(state)
    
    def _resync_state(self, state: AddressNonceState):
        """Внутренняя ресинхронизация состояния"""
        try:
            # Получаем актуальный nonce из сети
            network_nonce = self._fetch_network_nonce(state.address)
            
            # Обновляем состояние
            old_nonce = state.network_nonce
            state.network_nonce = network_nonce
            state.last_sync = datetime.now()
            
            # Корректируем next_nonce если нужно
            if network_nonce > state.next_nonce:
                logger.warning(f"Network nonce ({network_nonce}) > next_nonce ({state.next_nonce}) for {state.address}")
                state.next_nonce = network_nonce
            
            # Очищаем устаревшие confirmed nonces
            state.confirmed_nonces = {n for n in state.confirmed_nonces if n >= network_nonce}
            
            # Обновляем статистику
            self.resync_count += 1
            
            logger.info(f"Resynced {state.address}: network_nonce {old_nonce} -> {network_nonce}")
            
        except Exception as e:
            logger.error(f"Failed to resync {state.address}: {e}")
    
    def _cleanup_loop(self):
        """Фоновый поток для очистки устаревших резерваций"""
        while self.is_running:
            try:
                time.sleep(10)  # Проверка каждые 10 секунд
                self._cleanup_expired()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
    
    def _cleanup_expired(self):
        """Очистка истекших резерваций"""
        now = datetime.now()
        
        for address, state in list(self.states.items()):
            with state.lock:
                expired_tickets = []
                
                for ticket_id, ticket in state.tickets.items():
                    if ticket.status == NonceStatus.RESERVED and ticket.is_expired(self.reservation_timeout):
                        expired_tickets.append(ticket_id)
                
                for ticket_id in expired_tickets:
                    ticket = state.tickets[ticket_id]
                    
                    # Освобождаем nonce
                    if ticket.nonce in state.pending_nonces:
                        state.pending_nonces.remove(ticket.nonce)
                    
                    # Откатываем next_nonce если это был последний
                    if state.next_nonce == ticket.nonce + 1 and not state.pending_nonces:
                        state.next_nonce = ticket.nonce
                        logger.info(f"Rolled back next_nonce to {ticket.nonce} for {address} (expired)")
                    
                    # Обновляем статус
                    ticket.status = NonceStatus.EXPIRED
                    
                    logger.warning(f"Expired nonce reservation {ticket.nonce} for {address}")
                
                # Очищаем старые tickets (старше 1 часа)
                cutoff = now - timedelta(hours=1)
                old_tickets = [tid for tid, t in state.tickets.items() 
                             if t.reserved_at < cutoff and t.status in [NonceStatus.CONFIRMED, NonceStatus.FAILED, NonceStatus.EXPIRED]]
                
                for ticket_id in old_tickets:
                    del state.tickets[ticket_id]
    
    def _add_to_history(self, action: str, address: str, nonce: int, 
                       ticket_id: str, extra: Optional[str] = None):
        """Добавление записи в историю"""
        self.history.append({
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'address': address,
            'nonce': nonce,
            'ticket_id': ticket_id,
            'extra': extra
        })
    
    def get_stats(self, address: Optional[str] = None) -> Dict[str, Any]:
        """
        Получение статистики
        
        Args:
            address: Адрес для статистики (None для глобальной)
            
        Returns:
            Словарь со статистикой
        """
        if address:
            address = Web3.to_checksum_address(address)
            state = self.states.get(address)
            
            if not state:
                return {'error': 'Address not found'}
            
            with state.lock:
                return {
                    'address': address,
                    'network_nonce': state.network_nonce,
                    'next_nonce': state.next_nonce,
                    'pending_count': len(state.pending_nonces),
                    'confirmed_count': len(state.confirmed_nonces),
                    'failed_count': len(state.failed_nonces),
                    'active_tickets': len([t for t in state.tickets.values() 
                                         if t.status in [NonceStatus.RESERVED, NonceStatus.PENDING]]),
                    'last_sync': state.last_sync.isoformat()
                }
        else:
            # Глобальная статистика
            total_pending = sum(len(s.pending_nonces) for s in self.states.values())
            total_tickets = sum(len(s.tickets) for s in self.states.values())
            
            return {
                'total_addresses': len(self.states),
                'total_reserved': self.total_reserved,
                'total_confirmed': self.total_confirmed,
                'total_failed': self.total_failed,
                'total_pending': total_pending,
                'total_tickets': total_tickets,
                'resync_count': self.resync_count,
                'success_rate': f"{(self.total_confirmed / self.total_reserved * 100) if self.total_reserved > 0 else 0:.1f}%"
            }
    
    def get_pending_nonces(self, address: str) -> Set[int]:
        """Получение списка pending nonces для адреса"""
        address = Web3.to_checksum_address(address)
        state = self.states.get(address)
        
        if state:
            with state.lock:
                return state.pending_nonces.copy()
        return set()
    
    def reset_address(self, address: str):
        """Полный сброс состояния для адреса"""
        address = Web3.to_checksum_address(address)
        
        with self.global_lock:
            if address in self.states:
                del self.states[address]
                logger.info(f"Reset nonce state for {address}")
    
    def shutdown(self):
        """Остановка менеджера"""
        self.is_running = False
        if self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)


# Глобальный экземпляр
_global_manager: Optional[NonceManager] = None


def get_nonce_manager(web3: Optional[Web3] = None) -> NonceManager:
    """Получение глобального nonce manager"""
    global _global_manager
    
    if _global_manager is None:
        _global_manager = NonceManager(web3)
    elif web3 and not _global_manager.web3:
        _global_manager.set_web3(web3)
    
    return _global_manager


def close_nonce_manager():
    """Закрытие глобального nonce manager"""
    global _global_manager
    
    if _global_manager:
        _global_manager.shutdown()
        _global_manager = None
