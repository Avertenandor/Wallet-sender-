"""
Core модули WalletSender
"""

from .store import Store, get_store, close_store
from .rpc import RPCPool, get_rpc_pool, close_rpc_pool, get_web3, execute_with_retry
from .job_engine import (
    JobEngine, 
    get_job_engine, 
    close_job_engine,
    JobState,
    NonceManager,
    BaseExecutor,
    DistributionExecutor,
    AutoBuyExecutor,
    RewardsExecutor
)

# Существующие импорты для обратной совместимости
try:
    from .wallet_manager import WalletManager
except ImportError:
    WalletManager = None

try:
    from .web3_provider import Web3Provider
except ImportError:
    Web3Provider = None

__all__ = [
    # Store
    'Store',
    'get_store', 
    'close_store',
    
    # RPC
    'RPCPool',
    'get_rpc_pool',
    'close_rpc_pool',
    'get_web3',
    'execute_with_retry',
    
    # Job Engine
    'JobEngine',
    'get_job_engine',
    'close_job_engine',
    'JobState',
    'NonceManager',
    'BaseExecutor',
    'DistributionExecutor',
    'AutoBuyExecutor',
    'RewardsExecutor',
    
    # Legacy
    'WalletManager',
    'Web3Provider'
]
