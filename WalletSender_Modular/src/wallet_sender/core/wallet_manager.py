"""
Менеджер кошельков для работы с приватными ключами и мнемониками
"""

from typing import Optional, List, Dict, Any
from eth_account import Account
from web3 import Web3

from ..utils.logger import get_logger

logger = get_logger(__name__)

try:
    from mnemonic import Mnemonic
    MNEMONIC_AVAILABLE = True
except ImportError:
    MNEMONIC_AVAILABLE = False
    logger.warning("Библиотека mnemonic не установлена. Установите через: pip install mnemonic")


class WalletManager:
    """Менеджер для работы с кошельками"""
    
    def __init__(self):
        """Инициализация менеджера кошельков"""
        self.account: Optional[Account] = None
        self.address: Optional[str] = None
        self.private_key: Optional[str] = None
        
    def connect_with_private_key(self, private_key: str) -> bool:
        """
        Подключение кошелька через приватный ключ
        
        Args:
            private_key: Приватный ключ (с или без префикса 0x)
            
        Returns:
            bool: Успешность подключения
        """
        try:
            # Удаляем префикс 0x если есть
            if private_key.startswith('0x'):
                private_key = private_key[2:]
                
            # Создаем аккаунт из приватного ключа
            self.account = Account.from_key(private_key)
            self.address = self.account.address
            self.private_key = private_key
            
            logger.info(f"Кошелек подключен: {self.address}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения кошелька: {e}")
            self.disconnect()
            return False
            
    def connect_with_mnemonic(
        self, 
        mnemonic_phrase: str, 
        account_index: int = 0,
        passphrase: str = ""
    ) -> bool:
        """
        Подключение кошелька через мнемоническую фразу
        
        Args:
            mnemonic_phrase: Мнемоническая фраза (12 или 24 слова)
            account_index: Индекс аккаунта для деривации
            passphrase: Дополнительная парольная фраза (опционально)
            
        Returns:
            bool: Успешность подключения
        """
        try:
            if not MNEMONIC_AVAILABLE:
                logger.error("Библиотека mnemonic не установлена")
                return False
                
            # Создаем объект мнемоники
            mnemo = Mnemonic("english")
            
            # Проверяем валидность фразы
            if not mnemo.check(mnemonic_phrase):
                logger.error("Неверная мнемоническая фраза")
                return False
                
            # Генерируем seed из мнемоники
            seed = mnemo.to_seed(mnemonic_phrase, passphrase)
            
            # Получаем приватный ключ из seed (упрощенная версия)
            # В продакшене лучше использовать правильную HD деривацию
            private_key = seed[:32].hex()
            
            # Создаем аккаунт
            self.account = Account.from_key(private_key)
            self.address = self.account.address
            self.private_key = private_key
            
            logger.info(f"Кошелек подключен через мнемонику: {self.address}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения через мнемонику: {e}")
            self.disconnect()
            return False
            
    def create_new_wallet(self) -> Dict[str, str]:
        """
        Создание нового кошелька
        
        Returns:
            Dict: Информация о новом кошельке (address, private_key, mnemonic)
        """
        try:
            # Создаем новый аккаунт
            new_account = Account.create()
            
            result = {
                'address': new_account.address,
                'private_key': new_account.key.hex()
            }
            
            # Генерируем мнемонику если библиотека доступна
            if MNEMONIC_AVAILABLE:
                mnemo = Mnemonic("english")
                mnemonic = mnemo.generate(strength=128)  # 12 слов
                result['mnemonic'] = mnemonic
            else:
                result['mnemonic'] = None
                
            logger.info(f"Создан новый кошелек: {result['address']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка создания кошелька: {e}")
            return {}
            
    def disconnect(self):
        """Отключение кошелька"""
        self.account = None
        self.address = None
        self.private_key = None
        logger.info("Кошелек отключен")
        
    def is_connected(self) -> bool:
        """
        Проверка подключения кошелька
        
        Returns:
            bool: True если кошелек подключен
        """
        return self.account is not None
        
    def get_address(self) -> Optional[str]:
        """
        Получение адреса подключенного кошелька
        
        Returns:
            str: Адрес кошелька или None
        """
        return self.address
        
    def get_private_key(self) -> Optional[str]:
        """
        Получение приватного ключа подключенного кошелька
        
        Returns:
            str: Приватный ключ или None
        """
        return self.private_key
        
    def sign_message(self, message: str) -> Optional[str]:
        """
        Подпись сообщения
        
        Args:
            message: Сообщение для подписи
            
        Returns:
            str: Подпись или None
        """
        try:
            if not self.is_connected():
                logger.error("Кошелек не подключен")
                return None
                
            # Подписываем сообщение
            message_hash = Web3.keccak(text=message)
            signed = self.account.signHash(message_hash)
            
            signature = signed.signature.hex()
            logger.info(f"Сообщение подписано")
            
            return signature
            
        except Exception as e:
            logger.error(f"Ошибка подписи сообщения: {e}")
            return None
            
    def sign_transaction(self, transaction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Подпись транзакции
        
        Args:
            transaction: Транзакция для подписи
            
        Returns:
            Dict: Подписанная транзакция или None
        """
        try:
            if not self.is_connected():
                logger.error("Кошелек не подключен")
                return None
                
            # Подписываем транзакцию
            signed_tx = self.account.sign_transaction(transaction)
            
            return {
                'rawTransaction': signed_tx.rawTransaction,
                'hash': signed_tx.hash,
                'r': signed_tx.r,
                's': signed_tx.s,
                'v': signed_tx.v
            }
            
        except Exception as e:
            logger.error(f"Ошибка подписи транзакции: {e}")
            return None
            
    def validate_address(self, address: str) -> bool:
        """
        Проверка валидности адреса
        
        Args:
            address: Адрес для проверки
            
        Returns:
            bool: True если адрес валидный
        """
        try:
            return Web3.is_address(address)
        except Exception:
            return False
            
    def validate_private_key(self, private_key: str) -> bool:
        """
        Проверка валидности приватного ключа
        
        Args:
            private_key: Приватный ключ для проверки
            
        Returns:
            bool: True если ключ валидный
        """
        try:
            # Удаляем префикс 0x если есть
            if private_key.startswith('0x'):
                private_key = private_key[2:]
                
            # Пробуем создать аккаунт
            Account.from_key(private_key)
            return True
            
        except Exception:
            return False
            
    def validate_mnemonic(self, mnemonic_phrase: str) -> bool:
        """
        Проверка валидности мнемонической фразы
        
        Args:
            mnemonic_phrase: Мнемоническая фраза для проверки
            
        Returns:
            bool: True если фраза валидная
        """
        try:
            if not MNEMONIC_AVAILABLE:
                logger.warning("Библиотека mnemonic не установлена")
                return False
                
            mnemo = Mnemonic("english")
            return mnemo.check(mnemonic_phrase)
            
        except Exception:
            return False
            
    def generate_mnemonic(self, strength: int = 128) -> Optional[str]:
        """
        Генерация новой мнемонической фразы
        
        Args:
            strength: Сила энтропии (128 = 12 слов, 256 = 24 слова)
            
        Returns:
            str: Мнемоническая фраза или None
        """
        try:
            if not MNEMONIC_AVAILABLE:
                logger.error("Библиотека mnemonic не установлена")
                return None
                
            mnemo = Mnemonic("english")
            mnemonic = mnemo.generate(strength=strength)
            
            logger.info(f"Сгенерирована мнемоническая фраза ({strength // 32 * 3} слов)")
            
            return mnemonic
            
        except Exception as e:
            logger.error(f"Ошибка генерации мнемоники: {e}")
            return None
