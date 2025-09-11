# Changelog

## v2.4.20 (2025-09-11) - Асинхронная обработка транзакций 🚀

### ИСПРАВЛЕНИЯ:
- **Устранены таймауты**: Транзакции больше не блокируют приложение на 300 секунд
- **Асинхронное ожидание**: Receipt ожидается асинхронно с короткими интервалами
- **Синхронизация nonce**: Автоматическая синхронизация с сетью перед каждой транзакцией
- **Обработка конфликтов**: Автоматическая ресинхронизация при ошибках nonce

### Технические улучшения:
- **dex_swap_service_async.py**: Новая асинхронная реализация
  - Таймаут уменьшен с 300 до 30 секунд
  - 10 попыток проверки с интервалом 3 секунды
  - ThreadPoolExecutor для неблокирующих операций
  - Кеширование последнего успешного nonce
  - Синхронизация nonce с latest и pending

### Изменения в логике:
- **Неблокирующее ожидание**: Приложение не зависает при ожидании транзакции
- **Таймаут не критичен**: Если транзакция не подтверждена за 30 сек - не считается ошибкой
- **Проверка мемпула**: Проверка наличия транзакции перед получением receipt
- **Детальное логирование**: Логи на каждом этапе обработки

### Обратная совместимость:
- Старый DexSwapService заменен на асинхронную версию
- Все существующие вызовы продолжат работать

## v2.4.19 (2025-09-11) - Критический патч стабильности 🔥

### КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ:
- **Устранен краш после 5 транзакций**: Приложение больше не закрывается внезапно
- **Обработчики ошибок**: Добавлены глобальные обработчики критических ошибок
- **Мониторинг памяти**: Автоматическая очистка при превышении 500 МБ
- **Логирование крашей**: Все критические ошибки сохраняются в crash_log.txt

### Новые функции:
- **stability_patch.py**: Модуль стабильности с патчами для:
  - DexSwapService: переподключение Web3 при потере соединения
  - AutoSalesTab: защита от крашей при ошибках продаж
  - Монитор памяти: проверка каждые 30 секунд

### Улучшения:
- **Retry логика**: 3 попытки отправки транзакций с экспоненциальной задержкой
- **Очистка памяти**: Автоматический gc.collect() после каждых 5 транзакций
- **Обработка сигналов**: SIGINT и SIGTERM для корректного завершения

### Технические детали:
- Добавлена зависимость: psutil>=5.9.0
- Патчи применяются динамически при запуске
- Логи крашей сохраняются с полным стеком вызовов

## v2.4.18 (2025-09-11) - Cache Management System

### New Features:
- **Cache Management Tab**: Added new "Maintenance" tab in Settings for cache management
- **Python Cache Cleaning**: Remove all __pycache__ folders and .pyc files
- **Database Cache Cleaning**: Clean temporary data and optimize database with VACUUM
- **Full Cache Cleaning**: Complete cleanup of all temporary files including logs
- **Cache Statistics**: Real-time display of cache sizes and file counts

### UI Improvements:
- **New Maintenance Tab**: Dedicated section for system maintenance
- **Visual Feedback**: Color-coded buttons for different cache operations
- **Statistics Display**: Shows Python cache, database size, and log files
- **Confirmation Dialogs**: Added safety prompts for destructive operations

### Technical Improvements:
- **Automatic Stats Update**: Cache statistics refresh on tab load
- **Size Formatting**: Human-readable size display (bytes, KB, MB)
- **Error Handling**: Comprehensive error handling for all cache operations
- **Path Resolution**: Using pathlib for cross-platform compatibility

### Performance:
- **Improved Load Times**: Clearing Python cache can improve module loading
- **Database Optimization**: VACUUM command optimizes SQLite database
- **Disk Space Recovery**: Automatic cleanup of temporary files

## v2.4.12 (2025-01-29) - Liquidity and Decimals Fix

