"""
JobRouter - централизованный маршрутизатор для управления задачами
"""

from typing import Dict, Optional, List, Any
from datetime import datetime
import logging

from ..core.job_engine import get_job_engine, JobState
from ..utils.logger import get_logger

logger = get_logger(__name__)


class JobRouter:
    """Маршрутизатор задач для централизованного управления"""
    
    def __init__(self):
        """Инициализация роутера"""
        self.engine = get_job_engine()
        self.active_tags = {}  # {tag: [job_ids]}
        
    def submit_distribution(self, 
                          addresses: List[str],
                          token_address: str,
                          amount_per_address: float,
                          sender_key: str,
                          gas_price: int = 5,
                          gas_limit: int = 100000,
                          delay_between_tx: float = 1.0,
                          tag: Optional[str] = None,
                          priority: int = 5) -> int:
        """
        Отправка задачи массовой рассылки
        
        Args:
            addresses: Список адресов получателей
            token_address: Адрес токена (или "BNB")
            amount_per_address: Сумма на каждый адрес
            sender_key: Приватный ключ отправителя
            gas_price: Цена газа в gwei
            gas_limit: Лимит газа
            delay_between_tx: Задержка между транзакциями
            tag: Тег для группировки задач
            priority: Приоритет выполнения
            
        Returns:
            ID созданной задачи
        """
        config = {
            'addresses': addresses,
            'token_address': token_address,
            'amount_per_address': amount_per_address,
            'sender_key': sender_key,
            'gas_price': gas_price,
            'gas_limit': gas_limit,
            'delay_between_tx': delay_between_tx
        }
        
        title = f"Distribution to {len(addresses)} addresses"
        job_id = self.engine.submit_job(title, 'distribution', config, priority)
        
        # Сохраняем тег если указан
        if tag:
            if tag not in self.active_tags:
                self.active_tags[tag] = []
            self.active_tags[tag].append(job_id)
        
        logger.info(f"Submitted distribution job #{job_id} with tag '{tag}'")
        return job_id
    
    def submit_auto_buy(self,
                       token_address: str,
                       buy_amount: float,
                       interval: int,
                       total_buys: int,
                       buyer_keys: List[str],
                       slippage: float = 0.5,
                       tag: Optional[str] = None,
                       priority: int = 3) -> int:
        """
        Отправка задачи автоматических покупок
        
        Args:
            token_address: Адрес токена для покупки
            buy_amount: Сумма покупки в BNB
            interval: Интервал между покупками (секунды)
            total_buys: Общее количество покупок
            buyer_keys: Список приватных ключей покупателей
            slippage: Допустимое проскальзывание (%)
            tag: Тег для группировки задач
            priority: Приоритет выполнения
            
        Returns:
            ID созданной задачи
        """
        config = {
            'token_address': token_address,
            'buy_amount': buy_amount,
            'interval': interval,
            'total_buys': total_buys,
            'buyer_keys': buyer_keys,
            'slippage': slippage
        }
        
        title = f"Auto-buy {total_buys} times every {interval}s"
        job_id = self.engine.submit_job(title, 'auto_buy', config, priority)
        
        # Сохраняем тег если указан
        if tag:
            if tag not in self.active_tags:
                self.active_tags[tag] = []
            self.active_tags[tag].append(job_id)
        
        logger.info(f"Submitted auto-buy job #{job_id} with tag '{tag}'")
        return job_id
    
    def submit_auto_sell(self,
                        token_address: str,
                        sell_percentage: float,
                        interval: int,
                        total_sells: int,
                        seller_keys: List[str],
                        slippage: float = 0.5,
                        tag: Optional[str] = None,
                        priority: int = 3) -> int:
        """
        Отправка задачи автоматических продаж
        
        Args:
            token_address: Адрес токена для продажи
            sell_percentage: Процент от баланса для продажи
            interval: Интервал между продажами (секунды)
            total_sells: Общее количество продаж
            seller_keys: Список приватных ключей продавцов
            slippage: Допустимое проскальзывание (%)
            tag: Тег для группировки задач
            priority: Приоритет выполнения
            
        Returns:
            ID созданной задачи
        """
        config = {
            'token_address': token_address,
            'sell_percentage': sell_percentage,
            'interval': interval,
            'total_sells': total_sells,
            'seller_keys': seller_keys,
            'slippage': slippage
        }
        
        title = f"Auto-sell {sell_percentage}% {total_sells} times"
        job_id = self.engine.submit_job(title, 'auto_sell', config, priority)
        
        # Сохраняем тег если указан
        if tag:
            if tag not in self.active_tags:
                self.active_tags[tag] = []
            self.active_tags[tag].append(job_id)
        
        logger.info(f"Submitted auto-sell job #{job_id} with tag '{tag}'")
        return job_id
    
    def submit_rewards(self,
                      rewards_config: Dict,
                      sender_key: str,
                      tag: Optional[str] = None,
                      priority: int = 7) -> int:
        """
        Отправка задачи распределения наград
        
        Args:
            rewards_config: Конфигурация наград
            sender_key: Приватный ключ отправителя
            tag: Тег для группировки задач
            priority: Приоритет выполнения
            
        Returns:
            ID созданной задачи
        """
        config = {
            'rewards_config': rewards_config,
            'sender_key': sender_key
        }
        
        title = f"Rewards distribution"
        job_id = self.engine.submit_job(title, 'rewards', config, priority)
        
        # Сохраняем тег если указан
        if tag:
            if tag not in self.active_tags:
                self.active_tags[tag] = []
            self.active_tags[tag].append(job_id)
        
        logger.info(f"Submitted rewards job #{job_id} with tag '{tag}'")
        return job_id
    
    def cancel_by_tag(self, tag: str) -> List[int]:
        """
        Отмена всех задач с указанным тегом
        
        Args:
            tag: Тег задач для отмены
            
        Returns:
            Список ID отмененных задач
        """
        cancelled = []
        
        if tag in self.active_tags:
            for job_id in self.active_tags[tag]:
                if self.engine.cancel_job(job_id):
                    cancelled.append(job_id)
                    logger.info(f"Cancelled job #{job_id} (tag: {tag})")
            
            # Очищаем тег
            del self.active_tags[tag]
        
        return cancelled
    
    def cancel_job(self, job_id: int) -> bool:
        """
        Отмена конкретной задачи
        
        Args:
            job_id: ID задачи для отмены
            
        Returns:
            True если задача отменена
        """
        result = self.engine.cancel_job(job_id)
        
        if result:
            # Удаляем из тегов
            for tag, job_ids in self.active_tags.items():
                if job_id in job_ids:
                    job_ids.remove(job_id)
                    if not job_ids:
                        del self.active_tags[tag]
                    break
        
        return result
    
    def pause_job(self, job_id: int) -> bool:
        """
        Приостановка задачи
        
        Args:
            job_id: ID задачи
            
        Returns:
            True если задача приостановлена
        """
        return self.engine.pause_job(job_id)
    
    def resume_job(self, job_id: int) -> bool:
        """
        Возобновление задачи
        
        Args:
            job_id: ID задачи
            
        Returns:
            True если задача возобновлена
        """
        return self.engine.resume_job(job_id)
    
    def get_progress(self, job_id: int) -> Optional[Dict]:
        """
        Получение прогресса задачи
        
        Args:
            job_id: ID задачи
            
        Returns:
            Информация о прогрессе
        """
        return self.engine.get_job_progress(job_id)
    
    def stats(self) -> Dict[str, Any]:
        """
        Получение общей статистики
        
        Returns:
            Словарь со статистикой
        """
        # Подсчитываем задачи по состояниям
        states_count = {
            'queued': 0,
            'running': 0,
            'paused': 0,
            'completed': 0,
            'failed': 0,
            'cancelled': 0
        }
        
        # Получаем все задачи из хранилища
        all_jobs = self.engine.store.get_recent_jobs(limit=100)
        
        for job in all_jobs:
            state = job.get('state', '').lower()
            if state == 'pending':
                states_count['queued'] += 1
            elif state in states_count:
                states_count[state] += 1
        
        # Добавляем информацию об активных задачах
        active_jobs = []
        for job_id, executor in self.engine.active_jobs.items():
            job_info = {
                'id': job_id,
                'total': executor.total_count,
                'done': executor.done_count,
                'failed': executor.failed_count,
                'is_paused': executor.is_paused,
                'eta': executor.get_eta()
            }
            active_jobs.append(job_info)
        
        return {
            'states': states_count,
            'active_jobs': active_jobs,
            'active_tags': list(self.active_tags.keys()),
            'total_active': len(self.engine.active_jobs),
            'queue_size': self.engine.job_queue.qsize()
        }
    
    def get_jobs_by_tag(self, tag: str) -> List[int]:
        """
        Получение списка задач по тегу
        
        Args:
            tag: Тег для поиска
            
        Returns:
            Список ID задач
        """
        return self.active_tags.get(tag, [])
    
    def register_callback(self, event: str, callback):
        """
        Регистрация колбека для события
        
        Args:
            event: Название события
            callback: Функция колбека
        """
        self.engine.register_callback(event, callback)


# Глобальный экземпляр роутера
_job_router: Optional[JobRouter] = None


def get_job_router() -> JobRouter:
    """Получение глобального экземпляра роутера задач"""
    global _job_router
    
    if _job_router is None:
        _job_router = JobRouter()
    
    return _job_router


def close_job_router():
    """Закрытие глобального роутера задач"""
    global _job_router
    
    if _job_router:
        _job_router = None
