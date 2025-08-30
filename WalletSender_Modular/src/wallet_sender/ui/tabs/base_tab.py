"""Base tab widget with common helpers for WalletSender UI tabs.

This minimal implementation provides shared UI blocks and utilities used by
other tabs (logging, wallet connect placeholders, gas settings group). It aims
to keep imports working and the app booting; domain-specific logic lives in
specialized tabs.
"""

from typing import Optional

from PyQt5.QtWidgets import (
	QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
	QSpinBox
)
from PyQt5.QtGui import QFont


class BaseTab(QWidget):
	"""Lightweight base class for UI tabs."""

	def __init__(self, main_window, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self.main_window = main_window
		# Subclasses are expected to implement init_ui
		if hasattr(self, "init_ui"):
			try:
				self.init_ui()  # type: ignore[attr-defined]
			except Exception:
				# Avoid crashing the whole app if a specific tab fails
				pass

	# ----- Common UI blocks -----
	def _create_wallet_group(self) -> QGroupBox:
		group = QGroupBox("Подключение кошелька")
		layout = QVBoxLayout()

		self.wallet_input = QTextEdit()
		self.wallet_input.setPlaceholderText("Вставьте SEED или приватный ключ…")
		self.wallet_input.setMaximumHeight(60)
		layout.addWidget(self.wallet_input)

		btns = QHBoxLayout()
		self.connect_btn = QPushButton("🔗 Подключить кошелёк")
		self.connect_btn.clicked.connect(self.connect_wallet)
		btns.addWidget(self.connect_btn)

		self.disconnect_btn = QPushButton("🔌 Отключить")
		self.disconnect_btn.clicked.connect(self.disconnect_wallet)
		self.disconnect_btn.setEnabled(False)
		btns.addWidget(self.disconnect_btn)

		layout.addLayout(btns)

		self.wallet_address_label = QLabel("Адрес: Не подключен")
		self.wallet_address_label.setFont(QFont("Consolas", 10))
		layout.addWidget(self.wallet_address_label)

		group.setLayout(layout)
		return group

	def _create_balance_group(self) -> QGroupBox:
		group = QGroupBox("Баланс")
		layout = QVBoxLayout()
		self.balance_label = QLabel("BNB: 0 | Токен: 0")
		layout.addWidget(self.balance_label)
		group.setLayout(layout)
		return group

	def create_gas_settings_group(self) -> QGroupBox:
		group = QGroupBox("Настройки газа")
		layout = QHBoxLayout()

		layout.addWidget(QLabel("Цена газа (Gwei):"))
		self.gas_price_input = QSpinBox()
		self.gas_price_input.setRange(1, 1000)
		self.gas_price_input.setValue(5)
		layout.addWidget(self.gas_price_input)

		layout.addWidget(QLabel("Лимит газа:"))
		self.gas_limit_input = QSpinBox()
		self.gas_limit_input.setRange(21000, 1_000_000)
		self.gas_limit_input.setValue(100000)
		layout.addWidget(self.gas_limit_input)

		group.setLayout(layout)
		return group

	# ----- Basic actions used by tabs -----
	def connect_wallet(self):
		text = self.wallet_input.toPlainText().strip() if hasattr(self, "wallet_input") else ""
		if text:
			# UI-only placeholder; real connect logic lives in specific tabs/services
			self.wallet_address_label.setText("Адрес: (локально подключено)")
			self.disconnect_btn.setEnabled(True)
			self.log("Кошелёк подключён (плейсхолдер)", "SUCCESS")
		else:
			self.log("Введите SEED или приватный ключ", "WARNING")

	def disconnect_wallet(self):
		if hasattr(self, "wallet_address_label"):
			self.wallet_address_label.setText("Адрес: Не подключен")
		if hasattr(self, "disconnect_btn"):
			self.disconnect_btn.setEnabled(False)
		self.log("Кошелёк отключён", "INFO")

	def refresh_balance(self):
		# Placeholder to be overridden by tabs
		self.log("Обновление баланса (плейсхолдер)")

	def update_balances(self):
		# Placeholder periodic updater
		pass

	# ----- Logging helper -----
	def log(self, message: str, level: str = "INFO"):
		try:
			if hasattr(self.main_window, "log_message"):
				self.main_window.log_message.emit(message, level)  # type: ignore[attr-defined]
				return
		except Exception:
			pass
		# Fallback
		print(f"[{level}] {message}")

