"""DexSwapService с асинхронной обработкой и улучшенными таймаутами

Версия 2.4.20 - Исправление проблем с таймаутами и nonce
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any, Callable
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from web3 import Web3
from eth_account import Account
from ..utils.gas_manager import GasManager
from ..core.nonce_manager import get_nonce_manager, NonceStatus, NonceTicket
from ..utils.logger import get_logger
from ..constants import ERC20_ABI

PANCAKE_ROUTER_ABI = [
    {"name": "swapExactTokensForETH", "type": "function", "stateMutability": "nonpayable",
     "inputs": [
         {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
         {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
         {"internalType": "address[]", "name": "path", "type": "address[]"},
         {"internalType": "address", "name": "to", "type": "address"},
         {"internalType": "uint256", "name": "deadline", "type": "uint256"}
     ], "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}]},
    {"name": "swapExactETHForTokens", "type": "function", "stateMutability": "payable",
     "inputs": [
         {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
         {"internalType": "address[]", "name": "path", "type": "address[]"},
         {"internalType": "address", "name": "to", "type": "address"},
         {"internalType": "uint256", "name": "deadline", "type": "uint256"}
     ], "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}]},
    {"name": "swapExactTokensForTokens", "type": "function", "stateMutability": "nonpayable",
     "inputs": [
         {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
         {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
         {"internalType": "address[]", "name": "path", "type": "address[]"},
         {"internalType": "address", "name": "to", "type": "address"},
         {"internalType": "uint256", "name": "deadline", "type": "uint256"}
     ], "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}]},
    {"name": "getAmountsOut", "type": "function", "stateMutability": "view",
     "inputs": [
         {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
         {"internalType": "address[]", "name": "path", "type": "address[]"}
     ], "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}]}
]

logger = get_logger(__name__)


class DexSwapServiceAsync:
    """Асинхронная версия DexSwapService с улучшенной обработкой таймаутов"""
    
    def __init__(self, web3: Web3, router_address: str, private_key: str, 
                 gas_manager: Optional[GasManager] = None, 
                 custom_gas_price_gwei: float = 0.1):
        self.web3 = web3
        self.router_address = web3.to_checksum_address(router_address)
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        self.router = web3.eth.contract(address=self.router_address, abi=PANCAKE_ROUTER_ABI)
        self.gas_manager = gas_manager or GasManager(web3)
        
        # Nonce manager
        try:
            self.nonce_manager = get_nonce_manager(web3)
        except Exception:
            self.nonce_manager = None
        self._last_ticket: Optional[NonceTicket] = None
        
        # Кастомная цена газа
        self.custom_gas_price_gwei = custom_gas_price_gwei
        
        # Executor для асинхронных операций
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Кеш последнего успешного nonce
        self._last_successful_nonce = None
        self._nonce_lock = asyncio.Lock() if asyncio._get_running_loop() else None

    def __del__(self):
        """Закрытие executor при удалении объекта"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)

    # ---------- внутренние утилиты ----------
    def _sync_nonce_with_network(self) -> int:
        """Синхронизация nonce с сетью"""
        try:
            # Получаем реальный nonce из сети
            network_nonce = self.web3.eth.get_transaction_count(self.address, 'latest')
            pending_nonce = self.web3.eth.get_transaction_count(self.address, 'pending')
            
            # Используем максимальный
            actual_nonce = max(network_nonce, pending_nonce)
            
            # Если есть кешированный успешный nonce, проверяем
            if self._last_successful_nonce is not None:
                # Следующий nonce должен быть больше последнего успешного
                actual_nonce = max(actual_nonce, self._last_successful_nonce + 1)
            
            logger.info(f"Nonce синхронизирован: network={network_nonce}, pending={pending_nonce}, using={actual_nonce}")
            return actual_nonce
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации nonce: {e}")
            # Fallback на pending
            return self.web3.eth.get_transaction_count(self.address, 'pending')

    def _reserve_nonce(self) -> int:
        """Резервирование nonce с проверкой синхронизации"""
        # Сначала синхронизируемся с сетью
        network_nonce = self._sync_nonce_with_network()
        
        if self.nonce_manager:
            try:
                # Проверяем, что nonce manager синхронизирован
                self._last_ticket = self.nonce_manager.reserve(self.address)
                manager_nonce = self._last_ticket.nonce  # type: ignore[attr-defined]
                
                # Если manager отстал, используем сетевой
                if manager_nonce < network_nonce:
                    logger.warning(f"Nonce manager отстал: {manager_nonce} < {network_nonce}, ресинхронизация...")
                    # Принудительная синхронизация nonce manager
                    if hasattr(self.nonce_manager, 'resync'):
                        self.nonce_manager.resync(self.address)
                    return network_nonce
                    
                return manager_nonce
                
            except Exception as e:
                logger.warning(f"NonceManager reserve fallback: {e}")
                self._last_ticket = None
                
        return network_nonce

    def _mark_pending(self, tx_hash: str) -> None:
        """Отметка транзакции как pending"""
        if self.nonce_manager and self._last_ticket and self._last_ticket.status == NonceStatus.RESERVED:
            try:
                self.nonce_manager.complete(self._last_ticket, tx_hash)
            except Exception as e:
                logger.debug(f"Complete ticket warn: {e}")

    def _finalize(self, success: bool, nonce: int = None, reason: str = "") -> None:
        """Финализация транзакции"""
        if success and nonce is not None:
            self._last_successful_nonce = nonce
            
        if self.nonce_manager and self._last_ticket:
            try:
                if success:
                    self.nonce_manager.confirm(self._last_ticket)
                else:
                    self.nonce_manager.fail(self._last_ticket, reason or 'failed')
            except Exception as e:
                logger.debug(f"Finalize ticket warn: {e}")
            finally:
                self._last_ticket = None

    def _gas_price(self, override: Optional[int], op: str) -> int:
        """Получение цены газа"""
        if override is not None:
            return override
        
        custom_gas_price_wei = self.web3.to_wei(self.custom_gas_price_gwei, 'gwei')
        logger.debug(f"Используем кастомную цену газа: {self.custom_gas_price_gwei} gwei")
        return custom_gas_price_wei

    def _build_and_send(self, fn: Callable[..., Any], tx_params: Dict[str, Any]) -> str:
        """Построение и отправка транзакции"""
        try:
            tx = fn.build_transaction(tx_params)
            signed = self.web3.eth.account.sign_transaction(tx, self.account.key)
            raw_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
            tx_hash = raw_hash.hex()
            self._mark_pending(tx_hash)
            logger.info(f"Транзакция отправлена: {tx_hash}, nonce={tx_params['nonce']}")
            return tx_hash
        except Exception as e:
            logger.error(f"Ошибка отправки транзакции: {e}")
            # Проверяем тип ошибки
            error_str = str(e).lower()
            if 'nonce too low' in error_str:
                logger.error("Nonce слишком низкий, требуется ресинхронизация")
                self._last_successful_nonce = None  # Сбрасываем кеш
            elif 'nonce too high' in error_str:
                logger.error("Nonce слишком высокий")
            raise

    async def _wait_receipt_async(self, tx_hash: str, timeout: int = 30, max_attempts: int = 10) -> Optional[Dict[str, Any]]:
        """Асинхронное ожидание receipt с несколькими попытками"""
        attempt = 0
        total_wait = 0
        
        while attempt < max_attempts and total_wait < timeout:
            try:
                # Проверяем транзакцию
                tx = self.web3.eth.get_transaction(tx_hash)
                if tx:
                    # Транзакция есть в мемпуле
                    logger.debug(f"Транзакция {tx_hash[:8]}... в мемпуле, попытка {attempt + 1}/{max_attempts}")
                
                # Пробуем получить receipt
                receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                if receipt:
                    # Receipt получен!
                    status = receipt.get('status', 0)
                    if status == 1:
                        logger.info(f"Транзакция {tx_hash[:8]}... успешна!")
                        self._finalize(True, nonce=tx.get('nonce'))
                    else:
                        logger.error(f"Транзакция {tx_hash[:8]}... неудачна (status={status})")
                        self._finalize(False, reason=f'status={status}')
                    return dict(receipt)
                    
            except Exception as e:
                # Receipt еще не готов
                logger.debug(f"Receipt не готов: {e}")
            
            # Ждем перед следующей попыткой
            wait_time = min(3, timeout - total_wait)  # Максимум 3 секунды за раз
            await asyncio.sleep(wait_time)
            total_wait += wait_time
            attempt += 1
        
        # Таймаут - но не считаем это критической ошибкой
        logger.warning(f"Таймаут ожидания receipt для {tx_hash[:8]}... после {total_wait}с")
        
        # НЕ финализируем как ошибку - транзакция может быть еще в процессе
        # Просто возвращаем None
        return None

    # ---------- публичные методы ----------
    def approve(self, token_address: str, spender: Optional[str] = None, 
                amount_wei: Optional[int] = None, gas_price: Optional[int] = None, 
                gas_limit: int = 60_000) -> str:
        """Approve токена"""
        token = self.web3.eth.contract(address=self.web3.to_checksum_address(token_address), abi=ERC20_ABI)
        spender_final = self.router_address if spender is None else self.web3.to_checksum_address(spender)
        amount_final = amount_wei if amount_wei is not None else 2 ** 256 - 1
        nonce = self._reserve_nonce()
        
        tx_params = {
            'from': self.address,
            'nonce': nonce,
            'gas': gas_limit,
            'gasPrice': self._gas_price(gas_price, 'approve'),
            'chainId': self.web3.eth.chain_id
        }
        
        tx_hash = self._build_and_send(token.functions.approve(spender_final, amount_final), tx_params)
        logger.info(f"Approve sent: {tx_hash}")
        return tx_hash

    def get_amounts_out(self, amount_in: int, path: List[str]) -> List[int]:
        """Получение ожидаемого выхода"""
        return self.router.functions.getAmountsOut(amount_in, path).call()

    def swap_exact_tokens_for_tokens(self, amount_in: int, amount_out_min: int, path: List[str],
                                     deadline: Optional[int] = None, gas_price: Optional[int] = None,
                                     gas_limit: int = 300_000) -> str:
        """Swap токен на токен"""
        deadline_final = deadline or int(time.time()) + 1200
        nonce = self._reserve_nonce()
        
        tx_params = {
            'from': self.address,
            'nonce': nonce,
            'gas': gas_limit,
            'gasPrice': self._gas_price(gas_price, 'swap'),
            'chainId': self.web3.eth.chain_id
        }
        
        fn = self.router.functions.swapExactTokensForTokens(
            amount_in, amount_out_min, path, self.address, deadline_final
        )
        tx_hash = self._build_and_send(fn, tx_params)
        logger.info(f"swapExactTokensForTokens sent: {tx_hash}")
        return tx_hash

    def swap_exact_tokens_for_eth(self, amount_in: int, amount_out_min: int, path: List[str],
                                  deadline: Optional[int] = None, gas_price: Optional[int] = None,
                                  gas_limit: int = 300_000) -> str:
        """Swap токен на ETH/BNB"""
        deadline_final = deadline or int(time.time()) + 1200
        nonce = self._reserve_nonce()
        
        tx_params = {
            'from': self.address,
            'nonce': nonce,
            'gas': gas_limit,
            'gasPrice': self._gas_price(gas_price, 'swap'),
            'chainId': self.web3.eth.chain_id
        }
        
        fn = self.router.functions.swapExactTokensForETH(
            amount_in, amount_out_min, path, self.address, deadline_final
        )
        tx_hash = self._build_and_send(fn, tx_params)
        logger.info(f"swapExactTokensForETH sent: {tx_hash}")
        return tx_hash

    def swap_exact_eth_for_tokens(self, amount_in_wei: int, amount_out_min: int, path: List[str],
                                  deadline: Optional[int] = None, gas_price: Optional[int] = None,
                                  gas_limit: int = 300_000) -> str:
        """Swap ETH/BNB на токен"""
        deadline_final = deadline or int(time.time()) + 1200
        nonce = self._reserve_nonce()
        
        tx_params = {
            'from': self.address,
            'nonce': nonce,
            'value': amount_in_wei,
            'gas': gas_limit,
            'gasPrice': self._gas_price(gas_price, 'swap'),
            'chainId': self.web3.eth.chain_id
        }
        
        fn = self.router.functions.swapExactETHForTokens(
            amount_out_min, path, self.address, deadline_final
        )
        tx_hash = self._build_and_send(fn, tx_params)
        logger.info(f"swapExactETHForTokens sent: {tx_hash}")
        return tx_hash

    def wait_receipt(self, tx_hash: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """Синхронная обертка для асинхронного ожидания receipt"""
        try:
            # Создаем новый event loop если нужно
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Запускаем асинхронное ожидание
            return loop.run_until_complete(
                self._wait_receipt_async(tx_hash, timeout=timeout)
            )
            
        except Exception as e:
            logger.error(f"Ошибка при ожидании receipt: {e}")
            return None

    async def wait_receipt_async(self, tx_hash: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """Асинхронное ожидание receipt"""
        return await self._wait_receipt_async(tx_hash, timeout=timeout)

    def set_custom_gas_price(self, gas_price_gwei: float) -> None:
        """Установка кастомной цены газа"""
        self.custom_gas_price_gwei = gas_price_gwei
        logger.info(f"Установлена кастомная цена газа: {gas_price_gwei} gwei")


# Для обратной совместимости
DexSwapService = DexSwapServiceAsync
