"""
Web3 provider для подключения к BSC сети
"""

from typing import Optional, Dict, Any
from web3 import Web3
from web3.middleware import geth_poa_middleware

from ..utils.logger import get_logger

logger = get_logger(__name__)


class Web3Provider:
    """Провайдер Web3 для работы с BSC сетью"""
    
    def __init__(self, rpc_url: Optional[str] = None):
        """
        Инициализация Web3 провайдера
        
        Args:
            rpc_url: URL RPC эндпоинта (по умолчанию BSC mainnet)
        """
        if rpc_url is None:
            # BSC Mainnet RPC URLs (fallback)
            rpc_urls = [
                'https://bsc-dataseed.binance.org/',
                'https://bsc-dataseed1.defibit.io/',
                'https://bsc-dataseed1.ninicoin.io/',
                'https://bsc-dataseed2.defibit.io/',
                'https://bsc-dataseed3.defibit.io/'
            ]
            rpc_url = rpc_urls[0]  # Используем первый по умолчанию
            
        self.rpc_url = rpc_url
        self.web3 = None
        self.network_config = {
            'chain_id': 56,  # BSC Mainnet
            'currency_symbol': 'BNB',
            'block_explorer': 'https://bscscan.com'
        }
        
        self._connect()
        
    def _connect(self):
        """Подключение к сети"""
        try:
            self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
            
            # Добавляем middleware для BSC (Proof of Authority)
            self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            if self.web3.is_connected():
                logger.info(f"✅ Подключен к BSC: {self.rpc_url}")
                
                # Получаем информацию о сети
                try:
                    latest_block = self.web3.eth.get_block('latest')
                    logger.info(f"Последний блок: {latest_block['number']}")
                except Exception as e:
                    logger.warning(f"Не удалось получить информацию о блоке: {e}")
            else:
                logger.error("❌ Не удалось подключиться к BSC")
                raise ConnectionError("Не удалось подключиться к BSC")
                
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Web3: {e}")
            raise
            
    @property
    def w3(self) -> Web3:
        """Получение экземпляра Web3"""
        return self.web3
        
    def is_connected(self) -> bool:
        """Проверка подключения"""
        return self.web3 and self.web3.is_connected()
        
    def get_balance(self, address: str) -> int:
        """
        Получение баланса BNB в wei
        
        Args:
            address: Адрес кошелька
            
        Returns:
            int: Баланс в wei
        """
        if not self.is_connected():
            raise ConnectionError("Web3 не подключен")
            
        return self.web3.eth.get_balance(address)
        
    def get_balance_ether(self, address: str) -> float:
        """
        Получение баланса BNB в эфирах
        
        Args:
            address: Адрес кошелька
            
        Returns:
            float: Баланс в BNB
        """
        balance_wei = self.get_balance(address)
        return self.web3.from_wei(balance_wei, 'ether')
        
    def get_gas_price(self) -> int:
        """
        Получение текущей цены газа
        
        Returns:
            int: Цена газа в wei
        """
        if not self.is_connected():
            raise ConnectionError("Web3 не подключен")
            
        return self.web3.eth.gas_price
        
    def get_gas_price_gwei(self) -> float:
        """
        Получение текущей цены газа в Gwei
        
        Returns:
            float: Цена газа в Gwei
        """
        gas_price_wei = self.get_gas_price()
        return self.web3.from_wei(gas_price_wei, 'gwei')
        
    def get_transaction_count(self, address: str) -> int:
        """
        Получение nonce для адреса
        
        Args:
            address: Адрес кошелька
            
        Returns:
            int: Nonce
        """
        if not self.is_connected():
            raise ConnectionError("Web3 не подключен")
            
        return self.web3.eth.get_transaction_count(address)
        
    def wait_for_transaction_receipt(self, tx_hash: str, timeout: int = 300) -> Optional[Dict[str, Any]]:
        """
        Ожидание подтверждения транзакции
        
        Args:
            tx_hash: Хэш транзакции
            timeout: Таймаут в секундах
            
        Returns:
            Dict: Квитанция транзакции или None
        """
        if not self.is_connected():
            raise ConnectionError("Web3 не подключен")
            
        try:
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
            return receipt
        except Exception as e:
            logger.error(f"Ошибка ожидания подтверждения транзакции {tx_hash}: {e}")
            return None
            
    def get_latest_block(self) -> Dict[str, Any]:
        """
        Получение информации о последнем блоке
        
        Returns:
            Dict: Информация о блоке
        """
        if not self.is_connected():
            raise ConnectionError("Web3 не подключен")
            
        return self.web3.eth.get_block('latest')
        
    def estimate_gas(self, transaction: Dict[str, Any]) -> int:
        """
        Оценка газа для транзакции
        
        Args:
            transaction: Параметры транзакции
            
        Returns:
            int: Оценка газа
        """
        if not self.is_connected():
            raise ConnectionError("Web3 не подключен")
            
        return self.web3.eth.estimate_gas(transaction)
        
    def send_raw_transaction(self, signed_txn_bytes: bytes) -> str:
        """
        Отправка подписанной транзакции
        
        Args:
            signed_txn_bytes: Подписанная транзакция в байтах
            
        Returns:
            str: Хэш транзакции
        """
        if not self.is_connected():
            raise ConnectionError("Web3 не подключен")
            
        tx_hash = self.web3.eth.send_raw_transaction(signed_txn_bytes)
        return tx_hash.hex()
        
    def get_network_info(self) -> Dict[str, Any]:
        """
        Получение информации о сети
        
        Returns:
            Dict: Информация о сети
        """
        info = self.network_config.copy()
        
        if self.is_connected():
            try:
                latest_block = self.get_latest_block()
                info.update({
                    'latest_block': latest_block['number'],
                    'gas_price_gwei': self.get_gas_price_gwei(),
                    'connected': True
                })
            except Exception as e:
                logger.warning(f"Не удалось получить расширенную информацию о сети: {e}")
                info['connected'] = True
        else:
            info['connected'] = False
            
        return info
