"""
BSC Scan API integration with key rotation and rate limiting.
"""
import asyncio
import aiohttp
import time
import logging
from typing import Dict, Any, List, Optional
import json

logger = logging.getLogger(__name__)

class BSCScanAPI:
    def __init__(self, api_keys: List[str]):
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
        
        params['apikey'] = self.get_current_key()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.bscscan.com/api', params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == '1':
                            self.last_request_time = time.time()
                            return data
                        else:
                            logger.warning(f"API error: {data.get('message', 'Unknown error')}")
                            return None
                    else:
                        logger.error(f"HTTP {response.status}: {await response.text()}")
                        self.rotate_key()
                        return None
        except Exception as e:
            logger.error(f"Request failed: {e}")
            self.rotate_key()
            return None
    
    async def get_token_transactions(self, contract_address: str, page: int = 1, offset: int = 100) -> Optional[List[Dict]]:
        """Get token transactions"""
        params = {
            'module': 'account',
            'action': 'tokentx',
            'contractaddress': contract_address,
            'page': page,
            'offset': offset,
            'sort': 'desc'
        }
        
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
