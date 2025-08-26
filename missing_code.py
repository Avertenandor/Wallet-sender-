    def _toggle_reward_mode(self, checked):
        """Переключение режима награждения за транзакции"""
        self.reward_per_tx_mode = checked
        self.cfg.set_reward_per_tx(checked)
        logger.info(f"Режим награждения за каждую транзакцию {'включен' if checked else 'выключен'}")
    
    def _scan_transactions_for_rewards(self):
        """Заглушка для сканирования транзакций"""
        logger.info("Сканирование транзакций для наград...")
        self._load_tx_senders()
    
    def _clear_tx_data(self):
        """Очистка данных о транзакциях"""
        clear_sender_transactions()
        self._load_tx_senders()
        logger.info("Данные о транзакциях очищены")
    
    def _show_tx_senders_menu(self, position):
        """Контекстное меню для таблицы отправителей"""
        menu = QtWidgets.QMenu()
        view_tx = menu.addAction("Показать транзакции")
        action = menu.exec_(self.tx_senders_table.viewport().mapToGlobal(position))
        if action == view_tx:
            selected = self.tx_senders_table.selectedItems()
            if selected:
                row = selected[0].row()
                sender = self.tx_senders_table.item(row, 0).text()
                self._show_sender_transactions(sender)
    
    def _show_sender_tx_menu(self, position):
        """Контекстное меню для таблицы транзакций отправителя"""
        menu = QtWidgets.QMenu()
        copy_hash = menu.addAction("Копировать хэш")
        action = menu.exec_(self.sender_tx_table.viewport().mapToGlobal(position))
        if action == copy_hash:
            selected = self.sender_tx_table.selectedItems()
            if selected:
                row = selected[0].row()
                tx_hash = self.sender_tx_table.item(row, 0).text()
                QtWidgets.QApplication.clipboard().setText(tx_hash)
    
    def _create_rewards_from_tx(self):
        """Создание наград на основе транзакций"""
        logger.info("Создание наград на основе транзакций...")
    
    def _send_rewards_for_tx(self):
        """Отправка наград за транзакции"""
        logger.info("Отправка наград за транзакции...")
    
    def _load_tx_senders(self):
        """Загрузка данных об отправителях транзакций"""
        try:
            senders = get_sender_transaction_counts()
            self.tx_senders_table.setRowCount(0)
            for sender_data in senders:
                row = self.tx_senders_table.rowCount()
                self.tx_senders_table.insertRow(row)
                self.tx_senders_table.setItem(row, 0, QtWidgets.QTableWidgetItem(sender_data['sender_addr']))
                self.tx_senders_table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(sender_data['tx_count'])))
                self.tx_senders_table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(sender_data['rewarded_count'])))
                unrewarded = sender_data['tx_count'] - sender_data['rewarded_count']
                self.tx_senders_table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(unrewarded)))
        except Exception as e:
            logger.error(f"Ошибка при загрузке отправителей: {e}")
    
    def _show_sender_transactions(self, sender_addr):
        """Отображение транзакций конкретного отправителя"""
        try:
            transactions = get_transactions_by_sender(sender_addr)
            self.sender_tx_table.setRowCount(0)
            for tx_data in transactions:
                row = self.sender_tx_table.rowCount()
                self.sender_tx_table.insertRow(row)
                self.sender_tx_table.setItem(row, 0, QtWidgets.QTableWidgetItem(tx_data['tx_hash']))
                self.sender_tx_table.setItem(row, 1, QtWidgets.QTableWidgetItem(tx_data['tx_timestamp'] or '-'))
                self.sender_tx_table.setItem(row, 2, QtWidgets.QTableWidgetItem(tx_data['token_name']))
                self.sender_tx_table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(tx_data['amount'])))
                rewarded = "Да" if tx_data['rewarded'] else "Нет"
                self.sender_tx_table.setItem(row, 4, QtWidgets.QTableWidgetItem(rewarded))
        except Exception as e:
            logger.error(f"Ошибка при загрузке транзакций отправителя: {e}")
    
    # Заглушки для остальных вкладок
    def _tab_analyze(self):
        """Вкладка анализа"""
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.addWidget(QtWidgets.QLabel("Вкладка анализа"))
        return w
    
    def _tab_paginated_search(self):
        """Вкладка поиска транзакций"""
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.addWidget(QtWidgets.QLabel("Вкладка поиска транзакций"))
        self.radio_exact = QtWidgets.QRadioButton("Точная сумма")
        self.radio_range = QtWidgets.QRadioButton("Диапазон")
        self.spin_amt = QtWidgets.QDoubleSpinBox()
        self.spin_amt_from = QtWidgets.QDoubleSpinBox()
        self.spin_amt_to = QtWidgets.QDoubleSpinBox()
        layout.addWidget(self.radio_exact)
        layout.addWidget(self.radio_range)
        self.progress_search = QtWidgets.QProgressBar()
        layout.addWidget(self.progress_search)
        return w
    
    def _tab_rewards(self):
        """Вкладка наград"""
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.addWidget(QtWidgets.QLabel("Вкладка наград"))
        self.progress_send = QtWidgets.QProgressBar()
        layout.addWidget(self.progress_send)
        return w
    
    def _tab_direct_send(self):
        """Вкладка прямой отправки"""
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.addWidget(QtWidgets.QLabel("Вкладка прямой отправки"))
        self.direct_send_progress = QtWidgets.QProgressBar()
        layout.addWidget(self.direct_send_progress)
        return w
    
    def _direct_send_periodic_send(self):
        """Периодическая отправка"""
        pass
    
    def _tab_ds(self):
        """Вкладка дополнительных сервисов"""
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.addWidget(QtWidgets.QLabel("Вкладка дополнительных сервисов"))
        return w
    
    def _tab_history(self):
        """Вкладка истории"""
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.addWidget(QtWidgets.QLabel("Вкладка истории"))
        self.progress = QtWidgets.QProgressBar()
        layout.addWidget(self.progress)
        return w
    
    def _tab_found_tx(self):
        """Вкладка найденных транзакций"""
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.addWidget(QtWidgets.QLabel("Вкладка найденных транзакций"))
        return w
    
    def _tab_settings(self):
        """Вкладка настроек"""
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.addWidget(QtWidgets.QLabel("Вкладка настроек"))
        return w
    
    def _update_search_results(self, transactions, sender_counter, sender_transactions):
        """Обновление результатов поиска"""
        logger.info(f"Найдено {len(transactions)} транзакций")
    
    def _update_progress_item(self, row, current, total):
        """Обновление прогресса элемента"""
        pass
    
    def _update_mass_statistics(self, sent, errors, gas_spent, total_amount):
        """Обновление статистики массовой рассылки"""
        logger.info(f"Отправлено: {sent}, Ошибок: {errors}, Газ: {gas_spent}, Сумма: {total_amount}")
    
    def _mass_distribution_finished(self):
        """Завершение массовой рассылки"""
        logger.info("Массовая рассылка завершена")
    
    def _mass_stop_distribution(self):
        """Остановка массовой рассылки"""
        self.mass_distribution_active = False
        logger.info("Массовая рассылка остановлена")


# Точка входа в приложение
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('fusion')
    
    # Настройка тёмной темы
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    
    # Создание и отображение главного окна
    window = MainWindow()
    window.show()
    
    # Запуск приложения
    sys.exit(app.exec_())
