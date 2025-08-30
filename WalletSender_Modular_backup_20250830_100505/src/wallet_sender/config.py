"""
Configuration management for WalletSender application
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, List
from copy import deepcopy

# Project Info
__version__ = "2.0.0"
__author__ = "Avertenandor"
__description__ = "Модульная версия WalletSender для массовой рассылки токенов BSC"

# Default configuration
DEFAULT_CONFIG = {
    "network": "bsc_mainnet",
    "autosave": True,
    "confirm_operations": True,
    "sound_notifications": False,
    "rpc_urls": {
        "bsc_mainnet": "https://bsc-dataseed.binance.org/",
        "bsc_testnet": "https://data-seed-prebsc-1-s1.binance.org:8545/"
    },
    "additional_rpcs": [],
    "connection_timeout": 30,
    "retry_count": 3,
    "auto_switch_rpc": True,
    "gas_settings": {
        "default_gas_price": 5,
        "default_gas_limit": 100000,
        "max_gas_price": 50,
        "auto_estimate": False,
        "use_eip1559": False
    },
    "tokens": {
        "PLEX_ONE": "0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1",
        "USDT": "0x55d398326f99059ff775485246999027b3197955",
        "WBNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
    },
    "pancakeswap_router": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
    "slippage": 2.0,
    "bscscan_api_keys": [],
    "api_rate_limit": 5,
    "rotate_api_keys": True,
    "ui": {
        "window_width": 1400,
        "window_height": 900,
        "theme": "dark",
        "language": "ru",
        "show_tooltips": True,
        "minimize_to_tray": False,
        "start_minimized": False,
        "table_row_height": 30,
        "alternating_row_colors": True
    },
    "logging": {
        "level": "INFO",
        "file": "wallet_sender.log",
        "max_size": 10485760,
        "backup_count": 5,
        "log_to_console": True,
        "log_transactions": True,
        "log_api_calls": False
    },
    "database": {
        "url": "sqlite:///wallet_sender.db",
        "echo": False
    },
    "rewards": {
        "enabled": False,
        "min_amount": 0.01,
        "reward_percentage": 1.0
    },
    "security": {
        "encrypt_keys": True,
        "auto_lock": False,
        "auto_lock_minutes": 30,
        "clear_clipboard": True,
        "verify_addresses": True,
        "tx_limit_enabled": False,
        "tx_limit_amount": 100,
        "auto_backup": False,
        "backup_path": "./backups"
    },
    "profiles": {}
}

# Legacy constants for backward compatibility
DATABASE_URL = "sqlite:///wallet_sender.db"
BSC_MAINNET_RPC = "https://bsc-dataseed.binance.org/"
BSC_TESTNET_RPC = "https://data-seed-prebsc-1-s1.binance.org:8545/"
DEFAULT_GAS_PRICE_GWEI = 5
DEFAULT_GAS_LIMIT = 100000
BSCSCAN_API_KEYS = []


class ConfigManager:
    """
    Configuration manager with JSON file persistence
    """
    
    def __init__(self, config_file: str = "config.json"):
        """
        Initialize configuration manager
        
        Args:
            config_file: Path to configuration file
        """
        # Get the directory where the module is located
        module_dir = Path(__file__).parent.parent.parent  # Go up to WalletSender_Modular
        self.config_file = module_dir / config_file
        self.config: Dict[str, Any] = {}
        self.defaults = deepcopy(DEFAULT_CONFIG)
        self.load()
        
    def load(self) -> None:
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    self.config = self._merge_configs(deepcopy(self.defaults), loaded_config)
            else:
                # Use defaults if file doesn't exist
                self.config = deepcopy(self.defaults)
                self.save()  # Create the file with defaults
        except Exception as e:
            print(f"Error loading config: {e}")
            self.config = deepcopy(self.defaults)
            
    def save(self) -> None:
        """Save configuration to file"""
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")
            
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key (supports nested keys with dots)
        
        Args:
            key: Configuration key (e.g., 'ui.theme' for nested)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
        
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value by key (supports nested keys with dots)
        
        Args:
            key: Configuration key (e.g., 'ui.theme' for nested)
            value: Value to set
        """
        keys = key.split('.')
        config = self.config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        # Set the value
        config[keys[-1]] = value
        
        # Auto-save if enabled
        if self.get('autosave', True):
            self.save()
            
    def reset_to_defaults(self) -> None:
        """Reset configuration to default values"""
        self.config = deepcopy(self.defaults)
        self.save()
        
    def _merge_configs(self, base: Dict, update: Dict) -> Dict:
        """
        Recursively merge two configuration dictionaries
        
        Args:
            base: Base configuration
            update: Configuration to merge
            
        Returns:
            Merged configuration
        """
        for key, value in update.items():
            if key in base:
                if isinstance(base[key], dict) and isinstance(value, dict):
                    base[key] = self._merge_configs(base[key], value)
                else:
                    base[key] = value
            else:
                base[key] = value
                
        return base
        
    # Legacy properties for backward compatibility
    @property
    def version(self) -> str:
        return __version__
        
    @property
    def author(self) -> str:
        return __author__
        
    @property
    def description(self) -> str:
        return __description__
        
    @property
    def database_url(self) -> str:
        return self.get('database.url', DATABASE_URL)
        
    @property
    def bsc_mainnet_rpc(self) -> str:
        return self.get('rpc_urls.bsc_mainnet', BSC_MAINNET_RPC)
        
    @property
    def bsc_testnet_rpc(self) -> str:
        return self.get('rpc_urls.bsc_testnet', BSC_TESTNET_RPC)
        
    @property
    def default_gas_price_gwei(self) -> float:
        return self.get('gas_settings.default_gas_price', DEFAULT_GAS_PRICE_GWEI)
        
    @property
    def default_gas_limit(self) -> int:
        return self.get('gas_settings.default_gas_limit', DEFAULT_GAS_LIMIT)
        
    @property
    def bscscan_api_keys(self) -> List[str]:
        return self.get('bscscan_api_keys', [])
        
    def get_rpc_url(self) -> str:
        """Get current RPC URL based on selected network"""
        network = self.get('network', 'bsc_mainnet')
        return self.get(f'rpc_urls.{network}', BSC_MAINNET_RPC)


# Legacy Config class for backward compatibility
class Config:
    """Legacy configuration class for backward compatibility"""
    
    def __init__(self):
        self._manager = ConfigManager()
        
    def __getattr__(self, name):
        # Delegate to ConfigManager
        return getattr(self._manager, name)
        

# Global configuration instance
_config_instance: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """
    Get global configuration instance
    
    Returns:
        ConfigManager instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance


# Token Contracts (BSC Mainnet) - for backward compatibility
CONTRACTS = {
    "PLEX_ONE": "0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1",
    "USDT": "0x55d398326f99059ff775485246999027b3197955",
    "BNB": "0x0000000000000000000000000000000000000000"  # Native token
}

# PancakeSwap Router
PANCAKESWAP_ROUTER = "0x10ED43C718714eb63d5aA57B78B54704E256024E"

# UI Settings
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
WINDOW_TITLE = "WalletSender Modular v2.0"

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = "wallet_sender_modular.log"
