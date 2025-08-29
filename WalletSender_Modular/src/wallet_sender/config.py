"""
Конфигурация приложения WalletSender
"""

import os
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from .utils.logger import get_logger

logger = get_logger(__name__)

# Версия приложения
__version__ = "2.0.0"
__author__ = "Production Team"
__description__ = "Модульная версия WalletSender для массовой рассылки токенов BSC"


class Config:
    """Класс для управления конфигурацией приложения"""
    
    # Путь к файлу конфигурации
    CONFIG_FILE = "config.json"
    
    # Значения по умолчанию
    DEFAULTS = {
        # Сеть
        "network": "bsc_mainnet",
        "rpc_urls": {
            "bsc_mainnet": "https://bsc-dataseed.binance.org/",
            "bsc_testnet": "https://data-seed-prebsc-1-s1.binance.org:8545/"
        },
        
        # Газ
        "gas_settings": {
            "default_gas_price": 5,  # Gwei
            "default_gas_limit": 100000,
            "max_gas_price": 50
        },
        
        # Токены
        "tokens": {
            "PLEX_ONE": "0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1",
            "USDT": "0x55d398326f99059ff775485246999027b3197955",
            "WBNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
        },
        
        # PancakeSwap
        "pancakeswap_router": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
        
        # API ключи
        "bscscan_api_keys": [],
        
        # UI настройки
        "ui": {
            "window_width": 1400,
            "window_height": 900,
            "theme": "dark",
            "language": "ru"
        },
        
        # Логирование
        "logging": {
            "level": "INFO",
            "file": "wallet_sender.log",
            "max_size": 10485760,  # 10 MB
            "backup_count": 5
        },
        
        # База данных
        "database": {
            "url": "sqlite:///wallet_sender.db",
            "echo": False
        },
        
        # Награды
        "rewards": {
            "enabled": False,
            "min_amount": 0.01,
            "reward_percentage": 1.0
        },
        
        # Безопасность
        "security": {
            "encrypt_keys": True,
            "auto_lock_minutes": 30
        }
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Инициализация конфигурации
        
        Args:
            config_file: Путь к файлу конфигурации
        """
        self.config_file = config_file or self.CONFIG_FILE
        self.config_path = Path(self.config_file)
        self.config = self.DEFAULTS.copy()
        
        # Загрузка конфигурации из файла
        self.load()
        
    def load(self) -> bool:
        """
        Загрузка конфигурации из файла
        
        Returns:
            bool: Успешность загрузки
        """
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    
                # Обновляем конфигурацию загруженными значениями
                self._deep_update(self.config, loaded_config)
                
                logger.info(f"Конфигурация загружена из {self.config_file}")
                return True
            else:
                logger.info(f"Файл конфигурации не найден, используются значения по умолчанию")
                self.save()  # Сохраняем дефолтную конфигурацию
                return False
                
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            return False
            
    def save(self) -> bool:
        """
        Сохранение конфигурации в файл
        
        Returns:
            bool: Успешность сохранения
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
                
            logger.info(f"Конфигурация сохранена в {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}")
            return False
            
    def get(self, key: str, default: Any = None) -> Any:
        """
        Получение значения конфигурации
        
        Args:
            key: Ключ конфигурации (поддерживает точечную нотацию)
            default: Значение по умолчанию
            
        Returns:
            Значение конфигурации
        """
        try:
            # Поддержка точечной нотации (например, "gas_settings.default_gas_price")
            keys = key.split('.')
            value = self.config
            
            for k in keys:
                value = value[k]
                
            return value
            
        except (KeyError, TypeError):
            return default
            
    def set(self, key: str, value: Any) -> bool:
        """
        Установка значения конфигурации
        
        Args:
            key: Ключ конфигурации (поддерживает точечную нотацию)
            value: Новое значение
            
        Returns:
            bool: Успешность установки
        """
        try:
            # Поддержка точечной нотации
            keys = key.split('.')
            config = self.config
            
            # Навигация до предпоследнего ключа
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
                
            # Установка значения
            config[keys[-1]] = value
            
            # Автосохранение
            self.save()
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка установки конфигурации {key}: {e}")
            return False
            
    def _deep_update(self, base: Dict, update: Dict) -> Dict:
        """
        Глубокое обновление словаря
        
        Args:
            base: Базовый словарь
            update: Словарь с обновлениями
            
        Returns:
            Обновленный словарь
        """
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value
                
        return base
        
    def get_rpc_url(self, network: Optional[str] = None) -> str:
        """
        Получение RPC URL для сети
        
        Args:
            network: Название сети
            
        Returns:
            str: RPC URL
        """
        network = network or self.get("network", "bsc_mainnet")
        return self.get(f"rpc_urls.{network}", "https://bsc-dataseed.binance.org/")
        
    def get_token_address(self, token_name: str) -> Optional[str]:
        """
        Получение адреса токена
        
        Args:
            token_name: Название токена
            
        Returns:
            str: Адрес токена или None
        """
        return self.get(f"tokens.{token_name}")
        
    def get_bscscan_api_key(self) -> Optional[str]:
        """
        Получение API ключа BSCScan
        
        Returns:
            str: API ключ или None
        """
        keys = self.get("bscscan_api_keys", [])
        return keys[0] if keys else None
        
    def add_bscscan_api_key(self, api_key: str) -> bool:
        """
        Добавление API ключа BSCScan
        
        Args:
            api_key: API ключ
            
        Returns:
            bool: Успешность добавления
        """
        keys = self.get("bscscan_api_keys", [])
        if api_key not in keys:
            keys.append(api_key)
            return self.set("bscscan_api_keys", keys)
        return True
        
    def get_gas_settings(self) -> Dict[str, Any]:
        """
        Получение настроек газа
        
        Returns:
            Dict: Настройки газа
        """
        return self.get("gas_settings", self.DEFAULTS["gas_settings"])
        
    def get_ui_settings(self) -> Dict[str, Any]:
        """
        Получение настроек интерфейса
        
        Returns:
            Dict: Настройки UI
        """
        return self.get("ui", self.DEFAULTS["ui"])
        
    def reset_to_defaults(self) -> bool:
        """
        Сброс конфигурации к значениям по умолчанию
        
        Returns:
            bool: Успешность сброса
        """
        try:
            self.config = self.DEFAULTS.copy()
            return self.save()
        except Exception as e:
            logger.error(f"Ошибка сброса конфигурации: {e}")
            return False


# Глобальный экземпляр конфигурации
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """
    Получение глобального экземпляра конфигурации
    
    Returns:
        Config: Экземпляр конфигурации
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = Config()
        
    return _config_instance
