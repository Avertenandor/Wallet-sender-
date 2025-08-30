"""
Etherscan API V2 integration with BSC support and key rotation.
Migrated from BSCScan V1 to Etherscan V2 API (August 2025)
"""
import asyncio
import aiohttp
import time
import logging
from typing import Dict, Any, List, Optional
import json

logger = logging.getLogger(__name__)

class EtherscanAPI:
    """
    Etherscan V2 API client for BSC (Binance Smart Chain)
    Supports multichain API with chainid parameter
    """
    
    # Base URL for Etherscan V2 API
    BASE_URL = "https://api.etherscan.io/v2/api"
    BSC_CHAIN_ID = 56  # Binance Smart Chain ID
    
    def __init__(self, api_keys: List[str]):
        """
        Initialize with list of Etherscan API keys
        Note: These should be Etherscan keys, not BSCScan keys
        """
        self.api_keys = api_keys
        self.current_key_index = 0
        self.last_request_time = 0
        self.min_interval = 0.2  # 5 requests per second max
        
    def get_current_key(self) -> str:
        """Get current API key"""
        return self.api_keys[self.current_key_index]
    
    def rotate_key(self):
        """Rotate to next API key"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        logger.info(f"Rotated to API key #{self.current_key_index + 1}")
    
    async def make_request(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make API request with rate limiting and key rotation"""
        # Rate limiting
        now = time.time()
        if now - self.last_request_time < self.min_interval:
            await asyncio.sleep(self.min_interval - (now - self.last_request_time))
        
        # Add required parameters for V2 API
        params['chainid'] = self.BSC_CHAIN_ID
        params['apikey'] = self.get_current_key()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == '1':
                            self.last_request_time = time.time()
                            return data
                        else:
                            error_msg = data.get('message', 'Unknown error')
                            logger.warning(f"API error: {error_msg}")
                            # Check for migration-related errors
                            if 'migrate' in error_msg.lower() or 'v2' in error_msg.lower():
                                logger.error("BSCScan V1 API is deprecated. Using Etherscan V2 API.")
                            return None
                    else:
                        logger.error(f"HTTP {response.status}: {await response.text()}")
                        self.rotate_key()
                        return None
        except Exception as e:
            logger.error(f"Request failed: {e}")
            self.rotate_key()
            return None
    
    async def get_token_transactions(self, contract_address: str, address: str = None, 
                                    page: int = 1, offset: int = 100) -> Optional[List[Dict]]:
        """Get token transactions for a contract or address"""
        params = {
            'module': 'account',
            'action': 'tokentx',
            'contractaddress': contract_address,
            'page': page,
            'offset': offset,
            'sort': 'desc'
        }
        
        # Add address filter if provided
        if address:
            params['address'] = address
        
        result = await self.make_request(params)
        if result and 'result' in result:
            return result['result']
        return None
    
    async def get_balance(self, address: str) -> Optional[float]:
        """Get BNB balance"""
        params = {
            'module': 'account',
            'action': 'balance',
            'address': address,
            'tag': 'latest'
        }
        
        result = await self.make_request(params)
        if result and 'result' in result:
            # Convert Wei to BNB
            return int(result['result']) / 10**18
        return None
    
    async def get_token_balance(self, address: str, contract_address: str) -> Optional[float]:
        """Get token balance"""
        params = {
            'module': 'account',
            'action': 'tokenbalance',
            'contractaddress': contract_address,
            'address': address,
            'tag': 'latest'
        }
        
        result = await self.make_request(params)
        if result and 'result' in result:
            # Assuming 18 decimals for most tokens
            return int(result['result']) / 10**18
        return None
    
    async def get_block_by_timestamp(self, timestamp: int, closest: str = 'before') -> Optional[int]:
        """Get block number by timestamp"""
        params = {
            'module': 'block',
            'action': 'getblocknobytime',
            'timestamp': timestamp,
            'closest': closest
        }
        
        result = await self.make_request(params)
        if result and 'result' in result:
            return int(result['result'])
        return None
    
    async def get_latest_block(self) -> Optional[int]:
        """Get latest block number using proxy module"""
        params = {
            'module': 'proxy',
            'action': 'eth_blockNumber'
        }
        
        result = await self.make_request(params)
        if result and 'result' in result:
            # Convert from hex to int
            return int(result['result'], 16)
        return None
    
    async def get_event_logs(self, from_block: int, to_block: int, 
                           address: str = None, topics: List[str] = None) -> Optional[List[Dict]]:
        """Get event logs"""
        params = {
            'module': 'logs',
            'action': 'getLogs',
            'fromBlock': from_block,
            'toBlock': to_block
        }
        
        if address:
            params['address'] = address
        
        if topics:
            for i, topic in enumerate(topics):
                if topic:
                    params[f'topic{i}'] = topic
        
        result = await self.make_request(params)
        if result and 'result' in result:
            return result['result']
        return None
    
    async def get_token_holders(self, contract_address: str, page: int = 1, offset: int = 100) -> Optional[List[Dict]]:
        """Get token holders list (V2 API feature)"""
        params = {
            'module': 'token',
            'action': 'tokenholderlist',
            'contractaddress': contract_address,
            'page': page,
            'offset': offset
        }
        
        result = await self.make_request(params)
        if result and 'result' in result:
            return result['result']
        return None
    
    async def get_token_info(self, contract_address: str) -> Optional[Dict]:
        """Get token information (V2 API feature)"""
        params = {
            'module': 'token',
            'action': 'tokeninfo',
            'contractaddress': contract_address
        }
        
        result = await self.make_request(params)
        if result and 'result' in result:
            return result['result']
        return None


# Backward compatibility alias
BSCScanAPI = EtherscanAPI