### Fixed Issues:
- **Fixed "Zero quote result" error**: Resolved issue with liquidity checking for token swaps
- **Fixed PLEX ONE decimals**: Correctly handle PLEX ONE with 9 decimals instead of 18
- **Improved path finding**: Now tries multiple swap paths (direct and through intermediate tokens)
- **Better error messages**: More detailed logging for debugging swap issues

### Technical Improvements:
- **auto_buy_tab.py**: 
  - Added multi-path checking for better liquidity discovery
  - Fixed decimals handling for PLEX ONE (9 decimals)
  - Added proper token symbol display in logs
  - Improved getAmountsOut error handling
- **Known token decimals cache**: Added cache for known tokens to avoid repeated calls
- **Version Update**: Bumped from 2.4.11 to 2.4.12

### Confirmed Working:
- PLEX ONE/WBNB pool: 0x41d9650faf3341cbf8947fd8063a1fc88dbf1889
- PLEX ONE/USDT pool: 0xc7961e1e762d4b1975a3fcd07b8f70e34726c04e

## v2.4.11 (2025-01-29) - Logging System Fix

### Fixed Issues:
- **Fixed Duplicate Logging**: Resolved issue where logs were appearing twice in the main window
- **Fixed Log Synchronization**: All log windows (main, separate, floating) now receive identical logs
- **Unified Logging System**: Streamlined to use single UnifiedLogManager for all log distribution

### Technical Improvements:
- **main_window.py**: Refactored log handlers to avoid duplication
  - `_unified_log_handler` now directly adds logs to UI via `_add_log_impl`
  - `_enhanced_log_handler` sends logs to unified manager instead of direct emission
  - `add_log` method simplified to only use unified manager
- **Centralized Log Management**: All logs now flow through UnifiedLogManager
- **Version Update**: Bumped from 2.4.10 to 2.4.11

### Known Issues:
- **Liquidity Error**: "Zero quote result" error in auto_buy_tab when liquidity is insufficient
  - Needs improved path finding algorithm with intermediate tokens (WBNB, BUSD)
  - Requires better error messages for liquidity issues

## v2.4.4 (2025-01-16) - Enhanced Logging Decorators

### Major Improvements:
- **Async Support**: Added full support for asynchronous functions in logging decorators
- **Better Error Handling**: Enhanced error logging with detailed context and stack traces
- **Context Information**: Improved context capture for method calls with class/module info
- **Performance Optimization**: Added string truncation and efficient parameter formatting

### New Features:
- **Async Decorator**: Added `@log_async_action` specifically for async operations
- **Context Tracking**: Automatic detection of class methods and context extraction
- **Stack Trace Logging**: Limited stack traces (last 3 relevant lines) for debugging
- **Parameter Truncation**: Automatic truncation of long parameters to keep logs readable

### Technical Improvements:
- Added `_get_context_info()` for better context extraction
- Added `_format_action_message()` for consistent message formatting
- Added `_format_result()` for result formatting with truncation
- Added `_truncate_str()` utility for string length management
- Added `_log_error()` for detailed error logging with context
- Support for both sync and async functions in `@log_action`
- Proper handling of `asyncio.CancelledError` in async operations
- Improved class method detection using `inspect.signature`

### Fixed Issues:
- ✅ Fixed: Async functions not properly logged
- ✅ Fixed: Missing context information in error logs
- ✅ Fixed: Long parameters cluttering log output
- ✅ Fixed: Stack traces too verbose in error messages

## v2.4.3 (2025-09-11) - Logging Integration Progress

### Changes:
- **mass_distribution_tab.py**: Added logging decorators for all major UI elements
  - Added decorators for dropdown changes (token selection)
  - Added decorators for spinbox changes (amounts, cycles, intervals)
  - Added decorators for button clicks (import, start, stop)
  - Added decorators for file operations and validations
- **Fixed**: Commented out missing create_gas_settings_group function calls

### Updated Components:
- mass_distribution_tab.py - Full logging decorator integration

## v2.4.2 (2025-09-11) - Continued Logging Integration

### Changes:
- **auto_buy_tab.py**: Fixed missing create_gas_settings_group function
- **Continued logging integration**: Working on adding decorators to all tabs

