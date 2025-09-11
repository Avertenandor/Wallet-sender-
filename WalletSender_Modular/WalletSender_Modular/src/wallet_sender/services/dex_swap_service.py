"""DexSwapService: операции approve и swap с управлением nonce и газом.

Версия 2.4.20 - Переключение на асинхронную версию с улучшенными таймаутами
"""

# Импортируем новую асинхронную версию
from .dex_swap_service_async import DexSwapServiceAsync as DexSwapService

# Экспортируем для обратной совместимости
__all__ = ['DexSwapService']
