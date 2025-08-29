"""
Constants for WalletSender application.
"""

# Contract addresses (BSC)
CONTRACTS = {
    'PLEX_ONE': '0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1',
    'USDT': '0x55d398326f99059ff775485246999027b3197955',
    'PANCAKESWAP_ROUTER': '0x10ed43c718714eb63d5aa57b78b54704e256024e',
    'WBNB': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'
}

# BSC network configuration
BSC_MAINNET = {
    'rpc_url': 'https://bsc-dataseed.binance.org/',
    'chain_id': 56,
    'currency_symbol': 'BNB',
    'block_explorer': 'https://bscscan.com'
}

# Default values
DEFAULT_GAS_PRICE = 5  # Gwei
DEFAULT_GAS_LIMIT = 21000
DEFAULT_SLIPPAGE = 2  # %

# API endpoints
BSCSCAN_API_URLS = [
    'https://api.bscscan.com/api',
    'https://api.bscscan.com/api'
]

# File paths
DB_PATH = 'wallet_sender.db'
LOGS_DIR = 'logs'
CONFIG_DIR = 'config'

# Gas limits
GAS_LIMITS = {
    'transfer': 21000,
    'token_transfer': 100000,
    'approve': 50000,
    'swap': 300000
}

# ERC20 ABI
ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
]

# Контракты для совместимости
PLEX_CONTRACT = CONTRACTS['PLEX_ONE']
USDT_CONTRACT = CONTRACTS['USDT']

# GUI settings
WINDOW_SIZE = (1400, 900)
TAB_TITLES = {
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