### Fixed Issues:
- ✅ Fixed: Commented out call to non-existent create_gas_settings_group function

## v2.4.1 (2025-09-11) - Complete Operator Action Logging

### Major Features:
- **Complete Action Logging**: All operator actions on all tabs are now fully logged
- **Extended Logging Decorators**: Added new decorators for comprehensive UI tracking
- **Settings Tab Integration**: Full logging coverage for settings changes

### New Logging Decorators:
- `@log_dropdown_change` - Logs dropdown/combobox selections
- `@log_checkbox_change` - Logs checkbox state changes  
- `@log_radio_change` - Logs radio button selections
- `@log_slider_change` - Logs slider value changes
- `@log_spinbox_change` - Logs spinbox value changes
- `@log_table_action` - Logs table interactions
- `@log_dialog_action` - Logs dialog open/close events
- `@log_validation` - Logs validation processes
- `@log_api_call` - Logs API calls with success/failure
- `@log_currency_change` - Logs currency/token changes
- `@log_time_change` - Logs time/interval modifications

### Updated Components:
- **logger_enhanced.py**: Added 11 new logging decorators
- **settings_tab.py**: Full integration with logging decorators
  - All button clicks logged
  - All settings changes logged
  - All API tests logged
  - All validations logged
- **Version**: Updated to 2.4.1

### Operator Actions Now Logged:
- Currency/token selection changes
- Time interval modifications
- Gas price and limit changes
- RPC endpoint changes
- API key modifications
- Language and timezone changes
- Import/Export operations
- All test operations (RPC, API keys)
- Settings save/reset operations
- Every spinbox, dropdown, and checkbox interaction

### Technical Improvements:
- Thread-safe logging for all UI interactions
- Automatic value capture from UI elements
- Consistent log formatting across all tabs
- Debug-level logging for granular tracking

## v2.4.0 (2025-09-11) - Enhanced Logging System

### Major Features:
- **Enhanced Logging System**: Complete overhaul of logging infrastructure with automatic action tracking
- **Automatic Action Logging**: All user interactions are now automatically logged using decorators
- **Multiple Log Windows**: Support for separate and floating log windows with full synchronization
- **Real-time Log Synchronization**: All log windows sync every 100ms with the main window

### New Components:
- **logger_enhanced.py**: New enhanced logging system with decorators for automatic logging
- **Logging Decorators**:
  - `@log_action` - Logs any action with start/completion/error states
  - `@log_click` - Logs button clicks
  - `@log_input_change` - Logs field value changes
  - `@log_tab_change` - Logs tab switching
  - `@log_window_action` - Logs window operations
  - `@log_network_action` - Logs network operations
  - `@log_transaction` - Logs blockchain transactions
  - `@log_file_operation` - Logs file operations
  - `@log_settings_change` - Logs settings modifications

### UI Improvements:
- **Log Window Features**:
  - Search functionality in log windows
  - Export logs to txt/html formats
  - Copy all logs to clipboard
  - Auto-scroll toggle
  - Transparency adjustment for floating windows
  - Pin on top functionality
- **Visual Enhancements**:
  - Color-coded log levels (INFO, SUCCESS, WARNING, ERROR)
  - Icons for different action types
  - Timestamps for all log entries
  - Collapsible log area in main window

### Fixed Issues:
- ✅ Fixed: Not all operator actions were being logged
- ✅ Fixed: Logs not displaying in additional log windows
- ✅ Fixed: Missing logging for UI interactions
- ✅ Fixed: Incomplete transaction logging

### Technical Details:
- Global UI log handler for centralized log management
- Decorator-based automatic logging reduces boilerplate code
- Thread-safe log emission through Qt signals
- Extensible logging system for easy integration in new tabs

### Updated Components:
- **main_window.py**: Integrated enhanced logging handler
- **base_tab.py**: Added logging decorators to common actions
- **direct_send_tab.py**: Full logging coverage for all actions
- **log_windows.py**: Enhanced with search, export, and sync features

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
