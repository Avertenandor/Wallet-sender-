"""
Constants for WalletSender application.
This module centralizes network config, common ABIs, gas presets and known contract addresses
to avoid duplication and import errors across modules.
"""
from typing import Any, Dict, List, Tuple, Union

# Contract addresses (BSC)
CONTRACTS: Dict[str, str] = {
    'PLEX_ONE': '0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1',
    'USDT': '0x55d398326f99059ff775485246999027b3197955',
    'PANCAKESWAP_ROUTER': '0x10ed43c718714eb63d5aa57b78b54704e256024e',
    'WBNB': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'
}

# Backward-compatible single-name exports (some modules import these directly)
PLEX_CONTRACT = CONTRACTS['PLEX_ONE']
USDT_CONTRACT = CONTRACTS['USDT']

# BSC network configuration
BSC_MAINNET: Dict[str, Union[str, int]] = {
    'rpc_url': 'https://bsc-dataseed.binance.org/',
    'chain_id': 56,
    'currency_symbol': 'BNB',
    'block_explorer': 'https://bscscan.com'
}

# Default values
DEFAULT_GAS_PRICE: int = 5  # Gwei
DEFAULT_GAS_LIMIT: int = 21000
DEFAULT_SLIPPAGE: int = 2  # %

# Gas presets used by services
GAS_LIMITS: Dict[str, int] = {
    'transfer': 21000,
    'erc20_transfer': 100000,
    'approve': 100000
}

# API endpoints
BSCSCAN_API_URLS: List[str] = [
    'https://api.bscscan.com/api',
    'https://api.bscscan.com/api'
]

# Legacy aliases for backward compatibility
BSCSCAN_URL: str = 'https://api.etherscan.io/v2/api'  # Now using Etherscan V2 API
BSCSCAN_KEYS: List[str] = [
    'RF1Q8SCFHFD1EVAP5A4WCMIM4DREA7UNUH',
    'U89HXHR9Y26CHMWAA9JUZ17YK2AAXS65CZ', 
    'RAI3FTD9W53JPYZ2AHW8IBH9BXUC71NRH1'
]

# File paths
DB_PATH: str = 'wallet_sender.db'
LOGS_DIR: str = 'logs'
CONFIG_DIR: str = 'config'

# GUI settings
WINDOW_SIZE: Tuple[int, int] = (1400, 900)
TAB_TITLES: Dict[str, str] = {
    'analyze': '🔍 Анализ токенов',
    'search': '🔎 Поиск транзакций', 
    'rewards': '🎁 Награды',
    'tx_rewards': '💰 Награды за Tx',
    'direct_send': '📫 Прямая отправка',
    'mass_distribution': '⚽ Массовая рассылка',
    'mass_distribution2': '⚽ Массовая рассылка 2',
    'mass_distribution3': '⚽ Массовая рассылка 3',
    'queue': '📋 Очередь',
    'history': '📜 История',
    'found_tx': '🔍 Найденные Tx',
    'settings': '⚙️ Настройки',
    'auto_sales': '💰 Автопродажи',
    'auto_buy': '🛌 Автопокупки'
}

# Minimal ERC20 ABI used across services (read + basic write)
ERC20_ABI: List[Dict[str, Any]] = [
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "payable": False, "stateMutability": "view", "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "payable": False, "stateMutability": "nonpayable", "type": "function"},
    {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "payable": False, "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "payable": False, "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "payable": False, "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "payable": False, "stateMutability": "view", "type": "function"},
    {"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "payable": False, "stateMutability": "nonpayable", "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "payable": False, "stateMutability": "view", "type": "function"}
]
