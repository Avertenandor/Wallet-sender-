"""
Простой тест для проверки базового функционала WalletSender
"""

import sys
import os
sys.path.insert(0, 'src')

from wallet_sender.database.database import Database
from wallet_sender.database.models import Reward, Transaction, DistributionTask
from wallet_sender.config import Config
from datetime import datetime

def test_database():
    """Тест подключения к БД"""
    print("1. Тестируем подключение к БД...")
    try:
        db = Database()
        print("   [OK] БД подключена")
        
        # Создаем тестовую награду
        reward = Reward(
            recipient_address="0x1234567890123456789012345678901234567890",
            reward_amount=10.0,
            reward_token="0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1",
            reward_token_symbol="PLEX",
            status="sent",
            created_at=datetime.utcnow()
        )
        db.session.add(reward)
        db.session.commit()
        print("   [OK] Тестовая награда создана")
        
        # Читаем награды
        rewards = db.session.query(Reward).all()
        print(f"   [OK] Найдено наград в БД: {len(rewards)}")
        
        return True
    except Exception as e:
        print(f"   [ERROR] Ошибка БД: {e}")
        return False

def test_config():
    """Тест конфигурации"""
    print("\n2. Тестируем конфигурацию...")
    try:
        config = Config()
        
        # Проверяем ключи BSCScan
        api_keys = config.get('bscscan_api_keys', [])
        print(f"   [OK] Найдено API ключей: {len(api_keys)}")
        
        # Проверяем токены
        tokens = config.get('tokens', {})
        print(f"   [OK] Найдено токенов: {len(tokens)}")
        
        return True
    except Exception as e:
        print(f"   [ERROR] Ошибка конфигурации: {e}")
        return False

def test_imports():
    """Тест импортов модулей"""
    print("\n3. Тестируем импорты модулей...")
    try:
        from wallet_sender.ui.tabs.rewards_tab import RewardsTab
        print("   [OK] RewardsTab импортирован")
        
        from wallet_sender.ui.tabs.history_tab import HistoryTab
        print("   [OK] HistoryTab импортирован")
        
        from wallet_sender.ui.tabs.queue_tab import QueueTab
        print("   [OK] QueueTab импортирован")
        
        from wallet_sender.ui.tabs.search_tab import SearchTab
        print("   [OK] SearchTab импортирован")
        
        from wallet_sender.ui.tabs.analysis_tab import AnalysisTab
        print("   [OK] AnalysisTab импортирован")
        
        return True
    except Exception as e:
        print(f"   [ERROR] Ошибка импорта: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("=" * 50)
    print("ТЕСТИРОВАНИЕ WALLETSENDER MODULAR")
    print("=" * 50)
    
    results = []
    
    # Запускаем тесты
    results.append(test_database())
    results.append(test_config())
    results.append(test_imports())
    
    # Итоги
    print("\n" + "=" * 50)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"[OK] ВСЕ ТЕСТЫ ПРОЙДЕНЫ ({passed}/{total})")
    else:
        print(f"[WARN] ПРОЙДЕНО ТЕСТОВ: {passed}/{total}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
