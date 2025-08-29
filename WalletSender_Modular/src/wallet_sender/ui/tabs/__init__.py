"""UI tabs package"""

# Импорт всех вкладок
try:
    from .base_tab import BaseTab
    from .auto_buy_tab import AutoBuyTab
    from .auto_sales_tab import AutoSalesTab
    from .direct_send_tab import DirectSendTab
    from .mass_distribution_tab import MassDistributionTab
except ImportError as e:
    print(f"Warning: Не удалось импортировать некоторые вкладки: {e}")

__all__ = [
    'BaseTab',
    'AutoBuyTab', 
    'AutoSalesTab',
    'DirectSendTab',
    'MassDistributionTab'
]
