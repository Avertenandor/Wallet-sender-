#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Etherscan V2 API
"""

import asyncio
import sys
from pathlib import Path

# Add src to Python path
current_dir = Path(__file__).parent
src_path = current_dir / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from wallet_sender.api.etherscan import EtherscanAPI


async def test_api():
    """Test Etherscan V2 API functionality"""
    
    # API keys
    api_keys = [
        "RF1Q8SCFHFD1EVAP5A4WCMIM4DREA7UNUH",
        "U89HXHR9Y26CHMWAA9JUZ17YK2AAXS65CZ",
        "RAI3FTD9W53JPYZ2AHW8IBH9BXUC71NRH1"
    ]
    
    # Initialize API
    api = EtherscanAPI(api_keys)
    
    print("=" * 60)
    print("Testing Etherscan V2 API for BSC")
    print("=" * 60)
    
    # Test 1: Get latest block
    print("\n1. Testing get_latest_block()...")
    block = await api.get_latest_block()
    if block:
        print(f"✅ Latest block: {block}")
    else:
        print("❌ Failed to get latest block")
    
    # Test 2: Get BNB balance
    print("\n2. Testing get_balance()...")
    test_address = "0x0000000000000000000000000000000000000000"
    balance = await api.get_balance(test_address)
    if balance is not None:
        print(f"✅ Balance for {test_address[:10]}...: {balance} BNB")
    else:
        print("❌ Failed to get balance")
    
    # Test 3: Get token balance (USDT)
    print("\n3. Testing get_token_balance() for USDT...")
    usdt_contract = "0x55d398326f99059ff775485246999027b3197955"
    token_balance = await api.get_token_balance(test_address, usdt_contract)
    if token_balance is not None:
        print(f"✅ USDT balance: {token_balance}")
    else:
        print("❌ Failed to get token balance")
    
    # Test 4: Get block by timestamp
    print("\n4. Testing get_block_by_timestamp()...")
    import time
    timestamp = int(time.time()) - 3600  # 1 hour ago
    block_by_time = await api.get_block_by_timestamp(timestamp)
    if block_by_time:
        print(f"✅ Block at timestamp {timestamp}: {block_by_time}")
    else:
        print("❌ Failed to get block by timestamp")
    
    # Test 5: Get token holders (PLEX)
    print("\n5. Testing get_token_holders() for PLEX...")
    plex_contract = "0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1"
    holders = await api.get_token_holders(plex_contract, page=1, offset=5)
    if holders:
        print(f"✅ Found {len(holders)} token holders")
        for holder in holders[:3]:
            print(f"   - {holder.get('TokenHolderAddress', 'N/A')}: {holder.get('TokenHolderQuantity', 'N/A')}")
    else:
        print("❌ Failed to get token holders")
    
    # Test 6: Get token info
    print("\n6. Testing get_token_info() for PLEX...")
    token_info = await api.get_token_info(plex_contract)
    if token_info:
        print(f"✅ Token info:")
        print(f"   - Name: {token_info.get('tokenName', 'N/A')}")
        print(f"   - Symbol: {token_info.get('symbol', 'N/A')}")
        print(f"   - Decimals: {token_info.get('divisor', 'N/A')}")
    else:
        print("❌ Failed to get token info")
    
    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_api())
