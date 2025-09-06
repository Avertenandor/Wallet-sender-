# Changelog

## v2.2.0 (2025-01-29) - Critical Fixes & Stability Update

### Major Fixes:
- **Fixed Auto-Buy Tab**: Complete overhaul of Web3 connection, wallet connection, and balance retrieval
- **Fixed Auto-Sales Tab**: Enhanced with multiple RPC endpoints and BIP44 derivation path
- **Fixed Mass Distribution Tabs**: All 3 mass distribution slots now work independently with proper Web3 connections
- **Enhanced Web3 Connectivity**: Multiple RPC endpoints with fallback mechanisms for all tabs
- **Improved Wallet Connection**: BIP44 derivation path support for seed phrases across all tabs

### Core Improvements:
- **Multiple RPC Endpoints**: Added 10+ BSC RPC endpoints for maximum reliability
- **BIP44 Derivation Path**: Proper m/44'/60'/0'/0/0 derivation for Ethereum/BSC wallets
- **Contract Validation**: Added contract existence checks before balance retrieval
- **Checksum Addresses**: Proper address formatting for all blockchain operations
- **Debug Tools**: Added balance diagnostic buttons to all wallet-connected tabs

### Technical Details:
- **Web3 Connection**: Timeout handling (10s) and automatic reconnection
- **Balance Retrieval**: Enhanced error handling and contract validation
- **Wallet Management**: Support for both private keys and seed phrases
- **Error Handling**: Comprehensive try-catch blocks with detailed logging
- **UI Enhancements**: Debug buttons and improved status indicators

### Fixed Components:
- ✅ Auto-Buy Tab: Web3, wallet connection, balance retrieval
- ✅ Auto-Sales Tab: Enhanced stability and reliability  
- ✅ Mass Distribution Tab 1: Independent operation
- ✅ Mass Distribution Tab 2: Independent operation
- ✅ Mass Distribution Tab 3: Independent operation
- ✅ All tabs now support simultaneous operation without conflicts

## v2.1.0 (2025-01-01) - Stability & Parallelism Update

### Major Features:
- **Unified NonceManager**: Removed duplicate NonceManager from job_engine.py, now using advanced ticket-based system from nonce_manager.py
- **JobRouter Service**: Centralized job management with tag-based grouping for better control
- **API Rate Limiter Integration**: Global rate limiting with token bucket algorithm for API calls
- **BscScan Service Rewrite**: Integrated with core API client and rate limiter for stability
- **Enhanced Status Bar**: Real-time indicators for Queue, RPC, and API status

### Core Improvements:
- **NonceManager**: Ticket-based reservation system with automatic cleanup and resync on errors
- **JobEngine**: Now uses global NonceManager instance with proper ticket lifecycle
- **BscScanClient**: V2 API support with automatic key rotation and backoff strategies
- **ApiRateLimiter**: Per-key and global rate limits with burst support

### Configuration Updates:
- Added `api.rate_limit` section for fine-tuned API control
- Added `rpc.list` with multiple BSC endpoints for failover
- Added `txqueue` settings for parallel transaction processing
- Version bumped to 2.1.0

### UI Enhancements:
- Queue status indicator (queued/running/failed)
- RPC endpoint display with current node
- API rate limiter status with RPS counter
- Status updates every second for real-time monitoring

### Services:
- **job_router.py**: Submit and manage distribution, auto-buy, auto-sell, and reward tasks
- **bscscan_service.py**: Unified API access with automatic rate limiting and key rotation

### Technical Details:
- Migrated to Etherscan V2 API (chainid=56 for BSC)
- Implemented token bucket algorithm for rate limiting
- Added automatic nonce resync on "too low/high" errors
- Support for parallel RPC operations with per-address serialization

## v2.0.1 (2025-08-31)

Improvements:

- UI: Dark theme enabled by default (qdarkstyle + Fusion).
- PyQt compatibility: safe fallbacks for QFont weight, Qt.Alignment and QSplitter orientation (PyQt5/6).
- Analysis: slot signature aligned with signal to avoid runtime errors.
- Rewards: added `_update_rewards_table` slot to reflect changes in UI.
- History: restored `log_message` via BaseTab for backward compatibility; tab loads reliably.

Notes:

- Minor warnings from third-party packages (setuptools/pkg_resources) do not affect functionality.
- Further polishing planned for HistoryTab status bar messages and actions.
