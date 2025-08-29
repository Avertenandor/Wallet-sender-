"""Core functionality package"""

try:
    from .web3_provider import Web3Provider
except ImportError as e:
    print(f"Warning: Не удалось импортировать Web3Provider: {e}")

__all__ = ['Web3Provider']
