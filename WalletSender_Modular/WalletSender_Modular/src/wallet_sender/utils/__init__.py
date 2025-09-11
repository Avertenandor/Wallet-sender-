"""
Utils package for WalletSender
"""

from .logger import get_logger
from .logger_enhanced import (
    EnhancedLogger,
    set_ui_log_handler,
    log_action,
    log_click,
    log_input_change,
    log_tab_change,
    log_window_action,
    log_network_action,
    log_transaction,
    log_file_operation,
    log_settings_change
)

__all__ = [
    'get_logger',
    'EnhancedLogger',
    'set_ui_log_handler',
    'log_action',
    'log_click',
    'log_input_change',
    'log_tab_change',
    'log_window_action',
    'log_network_action',
    'log_transaction',
    'log_file_operation',
    'log_settings_change'
]
