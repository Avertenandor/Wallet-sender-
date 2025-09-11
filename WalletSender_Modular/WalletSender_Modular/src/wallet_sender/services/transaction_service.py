"""
Сервис для работы с транзакциями
"""

from typing import Optional, Dict, Any, List, Callable
from web3 import Web3
from eth_account import Account

from ..core.web3_provider import Web3Provider
from ..core.nonce_manager import get_nonce_manager, NonceTicket, NonceStatus
from ..constants import ERC20_ABI, GAS_LIMITS
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TransactionService:
    """Сервис для отправки и отслеживания транзакций"""
    
    def __init__(self, web3_provider: Web3Provider, private_key: Optional[str] = None, use_nonce_manager: bool = True, auto_finalize_on_send: bool = False):
        """
        Инициализация сервиса транзакций
        
        Args:
            web3_provider: Web3 провайдер
            private_key: Приватный ключ для подписи транзакций (опционально)
        """
        self.web3_provider = web3_provider
        self.web3 = web3_provider.web3
        self.private_key = private_key
        self.nonce_manager = None
        if use_nonce_manager:
            try:
                self.nonce_manager = get_nonce_manager(self.web3)
            except Exception:
                self.nonce_manager = None
        # Тикет последней транзакции (для финализации nonce)
        self._last_ticket: Optional[NonceTicket] = None
        # Автофинализация (опционально) — если True, ticket подтверждается сразу после отправки
        self.auto_finalize_on_send = auto_finalize_on_send
        
        if private_key:
            self.account = Account.from_key(private_key)
            self.address = self.account.address
        else:
            self.account = None
            self.address = None
    
    def set_private_key(self, private_key: str):
        """
        Установка приватного ключа
        
        Args:
            private_key: Приватный ключ
        """
        self.private_key = private_key
        self.account = Account.from_key(private_key)
        self.address = self.account.address
    
    def clear_private_key(self):
        """Очистка приватного ключа"""
        self.private_key = None
        self.account = None
        self.address = None

    def _ensure_ready(self) -> None:
        """Проверяет что web3, приватный ключ и адрес инициализированы.
        Бросает исключение с понятным текстом если что-то отсутствует.
        """
        if self.web3 is None:
            raise RuntimeError("Web3 не инициализирован в TransactionService")
        if not self.private_key:
            raise RuntimeError("Приватный ключ не установлен в TransactionService")
        if not self.address:
            raise RuntimeError("Адрес аккаунта не установлен (возможно не вызван set_private_key)")
        
    def _reserve_nonce(self, address: Optional[str]) -> int:
        """Резервирование nonce через NonceManager либо получение из сети.

        Возвращает nonce.
        """
        if not address:
            raise RuntimeError("Нельзя зарезервировать nonce: address=None")
        if self.nonce_manager:
            try:
                self._last_ticket = self.nonce_manager.reserve(address)
                return self._last_ticket.nonce  # type: ignore[return-value]
            except Exception:
                self._last_ticket = None
        return self.web3.eth.get_transaction_count(address, 'pending')

    def _mark_pending(self, tx_hash: str):
        if self.nonce_manager and self._last_ticket and self._last_ticket.status == NonceStatus.RESERVED:
            try:
                self.nonce_manager.complete(self._last_ticket, tx_hash)
            except Exception:
                pass

    def _mark_final(self, success: bool, reason: str = ""):
        if self.nonce_manager and self._last_ticket:
            try:
                if success:
                    self.nonce_manager.confirm(self._last_ticket)
                else:
                    self.nonce_manager.fail(self._last_ticket, reason or 'failed')
            except Exception:
                pass
            finally:
                self._last_ticket = None

    def send_native(
        self, 
        to_address: str, 
        amount: float,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> str:
        """
        Отправка нативной валюты (ETH/BNB)
        
        Args:
            to_address: Адрес получателя
            amount: Сумма в эфирах/BNB
            gas_price: Цена газа в wei
            gas_limit: Лимит газа
            
        Returns:
            str: Хэш транзакции
        """
        try:
            self._ensure_ready()
            # Проверка адреса
            if not self.web3.is_address(to_address):
                raise ValueError(f"Неверный адрес получателя: {to_address}")
                
            to_address = self.web3.to_checksum_address(to_address)
            
            # Конвертация суммы в wei
            amount_wei = self.web3.to_wei(amount, 'ether')
            
            # Получение nonce
            nonce = self._reserve_nonce(self.address)
            
            # Параметры газа
            if gas_price is None:
                gas_price = self.web3.eth.gas_price
                
            if gas_limit is None:
                gas_limit = GAS_LIMITS['transfer']
                
            # Создание транзакции
            transaction = {
                'nonce': nonce,
                'to': to_address,
                'value': amount_wei,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'chainId': self.web3_provider.network_config['chain_id']
            }
            
            # Подпись транзакции
            signed_tx = self.web3.eth.account.sign_transaction(
                transaction, 
                self.private_key
            )
            
            # Отправка транзакции
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            self._mark_pending(tx_hash.hex())
            
            logger.info(f"Отправлена транзакция: {tx_hash.hex()}")
            if self.auto_finalize_on_send:
                # если пользователь не будет явно ждать подтверждения — считаем success условно
                self._mark_final(True)
            return tx_hash.hex()
            
        except Exception as e:
            logger.error(f"Ошибка отправки нативной валюты: {e}")
            self._mark_final(False, str(e))
            raise
            
    def send_token(
        self, 
        token_address: str,
        to_address: str, 
        amount: float,
        decimals: int,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> str:
        """
        Отправка ERC20 токена
        
        Args:
            token_address: Адрес контракта токена
            to_address: Адрес получателя
            amount: Сумма токенов
            decimals: Количество десятичных знаков токена
            gas_price: Цена газа в wei
            gas_limit: Лимит газа
            
        Returns:
            str: Хэш транзакции
        """
        try:
            self._ensure_ready()
            # Проверка адресов
            if not self.web3.is_address(token_address):
                raise ValueError(f"Неверный адрес токена: {token_address}")
                
            if not self.web3.is_address(to_address):
                raise ValueError(f"Неверный адрес получателя: {to_address}")
                
            token_address = self.web3.to_checksum_address(token_address)
            to_address = self.web3.to_checksum_address(to_address)
            
            # Создание контракта токена
            token_contract = self.web3.eth.contract(
                address=token_address,
                abi=ERC20_ABI
            )
            
            # Конвертация суммы с учетом decimals
            amount_wei = int(amount * (10 ** decimals))
            
            # Получение nonce
            nonce = self._reserve_nonce(self.address)
            
            # Параметры газа
            if gas_price is None:
                gas_price = self.web3.eth.gas_price
                
            if gas_limit is None:
                gas_limit = 100000  # Обычно для токенов нужно больше газа
                
            # Создание транзакции transfer
            transaction = token_contract.functions.transfer(
                to_address,
                amount_wei
            ).build_transaction({
                'chainId': self.web3_provider.network_config['chain_id'],
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': nonce,
                'from': self.address
            })
            
            # Подпись транзакции
            signed_tx = self.web3.eth.account.sign_transaction(
                transaction, 
                self.private_key
            )
            
            # Отправка транзакции
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            self._mark_pending(tx_hash.hex())
            
            logger.info(f"Отправлена транзакция токена: {tx_hash.hex()}")
            if self.auto_finalize_on_send:
                self._mark_final(True)
            return tx_hash.hex()
            
        except Exception as e:
            logger.error(f"Ошибка отправки токена: {e}")
            self._mark_final(False, str(e))
            raise
            
    def wait_for_confirmation(
        self, 
        tx_hash: str, 
        timeout: int = 300
    ) -> Optional[Dict[str, Any]]:
        """
        Ожидание подтверждения транзакции
        
        Args:
            tx_hash: Хэш транзакции
            timeout: Таймаут в секундах
            
        Returns:
            Dict: Квитанция транзакции или None
        """
        try:
            # Ждём подтверждение; здесь финализируем тикет если включена отложенная финализация
            receipt = self.web3_provider.wait_for_transaction_receipt(
                tx_hash, 
                timeout
            )
            
            if receipt and receipt['status'] == 1:
                logger.info(f"Транзакция подтверждена: {tx_hash}")
                self._mark_final(True)
            else:
                logger.warning(f"Транзакция не удалась: {tx_hash}")
                self._mark_final(False, 'receipt status != 1')
                
            return receipt
            
        except Exception as e:
            logger.error(f"Ошибка ожидания подтверждения: {e}")
            self._mark_final(False, str(e))
            return None
            
    def get_transaction_status(self, tx_hash: str) -> str:
        """
        Получение статуса транзакции
        
        Args:
            tx_hash: Хэш транзакции
            
        Returns:
            str: Статус ('pending', 'success', 'failed', 'unknown')
        """
        try:
            # Пробуем получить квитанцию
            receipt = self.web3.eth.get_transaction_receipt(tx_hash)
            
            if receipt:
                if receipt['status'] == 1:
                    return 'success'
                else:
                    return 'failed'
            else:
                # Проверяем, есть ли транзакция в пуле
                tx = self.web3.eth.get_transaction(tx_hash)
                if tx:
                    return 'pending'
                else:
                    return 'unknown'
                    
        except Exception as e:
            logger.error(f"Ошибка получения статуса транзакции: {e}")
            return 'unknown'
            
    def estimate_gas(
        self,
        to_address: str,
        value: int = 0,
        data: str = '0x'
    ) -> int:
        """
        Оценка газа для транзакции
        
        Args:
            to_address: Адрес получателя
            value: Сумма в wei
            data: Данные транзакции
            
        Returns:
            int: Оценка газа
        """
        try:
            gas_estimate = self.web3.eth.estimate_gas({
                'from': self.address,
                'to': to_address,
                'value': value,
                'data': data
            })
            
            # Добавляем небольшой запас
            return int(gas_estimate * 1.2)
            
        except Exception as e:
            logger.error(f"Ошибка оценки газа: {e}")
            return GAS_LIMITS['transfer']
            
    def batch_send_token(
        self,
        token_address: str,
        recipients: List[Dict[str, Any]],
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None,
        callback=None
    ) -> List[str]:
        """
        Массовая отправка токенов
        
        Args:
            token_address: Адрес контракта токена
            recipients: Список получателей [{address, amount}]
            gas_price: Цена газа в wei
            gas_limit: Лимит газа на транзакцию
            callback: Функция обратного вызова для прогресса
            
        Returns:
            List[str]: Список хэшей транзакций
        """
        tx_hashes = []
        
        # Получаем decimals токена
        token_contract = self.web3.eth.contract(
            address=self.web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )
        decimals = token_contract.functions.decimals().call()
        
        for i, recipient in enumerate(recipients):
            try:
                tx_hash = self.send_token(
                    token_address,
                    recipient['address'],
                    recipient['amount'],
                    decimals,
                    gas_price,
                    gas_limit
                )
                
                tx_hashes.append(tx_hash)
                
                if callback:
                    callback(i + 1, len(recipients), tx_hash, 'success')
                    
            except Exception as e:
                logger.error(f"Ошибка отправки на {recipient['address']}: {e}")
                
                if callback:
                    callback(i + 1, len(recipients), '', 'error', str(e))
                    
        return tx_hashes
