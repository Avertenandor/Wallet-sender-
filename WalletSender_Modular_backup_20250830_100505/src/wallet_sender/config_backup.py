# WalletSender Modular Configuration

# Project Info
__version__ = "2.0.0"
__author__ = "Avertenandor"
__description__ = "Модульная версия WalletSender для массовой рассылки токенов BSC"

# Database
DATABASE_URL = "sqlite:///wallet_sender.db"

# Blockchain Networks
BSC_MAINNET_RPC = "https://bsc-dataseed.binance.org/"
BSC_TESTNET_RPC = "https://data-seed-prebsc-1-s1.binance.org:8545/"

# Default Gas Settings
DEFAULT_GAS_PRICE_GWEI = 0.1
DEFAULT_GAS_LIMIT = 21000

# API Keys (will be loaded from config.json)
BSCSCAN_API_KEYS = []

class Config:
    """Configuration class for WalletSender"""
    
    def __init__(self):
        self.version = __version__
        self.author = __author__
        self.description = __description__
        self.database_url = DATABASE_URL
        self.bsc_mainnet_rpc = BSC_MAINNET_RPC
        self.bsc_testnet_rpc = BSC_TESTNET_RPC
        self.default_gas_price_gwei = DEFAULT_GAS_PRICE_GWEI
        self.default_gas_limit = DEFAULT_GAS_LIMIT
        self.bscscan_api_keys = BSCSCAN_API_KEYS
    
    def get_rpc_url(self):
        """Get main RPC URL"""
        return self.bsc_mainnet_rpc

# Token Contracts (BSC Mainnet)
CONTRACTS = {
    "PLEX_ONE": "0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1",
    "USDT": "0x55d398326f99059ff775485246999027b3197955",
    "BNB": "0x0000000000000000000000000000000000000000"  # Native token
}

# PancakeSwap Router
PANCAKESWAP_ROUTER = "0x10ED43C718714eb63d5aA57B78B54704E256024E"

# UI Settings
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
WINDOW_TITLE = "WalletSender Modular v2.0"

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = "wallet_sender_modular.log"

# Backward-compatible accessor some modules may import
def get_config() -> Config:
    """Return a default Config instance (compat shim)."""
    return Config()
