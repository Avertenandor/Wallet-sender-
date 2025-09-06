"""
Менеджер памяти для оптимизации использования ресурсов
"""

import gc
import psutil
import threading
import time
import weakref
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from collections import defaultdict, deque
import sys

@dataclass
class MemoryStats:
    """Статистика использования памяти"""
    total_memory: int
    available_memory: int
    used_memory: int
    memory_percent: float
    process_memory: int
    process_memory_percent: float
    timestamp: float

class MemoryManager:
    """Менеджер памяти"""
    
    def __init__(self, max_memory_percent: float = 80.0, cleanup_interval: int = 300):
        self.max_memory_percent = max_memory_percent
        self.cleanup_interval = cleanup_interval
        self._lock = threading.RLock()
        
        # Слабые ссылки для отслеживания объектов
        self._tracked_objects: Dict[str, List[weakref.ref]] = defaultdict(list)
        self._cleanup_callbacks: List[Callable] = []
        
        # Статистика
        self._memory_history: deque = deque(maxlen=100)
        self._last_cleanup = time.time()
        
        # Автоматическая очистка
        self._cleanup_thread = None
        self._running = False
        
        # Пороги для очистки
        self.cleanup_thresholds = {
            'memory_percent': 75.0,
            'process_memory_mb': 500,
            'object_count': 10000
        }
    
    def start_monitoring(self):
        """Запускает мониторинг памяти"""
        if not self._running:
            self._running = True
            self._cleanup_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self._cleanup_thread.start()
    
    def stop_monitoring(self):
        """Останавливает мониторинг памяти"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
    
    def _monitoring_loop(self):
        """Цикл мониторинга памяти"""
        while self._running:
            try:
                # Получаем статистику памяти
                stats = self.get_memory_stats()
                self._memory_history.append(stats)
                
                # Проверяем необходимость очистки
                if self._should_cleanup(stats):
                    self.perform_cleanup()
                
                # Ждем до следующей проверки
                time.sleep(self.cleanup_interval)
                
            except Exception as e:
                print(f"Ошибка в мониторинге памяти: {e}")
                time.sleep(60)  # Ждем минуту при ошибке
    
    def get_memory_stats(self) -> MemoryStats:
        """Получает статистику памяти"""
        # Системная память
        memory = psutil.virtual_memory()
        
        # Память процесса
        process = psutil.Process()
        process_memory = process.memory_info().rss
        
        return MemoryStats(
            total_memory=memory.total,
            available_memory=memory.available,
            used_memory=memory.used,
            memory_percent=memory.percent,
            process_memory=process_memory,
            process_memory_percent=(process_memory / memory.total) * 100,
            timestamp=time.time()
        )
    
    def _should_cleanup(self, stats: MemoryStats) -> bool:
        """Определяет, нужна ли очистка памяти"""
        # Проверяем системную память
        if stats.memory_percent > self.cleanup_thresholds['memory_percent']:
            return True
        
        # Проверяем память процесса
        process_memory_mb = stats.process_memory / (1024 * 1024)
        if process_memory_mb > self.cleanup_thresholds['process_memory_mb']:
            return True
        
        # Проверяем количество объектов
        object_count = len(gc.get_objects())
        if object_count > self.cleanup_thresholds['object_count']:
            return True
        
        # Проверяем время с последней очистки
        if time.time() - self._last_cleanup > self.cleanup_interval:
            return True
        
        return False
    
    def perform_cleanup(self, force: bool = False) -> Dict[str, Any]:
        """Выполняет очистку памяти"""
        with self._lock:
            cleanup_stats = {
                'timestamp': time.time(),
                'before_cleanup': self.get_memory_stats(),
                'actions_performed': [],
                'objects_removed': 0,
                'memory_freed_mb': 0
            }
            
            try:
                # 1. Очистка слабых ссылок
                removed_refs = self._cleanup_weak_refs()
                cleanup_stats['objects_removed'] += removed_refs
                cleanup_stats['actions_performed'].append(f"Очищено слабых ссылок: {removed_refs}")
                
                # 2. Принудительная сборка мусора
                collected = gc.collect()
                cleanup_stats['objects_removed'] += collected
                cleanup_stats['actions_performed'].append(f"Собрано мусора: {collected}")
                
                # 3. Вызов пользовательских callback'ов
                for callback in self._cleanup_callbacks:
                    try:
                        callback()
                        cleanup_stats['actions_performed'].append("Вызван пользовательский callback")
                    except Exception as e:
                        cleanup_stats['actions_performed'].append(f"Ошибка в callback: {e}")
                
                # 4. Очистка кешей (если есть)
                self._cleanup_caches()
                cleanup_stats['actions_performed'].append("Очищены кеши")
                
                # 5. Очистка истории памяти
                if len(self._memory_history) > 50:
                    # Оставляем только последние 50 записей
                    while len(self._memory_history) > 50:
                        self._memory_history.popleft()
                    cleanup_stats['actions_performed'].append("Очищена история памяти")
                
                # Обновляем время последней очистки
                self._last_cleanup = time.time()
                
                # Получаем статистику после очистки
                cleanup_stats['after_cleanup'] = self.get_memory_stats()
                
                # Вычисляем освобожденную память
                before_mb = cleanup_stats['before_cleanup'].process_memory / (1024 * 1024)
                after_mb = cleanup_stats['after_cleanup'].process_memory / (1024 * 1024)
                cleanup_stats['memory_freed_mb'] = max(0, before_mb - after_mb)
                
                return cleanup_stats
                
            except Exception as e:
                cleanup_stats['error'] = str(e)
                return cleanup_stats
    
    def _cleanup_weak_refs(self) -> int:
        """Очищает мертвые слабые ссылки"""
        removed_count = 0
        
        for category, refs in self._tracked_objects.items():
            alive_refs = []
            for ref in refs:
                if ref() is not None:
                    alive_refs.append(ref)
                else:
                    removed_count += 1
            
            self._tracked_objects[category] = alive_refs
        
        return removed_count
    
    def _cleanup_caches(self):
        """Очищает различные кеши"""
        # Здесь можно добавить очистку кешей из других модулей
        # Например, очистка кеша токенов, кеша балансов и т.д.
        pass
    
    def track_object(self, obj: Any, category: str = "general"):
        """Отслеживает объект через слабую ссылку"""
        with self._lock:
            ref = weakref.ref(obj)
            self._tracked_objects[category].append(ref)
    
    def add_cleanup_callback(self, callback: Callable):
        """Добавляет callback для очистки"""
        with self._lock:
            self._cleanup_callbacks.append(callback)
    
    def remove_cleanup_callback(self, callback: Callable):
        """Удаляет callback для очистки"""
        with self._lock:
            if callback in self._cleanup_callbacks:
                self._cleanup_callbacks.remove(callback)
    
    def get_memory_history(self, limit: int = 50) -> List[MemoryStats]:
        """Получает историю использования памяти"""
        with self._lock:
            return list(self._memory_history)[-limit:]
    
    def get_tracked_objects_count(self) -> Dict[str, int]:
        """Получает количество отслеживаемых объектов по категориям"""
        with self._lock:
            return {category: len(refs) for category, refs in self._tracked_objects.items()}
    
    def get_memory_usage_summary(self) -> Dict[str, Any]:
        """Получает сводку по использованию памяти"""
        stats = self.get_memory_stats()
        history = self.get_memory_history(10)
        tracked = self.get_tracked_objects_count()
        
        # Вычисляем тренды
        memory_trend = "stable"
        if len(history) >= 2:
            recent = history[-1].process_memory
            older = history[0].process_memory
            if recent > older * 1.1:
                memory_trend = "increasing"
            elif recent < older * 0.9:
                memory_trend = "decreasing"
        
        return {
            'current_stats': stats,
            'memory_trend': memory_trend,
            'tracked_objects': tracked,
            'total_tracked_objects': sum(tracked.values()),
            'last_cleanup': self._last_cleanup,
            'cleanup_thresholds': self.cleanup_thresholds,
            'should_cleanup': self._should_cleanup(stats)
        }

class CacheOptimizer:
    """Оптимизатор кешей"""
    
    def __init__(self, max_cache_size: int = 1000, max_cache_age: int = 3600):
        self.max_cache_size = max_cache_size
        self.max_cache_age = max_cache_age
        self._caches: Dict[str, Dict[str, Any]] = {}
        self._cache_metadata: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    def register_cache(self, cache_name: str, cache_dict: Dict[str, Any]):
        """Регистрирует кеш для оптимизации"""
        with self._lock:
            self._caches[cache_name] = cache_dict
            self._cache_metadata[cache_name] = {
                'created_at': time.time(),
                'last_access': time.time(),
                'access_count': 0
            }
    
    def optimize_cache(self, cache_name: str) -> Dict[str, Any]:
        """Оптимизирует конкретный кеш"""
        with self._lock:
            if cache_name not in self._caches:
                return {'error': f'Кеш {cache_name} не найден'}
            
            cache = self._caches[cache_name]
            metadata = self._cache_metadata[cache_name]
            
            optimization_stats = {
                'cache_name': cache_name,
                'before_size': len(cache),
                'actions_performed': [],
                'items_removed': 0
            }
            
            current_time = time.time()
            
            # 1. Удаляем устаревшие элементы
            if hasattr(cache, 'items'):
                items_to_remove = []
                for key, value in cache.items():
                    if hasattr(value, 'timestamp'):
                        if current_time - value.timestamp > self.max_cache_age:
                            items_to_remove.append(key)
                
                for key in items_to_remove:
                    del cache[key]
                    optimization_stats['items_removed'] += 1
                
                if items_to_remove:
                    optimization_stats['actions_performed'].append(f"Удалено устаревших элементов: {len(items_to_remove)}")
            
            # 2. Ограничиваем размер кеша
            if len(cache) > self.max_cache_size:
                # Удаляем самые старые элементы
                if hasattr(cache, 'items'):
                    # Сортируем по времени доступа (если есть)
                    sorted_items = sorted(cache.items(), 
                                        key=lambda x: getattr(x[1], 'last_access', 0))
                    
                    items_to_remove = len(cache) - self.max_cache_size
                    for i in range(items_to_remove):
                        key = sorted_items[i][0]
                        del cache[key]
                        optimization_stats['items_removed'] += 1
                    
                    optimization_stats['actions_performed'].append(f"Удалено старых элементов: {items_to_remove}")
            
            # 3. Обновляем метаданные
            metadata['last_access'] = current_time
            metadata['access_count'] += 1
            
            optimization_stats['after_size'] = len(cache)
            optimization_stats['memory_saved'] = optimization_stats['before_size'] - optimization_stats['after_size']
            
            return optimization_stats
    
    def optimize_all_caches(self) -> Dict[str, Any]:
        """Оптимизирует все зарегистрированные кеши"""
        with self._lock:
            total_stats = {
                'timestamp': time.time(),
                'caches_optimized': 0,
                'total_items_removed': 0,
                'cache_results': {}
            }
            
            for cache_name in list(self._caches.keys()):
                try:
                    result = self.optimize_cache(cache_name)
                    total_stats['cache_results'][cache_name] = result
                    total_stats['caches_optimized'] += 1
                    total_stats['total_items_removed'] += result.get('items_removed', 0)
                except Exception as e:
                    total_stats['cache_results'][cache_name] = {'error': str(e)}
            
            return total_stats
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Получает статистику всех кешей"""
        with self._lock:
            stats = {}
            for cache_name, cache in self._caches.items():
                metadata = self._cache_metadata[cache_name]
                stats[cache_name] = {
                    'size': len(cache),
                    'created_at': metadata['created_at'],
                    'last_access': metadata['last_access'],
                    'access_count': metadata['access_count'],
                    'age_seconds': time.time() - metadata['created_at']
                }
            return stats

# Глобальные экземпляры
memory_manager = MemoryManager()
cache_optimizer = CacheOptimizer()

# Автоматический запуск мониторинга
memory_manager.start_monitoring()
