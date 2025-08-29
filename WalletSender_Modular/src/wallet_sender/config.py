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
