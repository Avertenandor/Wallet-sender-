"""
BSC Scan API - Wrapper for Etherscan V2 API
Migrated to Etherscan V2 API (August 2025)
Provides backward compatibility for existing code
"""
import logging
from typing import List
from .etherscan import EtherscanAPI

logger = logging.getLogger(__name__)

class BSCScanAPI(EtherscanAPI):
    """
    BSCScan API wrapper - redirects to Etherscan V2 API
    BSCScan V1 API was deprecated on August 15, 2025
    This class provides backward compatibility
    """
    
    def __init__(self, api_keys: List[str]):
        """
        Initialize with API keys
        Note: These should be Etherscan keys (not BSCScan) for V2 API
        """
        logger.info("BSCScan API initialized - using Etherscan V2 API for BSC")
        super().__init__(api_keys)
        
    async def get_token_transactions(self, contract_address: str, page: int = 1, offset: int = 100):
        """Get token transactions - wrapper for compatibility"""
        # Call parent method with address=None for backward compatibility
        return await super().get_token_transactions(
            contract_address=contract_address,
            address=None,
            page=page,
            offset=offset
        )


# Migration helper function
def migrate_api_keys(old_bscscan_keys: List[str]) -> List[str]:
    """
    Helper to remind about key migration
    BSCScan keys don't work with Etherscan V2 API
    """
    logger.warning("BSCScan API keys need to be replaced with Etherscan API keys")
    logger.warning("Please get new keys from https://etherscan.io/apis")
    logger.warning("The same Etherscan key works for all chains including BSC")
    return old_bscscan_keys  # Return as-is, but they won't work
