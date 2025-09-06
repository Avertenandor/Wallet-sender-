#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test imports and basic functionality
"""

import sys
from pathlib import Path

# Add src to Python path
current_dir = Path(__file__).parent
src_path = current_dir / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

def test_imports():
    """Test all critical imports"""
    print("=" * 60)
    print("Testing imports for WalletSender Modular")
    print("=" * 60)
    
    errors = []
    
    # Test core imports
    print("\n1. Testing core imports...")
    try:
        from wallet_sender.config import get_config, ConfigManager
        print("✅ config.py")
    except Exception as e:
        errors.append(f"config.py: {e}")
        print(f"❌ config.py: {e}")
    
    try:
        from wallet_sender.constants import PLEX_CONTRACT, USDT_CONTRACT, ERC20_ABI
        print("✅ constants.py")
    except Exception as e:
        errors.append(f"constants.py: {e}")
        print(f"❌ constants.py: {e}")
    
    # Test core modules
    print("\n2. Testing core modules...")
    try:
        from wallet_sender.core.web3_provider import Web3Provider
        print("✅ core/web3_provider.py")
    except Exception as e:
        errors.append(f"core/web3_provider.py: {e}")
        print(f"❌ core/web3_provider.py: {e}")
    
    try:
        from wallet_sender.core.wallet_manager import WalletManager
        print("✅ core/wallet_manager.py")
    except Exception as e:
        errors.append(f"core/wallet_manager.py: {e}")
        print(f"❌ core/wallet_manager.py: {e}")
    
    # Test services
    print("\n3. Testing services...")
    try:
        from wallet_sender.services.token_service import TokenService
        print("✅ services/token_service.py")
    except Exception as e:
        errors.append(f"services/token_service.py: {e}")
        print(f"❌ services/token_service.py: {e}")
    
    try:
        from wallet_sender.services.transaction_service import TransactionService
        print("✅ services/transaction_service.py")
    except Exception as e:
        errors.append(f"services/transaction_service.py: {e}")
        print(f"❌ services/transaction_service.py: {e}")
    
    try:
        from wallet_sender.services.bscscan_service import BSCScanService
        print("✅ services/bscscan_service.py")
    except Exception as e:
        errors.append(f"services/bscscan_service.py: {e}")
        print(f"❌ services/bscscan_service.py: {e}")
    
    # Test API modules
    print("\n4. Testing API modules...")
    try:
        from wallet_sender.api.etherscan import EtherscanAPI
        print("✅ api/etherscan.py")
    except Exception as e:
        errors.append(f"api/etherscan.py: {e}")
        print(f"❌ api/etherscan.py: {e}")
    
    try:
        from wallet_sender.api.bscscan import BSCScanAPI
        print("✅ api/bscscan.py")
    except Exception as e:
        errors.append(f"api/bscscan.py: {e}")
        print(f"❌ api/bscscan.py: {e}")
    
    # Test database
    print("\n5. Testing database...")
    try:
        from wallet_sender.database.database import DatabaseManager
        print("✅ database/database.py")
    except Exception as e:
        errors.append(f"database/database.py: {e}")
        print(f"❌ database/database.py: {e}")
    
    try:
        from wallet_sender.database.models import Base, MassDistribution
        print("✅ database/models.py")
    except Exception as e:
        errors.append(f"database/models.py: {e}")
        print(f"❌ database/models.py: {e}")
    
    # Test UI tabs
    print("\n6. Testing UI tabs...")
    try:
        from wallet_sender.ui.tabs import BaseTab
        print("✅ ui/tabs/base_tab.py")
    except Exception as e:
        errors.append(f"ui/tabs/base_tab.py: {e}")
        print(f"❌ ui/tabs/base_tab.py: {e}")
    
    try:
        from wallet_sender.ui.tabs import MassDistributionTab
        print("✅ ui/tabs/mass_distribution_tab.py")
    except Exception as e:
        errors.append(f"ui/tabs/mass_distribution_tab.py: {e}")
        print(f"❌ ui/tabs/mass_distribution_tab.py: {e}")
    
    try:
        from wallet_sender.ui.tabs import DirectSendTab
        print("✅ ui/tabs/direct_send_tab.py")
    except Exception as e:
        errors.append(f"ui/tabs/direct_send_tab.py: {e}")
        print(f"❌ ui/tabs/direct_send_tab.py: {e}")
    
    try:
        from wallet_sender.ui.tabs import SettingsTab
        print("✅ ui/tabs/settings_tab.py")
    except Exception as e:
        errors.append(f"ui/tabs/settings_tab.py: {e}")
        print(f"❌ ui/tabs/settings_tab.py: {e}")
    
    # Test utils
    print("\n7. Testing utils...")
    try:
        from wallet_sender.utils.logger import setup_logger, get_logger
        print("✅ utils/logger.py")
    except Exception as e:
        errors.append(f"utils/logger.py: {e}")
        print(f"❌ utils/logger.py: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"❌ Found {len(errors)} import errors:")
        for err in errors:
            print(f"   - {err}")
        return False
    else:
        print("✅ All imports successful!")
        return True
    print("=" * 60)


def test_config():
    """Test configuration loading"""
    print("\n" + "=" * 60)
    print("Testing configuration")
    print("=" * 60)
    
    try:
        from wallet_sender.config import get_config
        config = get_config()
        
        print(f"✅ Config loaded successfully")
        print(f"   - Etherscan API keys: {len(config.etherscan_api_keys)} keys")
        print(f"   - Network: {config.get('network')}")
        print(f"   - RPC URL: {config.get_rpc_url()}")
        print(f"   - Database URL: {config.database_url}")
        
        return True
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False


def test_web3_connection():
    """Test Web3 connection"""
    print("\n" + "=" * 60)
    print("Testing Web3 connection")
    print("=" * 60)
    
    try:
        from wallet_sender.core.web3_provider import Web3Provider
        
        provider = Web3Provider()
        
        if provider.w3 and provider.w3.is_connected():
            print("✅ Connected to BSC")
            print(f"   - Latest block: {provider.w3.eth.block_number}")
            print(f"   - Chain ID: {provider.w3.eth.chain_id}")
            return True
        else:
            print("❌ Failed to connect to BSC")
            return False
            
    except Exception as e:
        print(f"❌ Web3 error: {e}")
        return False


if __name__ == "__main__":
    print("\n🚀 Starting WalletSender Modular tests...")
    
    # Run tests
    imports_ok = test_imports()
    config_ok = test_config()
    web3_ok = test_web3_connection()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Imports: {'✅ OK' if imports_ok else '❌ FAILED'}")
    print(f"Config: {'✅ OK' if config_ok else '❌ FAILED'}")
    print(f"Web3: {'✅ OK' if web3_ok else '❌ FAILED'}")
    
    if imports_ok and config_ok:
        print("\n✅ Basic functionality is working!")
        print("The application should be able to start.")
    else:
        print("\n❌ There are critical errors that need to be fixed.")
    
    print("=" * 60)
