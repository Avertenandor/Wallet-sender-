"""Web3 Provider for BSC network"""

from typing import Optional, Dict, Union
from web3 import Web3
from web3.types import TxReceipt
from hexbytes import HexBytes
import logging

logger = logging.getLogger(__name__)

class Web3Provider:
    """Провайдер для подключения к BSC сети"""
    
    def __init__(self):
        self.rpc_urls = [
            'https://bsc-dataseed.binance.org/',
            'https://bsc-dataseed1.defibit.io/',
            'https://bsc-dataseed1.ninicoin.io/'
        ]
        # Сетевые параметры, ожидаемые сервисами
        self.network_config: Dict[str, Union[int, str]] = {
            'chain_id': 56,
            'symbol': 'BNB',
        }
        self.w3: Optional[Web3] = None
        self.current_rpc_index = 0
        self._connect()
    
    # Совместимость: некоторые части кода обращаются к .web3, а не .w3
    @property
    def web3(self) -> Optional[Web3]:
        return self.w3
    
    def _connect(self):
        """Подключение к BSC сети"""
        for i, rpc_url in enumerate(self.rpc_urls):
            try:
                self.w3 = Web3(Web3.HTTPProvider(rpc_url))
                if self.w3.is_connected():
                    self.current_rpc_index = i
                    logger.info(f"[OK] Подключен к BSC: {rpc_url}")
                    return True
            except Exception as e:
                logger.warning(f"[ERROR] Не удалось подключиться к {rpc_url}: {e}")
                continue
        
        logger.error("[ERROR] Не удалось подключиться ни к одному RPC")
        return False
    
    def is_connected(self):
        """Проверка подключения"""
        try:
            return self.w3 and self.w3.is_connected()
        except:
            return False
    
    def get_web3(self):
        """Получить объект Web3"""
        return self.w3
    
    def wait_for_transaction_receipt(self, tx_hash: Union[str, bytes, HexBytes], timeout: int = 300) -> Optional[TxReceipt]:
        """Ожидание квитанции по транзакции с таймаутом.

        Возвращает Receipt или None при ошибке/таймауте.
        """
        try:
            if not self.w3:
                return None
            # web3.py вернёт исключение по таймауту, перехватываем и возвращаем None
            # Приводим к bytes (HexBytes совместим с bytes) для строгой типизации
            if isinstance(tx_hash, str):
                # Ожидаем строку вида '0x...'
                h: HexBytes = HexBytes(tx_hash)
            elif isinstance(tx_hash, (bytes, bytearray, memoryview)):
                h = HexBytes(tx_hash)
            else:
                h = tx_hash
            return self.w3.eth.wait_for_transaction_receipt(h, timeout=timeout)
        except Exception as e:
            logger.error(f"Ошибка ожидания квитанции: {e}")
            return None
