"""
Сервис для работы с токенами
"""

from typing import Optional, Dict, Any, List
from web3 import Web3
from decimal import Decimal

from ..core.web3_provider import Web3Provider
from ..constants import ERC20_ABI
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TokenService:
    """Сервис для работы с токенами ERC20"""
    
    def __init__(self, web3_provider: Web3Provider):
        """
        Инициализация сервиса токенов
        
        Args:
            web3_provider: Web3 провайдер
        """
        self.web3_provider = web3_provider
        self.web3 = web3_provider.web3
        self._token_cache = {}  # Кэш информации о токенах
        
    def get_token_info(self, token_address: str) -> Dict[str, Any]:
        """
        Получение информации о токене
        
        Args:
            token_address: Адрес контракта токена
            
        Returns:
            Dict: Информация о токене (name, symbol, decimals, totalSupply)
        """
        try:
            # Проверяем кэш
            if token_address in self._token_cache:
                return self._token_cache[token_address]
                
            # Проверка адреса
            if not self.web3.is_address(token_address):
                raise ValueError(f"Неверный адрес токена: {token_address}")
                
            token_address = self.web3.to_checksum_address(token_address)
            
            # Создание контракта токена
            token_contract = self.web3.eth.contract(
                address=token_address,
                abi=ERC20_ABI
            )
            
            # Получение информации о токене
            info = {
                'address': token_address,
                'name': self._safe_call(token_contract.functions.name()),
                'symbol': self._safe_call(token_contract.functions.symbol()),
                'decimals': self._safe_call(token_contract.functions.decimals()),
                'totalSupply': self._safe_call(token_contract.functions.totalSupply())
            }
            
            # Сохраняем в кэш
            self._token_cache[token_address] = info
            
            logger.info(f"Получена информация о токене {info['symbol']}: {token_address}")
            
            return info
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о токене: {e}")
            return {
                'address': token_address,
                'name': 'Unknown',
                'symbol': 'UNKNOWN',
                'decimals': 18,
                'totalSupply': 0
            }
            
    def get_balance(self, token_address: str, wallet_address: str) -> float:
        """
        Получение баланса токена для кошелька
        
        Args:
            token_address: Адрес контракта токена
            wallet_address: Адрес кошелька
            
        Returns:
            float: Баланс токена
        """
        try:
            # Проверка адресов
            if not self.web3.is_address(token_address):
                raise ValueError(f"Неверный адрес токена: {token_address}")
                
            if not self.web3.is_address(wallet_address):
                raise ValueError(f"Неверный адрес кошелька: {wallet_address}")
                
            token_address = self.web3.to_checksum_address(token_address)
            wallet_address = self.web3.to_checksum_address(wallet_address)
            
            # Создание контракта токена
            token_contract = self.web3.eth.contract(
                address=token_address,
                abi=ERC20_ABI
            )
            
            # Получение баланса
            balance_wei = token_contract.functions.balanceOf(wallet_address).call()
            
            # Получение decimals
            decimals = self._safe_call(token_contract.functions.decimals(), 18)
            
            # Конвертация в читаемый формат
            balance = balance_wei / (10 ** decimals)
            
            return balance
            
        except Exception as e:
            logger.error(f"Ошибка получения баланса токена: {e}")
            return 0.0
            
    def get_allowance(
        self, 
        token_address: str, 
        owner_address: str, 
        spender_address: str
    ) -> float:
        """
        Получение разрешенной суммы для траты токенов
        
        Args:
            token_address: Адрес контракта токена
            owner_address: Адрес владельца токенов
            spender_address: Адрес того, кому разрешено тратить
            
        Returns:
            float: Разрешенная сумма
        """
        try:
            # Проверка адресов
            token_address = self.web3.to_checksum_address(token_address)
            owner_address = self.web3.to_checksum_address(owner_address)
            spender_address = self.web3.to_checksum_address(spender_address)
            
            # Создание контракта токена
            token_contract = self.web3.eth.contract(
                address=token_address,
                abi=ERC20_ABI
            )
            
            # Получение allowance
            allowance_wei = token_contract.functions.allowance(
                owner_address, 
                spender_address
            ).call()
            
            # Получение decimals
            decimals = self._safe_call(token_contract.functions.decimals(), 18)
            
            # Конвертация в читаемый формат
            allowance = allowance_wei / (10 ** decimals)
            
            return allowance
            
        except Exception as e:
            logger.error(f"Ошибка получения allowance: {e}")
            return 0.0
            
    def approve(
        self,
        token_address: str,
        spender_address: str,
        amount: float,
        private_key: str,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> str:
        """
        Одобрение траты токенов
        
        Args:
            token_address: Адрес контракта токена
            spender_address: Адрес того, кому разрешаем тратить
            amount: Сумма для одобрения
            private_key: Приватный ключ владельца токенов
            gas_price: Цена газа в wei
            gas_limit: Лимит газа
            
        Returns:
            str: Хэш транзакции
        """
        try:
            from eth_account import Account
            
            # Получаем аккаунт из приватного ключа
            account = Account.from_key(private_key)
            
            # Проверка адресов
            token_address = self.web3.to_checksum_address(token_address)
            spender_address = self.web3.to_checksum_address(spender_address)
            
            # Создание контракта токена
            token_contract = self.web3.eth.contract(
                address=token_address,
                abi=ERC20_ABI
            )
            
            # Получение decimals
            decimals = self._safe_call(token_contract.functions.decimals(), 18)
            
            # Конвертация суммы
            amount_wei = int(amount * (10 ** decimals))
            
            # Получение nonce
            nonce = self.web3.eth.get_transaction_count(account.address)
            
            # Параметры газа
            if gas_price is None:
                gas_price = self.web3.eth.gas_price
                
            if gas_limit is None:
                gas_limit = 100000
                
            # Создание транзакции approve
            transaction = token_contract.functions.approve(
                spender_address,
                amount_wei
            ).build_transaction({
                'chainId': self.web3_provider.network_config['chain_id'],
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': nonce,
                'from': account.address
            })
            
            # Подпись транзакции
            signed_tx = self.web3.eth.account.sign_transaction(
                transaction, 
                private_key
            )
            
            # Отправка транзакции
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            logger.info(f"Отправлена транзакция approve: {tx_hash.hex()}")
            
            return tx_hash.hex()
            
        except Exception as e:
            logger.error(f"Ошибка approve: {e}")
            raise
            
    def get_token_holders(
        self,
        token_address: str,
        min_balance: float = 0
    ) -> List[Dict[str, Any]]:
        """
        Получение списка держателей токена
        (Требует индексированных данных или архивную ноду)
        
        Args:
            token_address: Адрес контракта токена
            min_balance: Минимальный баланс для включения в список
            
        Returns:
            List[Dict]: Список держателей токена
        """
        logger.warning("Получение списка держателей токена требует архивную ноду или внешний API")
        return []
        
    def get_token_transfers(
        self,
        token_address: str,
        from_block: int = 0,
        to_block: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение истории переводов токена
        
        Args:
            token_address: Адрес контракта токена
            from_block: Начальный блок
            to_block: Конечный блок (None = последний)
            
        Returns:
            List[Dict]: Список переводов
        """
        try:
            token_address = self.web3.to_checksum_address(token_address)
            
            # Создание контракта токена
            token_contract = self.web3.eth.contract(
                address=token_address,
                abi=ERC20_ABI
            )
            
            # Если не указан конечный блок, берем последний
            if to_block is None:
                to_block = self.web3.eth.block_number
                
            # Получение событий Transfer
            transfer_filter = token_contract.events.Transfer.create_filter(
                fromBlock=from_block,
                toBlock=to_block
            )
            
            events = transfer_filter.get_all_entries()
            
            transfers = []
            for event in events:
                transfers.append({
                    'from': event['args']['from'],
                    'to': event['args']['to'],
                    'value': event['args']['value'],
                    'blockNumber': event['blockNumber'],
                    'transactionHash': event['transactionHash'].hex()
                })
                
            logger.info(f"Получено {len(transfers)} переводов токена")
            
            return transfers
            
        except Exception as e:
            logger.error(f"Ошибка получения переводов токена: {e}")
            return []
            
    def _safe_call(self, func, default=None):
        """
        Безопасный вызов функции контракта
        
        Args:
            func: Функция для вызова
            default: Значение по умолчанию при ошибке
            
        Returns:
            Результат вызова или значение по умолчанию
        """
        try:
            return func.call()
        except Exception as e:
            logger.debug(f"Ошибка вызова функции контракта: {e}")
            return default
            
    def validate_token_address(self, address: str) -> bool:
        """
        Проверка валидности адреса токена
        
        Args:
            address: Адрес для проверки
            
        Returns:
            bool: True если адрес валидный токен
        """
        try:
            if not self.web3.is_address(address):
                return False
                
            # Пробуем получить информацию о токене
            info = self.get_token_info(address)
            
            # Если есть символ и decimals, скорее всего это токен
            return info['symbol'] != 'UNKNOWN' and info['decimals'] is not None
            
        except Exception:
            return False
            
    def clear_cache(self):
        """Очистка кэша информации о токенах"""
        self._token_cache.clear()
        logger.info("Кэш информации о токенах очищен")
