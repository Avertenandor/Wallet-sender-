"""
API module for blockchain interactions
Supports Etherscan V2 API for BSC and other chains
"""
from .etherscan import EtherscanAPI
from .bscscan import BSCScanAPI

__all__ = ['EtherscanAPI', 'BSCScanAPI']
