"""
Модели базы данных
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Transaction(Base):
    """Модель транзакции"""
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    tx_hash = Column(String(66), unique=True, index=True)
    from_address = Column(String(42), index=True)
    to_address = Column(String(42), index=True)
    token_address = Column(String(42))
    token_symbol = Column(String(20))
    amount = Column(Float)
    gas_price = Column(Float)
    gas_used = Column(Integer)
    status = Column(String(20))  # pending, success, failed
    type = Column(String(20), default='transfer')  # transfer, reward, distribution, buy, sell
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime)
    block_number = Column(Integer)
    
    # Связь с наградами
    rewards = relationship("Reward", back_populates="transaction")
    

class Wallet(Base):
    """Модель кошелька"""
    __tablename__ = 'wallets'
    
    id = Column(Integer, primary_key=True)
    address = Column(String(42), unique=True, index=True)
    label = Column(String(100))
    private_key_encrypted = Column(Text)  # Зашифрованный приватный ключ
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # Связь с балансами
    balances = relationship("Balance", back_populates="wallet")
    

class Balance(Base):
    """Модель баланса токена"""
    __tablename__ = 'balances'
    
    id = Column(Integer, primary_key=True)
    wallet_id = Column(Integer, ForeignKey('wallets.id'))
    token_address = Column(String(42))
    token_symbol = Column(String(20))
    balance = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Связь с кошельком
    wallet = relationship("Wallet", back_populates="balances")
    

class Reward(Base):
    """Модель награды"""
    __tablename__ = 'rewards'
    
    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey('transactions.id'))
    recipient_address = Column(String(42), index=True)
    reward_amount = Column(Float)
    reward_token = Column(String(42))
    reward_token_symbol = Column(String(20))
    status = Column(String(20))  # pending, sent, failed
    sent_tx_hash = Column(String(66))
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime)
    
    # Связь с транзакцией
    transaction = relationship("Transaction", back_populates="rewards")
    

class DistributionTask(Base):
    """Модель задачи массовой рассылки"""
    __tablename__ = 'distribution_tasks'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    token_address = Column(String(42))
    token_symbol = Column(String(20))
    amount_per_address = Column(Float)
    total_addresses = Column(Integer)
    processed_addresses = Column(Integer, default=0)
    successful_sends = Column(Integer, default=0)
    failed_sends = Column(Integer, default=0)
    status = Column(String(20))  # pending, running, paused, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Связь с адресами для рассылки
    addresses = relationship("DistributionAddress", back_populates="task")
    

class DistributionAddress(Base):
    """Модель адреса для массовой рассылки"""
    __tablename__ = 'distribution_addresses'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('distribution_tasks.id'))
    address = Column(String(42))
    amount = Column(Float)
    status = Column(String(20))  # pending, sent, failed
    tx_hash = Column(String(66))
    error_message = Column(Text)
    processed_at = Column(DateTime)
    
    # Связь с задачей
    task = relationship("DistributionTask", back_populates="addresses")
    

class AutoBuyTask(Base):
    """Модель задачи автоматической покупки"""
    __tablename__ = 'auto_buy_tasks'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    token_address = Column(String(42))
    token_symbol = Column(String(20))
    buy_amount = Column(Float)
    buy_interval = Column(Integer)  # Интервал в секундах
    total_buys = Column(Integer)
    completed_buys = Column(Integer, default=0)
    status = Column(String(20))  # active, paused, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    last_buy_at = Column(DateTime)
    

class AutoSaleTask(Base):
    """Модель задачи автоматической продажи"""
    __tablename__ = 'auto_sale_tasks'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    token_address = Column(String(42))
    token_symbol = Column(String(20))
    sale_amount = Column(Float)
    target_price = Column(Float)
    current_price = Column(Float)
    status = Column(String(20))  # monitoring, triggered, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    triggered_at = Column(DateTime)
    completed_at = Column(DateTime)
    

class Settings(Base):
    """Модель настроек приложения"""
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True)
    value = Column(Text)
    category = Column(String(50))
    updated_at = Column(DateTime, default=datetime.utcnow)
