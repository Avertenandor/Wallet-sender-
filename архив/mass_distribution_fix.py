    # --- Вкладка «Массовая рассылка» ---
    def _tab_mass_distribution(self):
        """Создание вкладки для массовой рассылки токенов
        
        #MCP:MASS_DIST - Вкладка массовой рассылки
        TODO:MCP - Добавить поддержку параллельной отправки
        """
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        
        # Группа импорта адресов
        import_group = QtWidgets.QGroupBox("Импорт адресов")
        import_layout = QtWidgets.QVBoxLayout(import_group)
        
        # Текстовое поле для адресов
        self.mass_addresses_text = QtWidgets.QTextEdit()
        self.mass_addresses_text.setPlaceholderText(
            "Вставьте адреса сюда (разделенные пробелом, запятой, точкой с запятой или новой строкой)"
        )
        self.mass_addresses_text.setMaximumHeight(100)
        import_layout.addWidget(self.mass_addresses_text)
        
        # Кнопки импорта
        import_buttons_layout = QtWidgets.QHBoxLayout()
        
        self.mass_paste_btn = QtWidgets.QPushButton("Вставить из буфера")
        self.mass_paste_btn.clicked.connect(self._mass_paste_addresses)
        import_buttons_layout.addWidget(self.mass_paste_btn)
        
        self.mass_import_excel_btn = QtWidgets.QPushButton("Импорт из Excel")
        self.mass_import_excel_btn.clicked.connect(self._mass_import_excel)
        self.mass_import_excel_btn.setEnabled(excel_enabled)
        import_buttons_layout.addWidget(self.mass_import_excel_btn)
        
        self.mass_clear_btn = QtWidgets.QPushButton("Очистить")
        self.mass_clear_btn.clicked.connect(lambda: self.mass_addresses_text.clear())
        import_buttons_layout.addWidget(self.mass_clear_btn)
        
        import_layout.addLayout(import_buttons_layout)
        
        # Метка с количеством адресов
        self.mass_addresses_count_label = QtWidgets.QLabel("Адресов: 0")
        import_layout.addWidget(self.mass_addresses_count_label)
        
        layout.addWidget(import_group)
        
        # Таблица адресов для рассылки
        self.mass_addresses_table = QtWidgets.QTableWidget(0, 3)
        self.mass_addresses_table.setHorizontalHeaderLabels(['Адрес', 'Статус', 'Отправлено'])
        self.mass_addresses_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.mass_addresses_table.setMaximumHeight(200)
        layout.addWidget(self.mass_addresses_table)
        
        # Кнопка обработки адресов
        self.mass_process_btn = QtWidgets.QPushButton("Обработать адреса")
        self.mass_process_btn.clicked.connect(self._mass_process_addresses)
        layout.addWidget(self.mass_process_btn)
        
        # Настройки рассылки
        settings_group = QtWidgets.QGroupBox("Настройки рассылки")
        settings_layout = QtWidgets.QGridLayout(settings_group)
        
        # Выбор токена
        settings_layout.addWidget(QtWidgets.QLabel("Токен:"), 0, 0)
        self.mass_token_combo = QtWidgets.QComboBox()
        self.mass_token_combo.addItems(['PLEX ONE', 'USDT', 'BNB', 'Другой...'])
        self.mass_token_combo.currentTextChanged.connect(self._mass_token_changed)
        settings_layout.addWidget(self.mass_token_combo, 0, 1)
        
        # Поле для произвольного адреса токена
        self.mass_custom_token = QtWidgets.QLineEdit()
        self.mass_custom_token.setPlaceholderText("Адрес контракта токена (0x...)")
        self.mass_custom_token.setVisible(False)
        settings_layout.addWidget(self.mass_custom_token, 0, 2)
        
        # Сумма для отправки
        settings_layout.addWidget(QtWidgets.QLabel("Сумма:"), 1, 0)
        self.mass_amount_spin = QtWidgets.QDoubleSpinBox()
        self.mass_amount_spin.setRange(0.00001, 1000000)
        self.mass_amount_spin.setDecimals(8)
        self.mass_amount_spin.setValue(0.05)  # По умолчанию 5 центов
        settings_layout.addWidget(self.mass_amount_spin, 1, 1)
        
        # Интервал между отправками
        settings_layout.addWidget(QtWidgets.QLabel("Интервал (сек):"), 2, 0)
        self.mass_interval_spin = QtWidgets.QSpinBox()
        self.mass_interval_spin.setRange(1, 600)
        self.mass_interval_spin.setValue(5)
        settings_layout.addWidget(self.mass_interval_spin, 2, 1)
        
        # Количество циклов
        settings_layout.addWidget(QtWidgets.QLabel("Количество циклов:"), 3, 0)
        self.mass_cycles_spin = QtWidgets.QSpinBox()
        self.mass_cycles_spin.setRange(1, 100)
        self.mass_cycles_spin.setValue(10)  # По умолчанию 10 раз
        settings_layout.addWidget(self.mass_cycles_spin, 3, 1)
        
        layout.addWidget(settings_group)
        
        # Статистика
        stats_group = QtWidgets.QGroupBox("Статистика")
        stats_layout = QtWidgets.QVBoxLayout(stats_group)
        
        self.mass_stats_label = QtWidgets.QLabel(
            "Всего адресов: 0 | Успешно: 0 | Ошибок: 0 | Осталось: 0"
        )
        stats_layout.addWidget(self.mass_stats_label)
        
        self.mass_progress = QtWidgets.QProgressBar()
        stats_layout.addWidget(self.mass_progress)
        
        self.mass_status_label = QtWidgets.QLabel("Готово к работе")
        stats_layout.addWidget(self.mass_status_label)
        
        layout.addWidget(stats_group)
        
        # Кнопки управления
        control_layout = QtWidgets.QHBoxLayout()
        
        self.mass_start_btn = QtWidgets.QPushButton("Начать рассылку")
        self.mass_start_btn.clicked.connect(self._mass_start_distribution)
        self.mass_start_btn.setEnabled(False)
        control_layout.addWidget(self.mass_start_btn)
        
        self.mass_pause_btn = QtWidgets.QPushButton("Пауза")
        self.mass_pause_btn.clicked.connect(self._mass_pause_distribution)
        self.mass_pause_btn.setEnabled(False)
        control_layout.addWidget(self.mass_pause_btn)
        
        self.mass_resume_btn = QtWidgets.QPushButton("Продолжить")
        self.mass_resume_btn.clicked.connect(self._mass_resume_distribution)
        self.mass_resume_btn.setEnabled(False)
        control_layout.addWidget(self.mass_resume_btn)
        
        self.mass_stop_btn = QtWidgets.QPushButton("Остановить")
        self.mass_stop_btn.clicked.connect(self._mass_stop_distribution)
        self.mass_stop_btn.setEnabled(False)
        control_layout.addWidget(self.mass_stop_btn)
        
        layout.addLayout(control_layout)
        
        # Дополнительные кнопки
        extra_layout = QtWidgets.QHBoxLayout()
        
        self.mass_save_list_btn = QtWidgets.QPushButton("Сохранить список")
        self.mass_save_list_btn.clicked.connect(self._mass_save_addresses)
        extra_layout.addWidget(self.mass_save_list_btn)
        
        self.mass_load_list_btn = QtWidgets.QPushButton("Загрузить список")
        self.mass_load_list_btn.clicked.connect(self._mass_load_addresses)
        extra_layout.addWidget(self.mass_load_list_btn)
        
        self.mass_export_results_btn = QtWidgets.QPushButton("Экспорт результатов")
        self.mass_export_results_btn.clicked.connect(self._mass_export_results)
        extra_layout.addWidget(self.mass_export_results_btn)
        
        layout.addLayout(extra_layout)
        
        # Инициализация переменных для массовой рассылки
        self.mass_distribution_active = False
        self.mass_distribution_paused = False
        self.mass_distribution_thread = None
        self.mass_addresses_list = []
        self.mass_current_cycle = 0
        self.mass_distribution_id = None
        
        # Обновление количества адресов при изменении текста
        self.mass_addresses_text.textChanged.connect(self._mass_update_address_count)
        
        return w
    
    def _mass_paste_addresses(self):
        """Вставка адресов из буфера обмена"""
        clipboard = QtWidgets.QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.mass_addresses_text.setText(text)
            logger.info("Адреса вставлены из буфера обмена")
    
    def _mass_import_excel(self):
        """Импорт адресов из Excel файла"""
        if not excel_enabled:
            QtWidgets.QMessageBox.warning(
                self, 'Ошибка',
                'Для импорта из Excel необходимо установить библиотеку openpyxl',
                QtWidgets.QMessageBox.Ok
            )
            return
        
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Выберите Excel файл', '', 'Excel files (*.xlsx *.xls)'
        )
        
        if not path:
            return
        
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path)
            ws = wb.active
            
            addresses = []
            for row in ws.iter_rows(values_only=True):
                for cell in row:
                    if cell and isinstance(cell, str) and cell.startswith('0x'):
                        addresses.append(cell.strip())
            
            if addresses:
                current_text = self.mass_addresses_text.toPlainText()
                if current_text:
                    self.mass_addresses_text.setText(current_text + '\n' + '\n'.join(addresses))
                else:
                    self.mass_addresses_text.setText('\n'.join(addresses))
                
                logger.info(f"Импортировано {len(addresses)} адресов из Excel")
            else:
                logger.warning("Не найдено адресов в Excel файле")
                
        except Exception as e:
            logger.error(f"Ошибка при импорте из Excel: {e}")
            QtWidgets.QMessageBox.critical(
                self, 'Ошибка',
                f'Не удалось импортировать адреса из Excel:\n{str(e)}',
                QtWidgets.QMessageBox.Ok
            )
    
    def _mass_token_changed(self, token):
        """Обработка изменения выбранного токена"""
        self.mass_custom_token.setVisible(token == "Другой...")
        if token == "Другой...":
            self.mass_custom_token.setFocus()
    
    def _mass_update_address_count(self):
        """Обновление счетчика адресов"""
        text = self.mass_addresses_text.toPlainText()
        if not text.strip():
            self.mass_addresses_count_label.setText("Адресов: 0")
            return
        
        # Разделяем по различным разделителям
        addresses = set()
        for separator in [' ', ',', ';', '\n', '\t']:
            parts = text.split(separator)
            for part in parts:
                part = part.strip()
                if part and part.startswith('0x') and len(part) == 42:
                    addresses.add(part.lower())
        
        self.mass_addresses_count_label.setText(f"Адресов: {len(addresses)}")
    
    def _mass_process_addresses(self):
        """Обработка и валидация введенных адресов"""
        text = self.mass_addresses_text.toPlainText()
        if not text.strip():
            QtWidgets.QMessageBox.warning(
                self, 'Предупреждение',
                'Введите адреса для рассылки',
                QtWidgets.QMessageBox.Ok
            )
            return
        
        # Парсим адреса
        raw_addresses = []
        for separator in [' ', ',', ';', '\n', '\t']:
            parts = text.split(separator)
            raw_addresses.extend([p.strip() for p in parts if p.strip()])
        
        # Валидация и удаление дубликатов
        valid_addresses = []
        invalid_addresses = []
        seen = set()
        
        for addr in raw_addresses:
            if not addr:
                continue
                
            # Проверка формата адреса
            if not addr.startswith('0x') or len(addr) != 42:
                invalid_addresses.append(addr)
                continue
            
            # Проверка на дубликаты
            addr_lower = addr.lower()
            if addr_lower in seen:
                continue
            
            # Дополнительная валидация через Web3 если доступно
            if blockchain_enabled:
                try:
                    if Web3.is_address(addr):
                        valid_addresses.append(addr)
                        seen.add(addr_lower)
                    else:
                        invalid_addresses.append(addr)
                except:
                    invalid_addresses.append(addr)
            else:
                # Базовая проверка без Web3
                try:
                    int(addr, 16)  # Проверка что это hex
                    valid_addresses.append(addr)
                    seen.add(addr_lower)
                except:
                    invalid_addresses.append(addr)
        
        # Показываем результаты валидации
        if invalid_addresses:
            msg = f"Найдено некорректных адресов: {len(invalid_addresses)}\n\n"
            msg += "Первые 10 некорректных адресов:\n"
            msg += '\n'.join(invalid_addresses[:10])
            if len(invalid_addresses) > 10:
                msg += f"\n... и еще {len(invalid_addresses) - 10}"
            
            QtWidgets.QMessageBox.warning(
                self, 'Некорректные адреса',
                msg,
                QtWidgets.QMessageBox.Ok
            )
        
        if not valid_addresses:
            QtWidgets.QMessageBox.critical(
                self, 'Ошибка',
                'Не найдено ни одного корректного адреса',
                QtWidgets.QMessageBox.Ok
            )
            return
        
        # Заполняем таблицу
        self.mass_addresses_table.setRowCount(0)
        self.mass_addresses_list = valid_addresses
        
        for addr in valid_addresses:
            row = self.mass_addresses_table.rowCount()
            self.mass_addresses_table.insertRow(row)
            
            # Адрес
            self.mass_addresses_table.setItem(row, 0, QtWidgets.QTableWidgetItem(addr))
            
            # Статус
            status_item = QtWidgets.QTableWidgetItem("Ожидание")
            self.mass_addresses_table.setItem(row, 1, status_item)
            
            # Счетчик отправок
            self.mass_addresses_table.setItem(row, 2, QtWidgets.QTableWidgetItem("0/0"))
        
        # Обновляем статистику
        self._mass_update_statistics()
        
        # Активируем кнопку начала рассылки
        self.mass_start_btn.setEnabled(True)
        
        logger.info(f"Обработано адресов: {len(valid_addresses)} корректных, {len(invalid_addresses)} некорректных")
    
    def _mass_update_statistics(self):
        """Обновление статистики рассылки"""
        total = len(self.mass_addresses_list)
        success = 0
        errors = 0
        pending = 0
        
        for row in range(self.mass_addresses_table.rowCount()):
            status = self.mass_addresses_table.item(row, 1).text()
            if "Успешно" in status:
                success += 1
            elif "Ошибка" in status:
                errors += 1
            else:
                pending += 1
        
        self.mass_stats_label.setText(
            f"Всего адресов: {total} | Успешно: {success} | Ошибок: {errors} | Осталось: {pending}"
        )
        
        # Обновляем прогресс
        if total > 0:
            progress = ((success + errors) * 100) // (total * self.mass_cycles_spin.value())
            self.mass_progress.setValue(min(progress, 100))
    
    def _mass_start_distribution(self):
        """Начало массовой рассылки"""
        if not self.mass_addresses_list:
            return
        
        # Проверяем приватный ключ
        if not self.pk:
            QtWidgets.QMessageBox.critical(
                self, 'Ошибка',
                'Не задан приватный ключ. Настройте его во вкладке "Настройки"',
                QtWidgets.QMessageBox.Ok
            )
            return
        
        # Получаем параметры
        token_name = self.mass_token_combo.currentText()
        if token_name == "Другой...":
            token_address = self.mass_custom_token.text().strip()
            if not token_address or not token_address.startswith('0x'):
                QtWidgets.QMessageBox.warning(
                    self, 'Ошибка',
                    'Введите корректный адрес токена',
                    QtWidgets.QMessageBox.Ok
                )
                return
            token_symbol = "CUSTOM"
        else:
            if token_name == "PLEX ONE":
                token_address = PLEX_CONTRACT
                token_symbol = "PLEX"
            elif token_name == "USDT":
                token_address = USDT_CONTRACT
                token_symbol = "USDT"
            elif token_name == "BNB":
                token_address = None  # Нативный токен
                token_symbol = "BNB"
        
        amount = self.mass_amount_spin.value()
        interval = self.mass_interval_spin.value()
        cycles = self.mass_cycles_spin.value()
        
        # Подтверждение
        total_amount = amount * len(self.mass_addresses_list) * cycles
        msg = f"Вы собираетесь отправить:\n\n"
        msg += f"Токен: {token_symbol}\n"
        msg += f"Сумма за транзакцию: {amount}\n"
        msg += f"Адресов: {len(self.mass_addresses_list)}\n"
        msg += f"Циклов: {cycles}\n"
        msg += f"Интервал: {interval} сек\n\n"
        msg += f"Общая сумма: {total_amount} {token_symbol}\n\n"
        msg += "Продолжить?"
        
        reply = QtWidgets.QMessageBox.question(
            self, 'Подтверждение рассылки',
            msg,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply != QtWidgets.QMessageBox.Yes:
            return
        
        # Создаем запись в БД
        self.mass_distribution_id = add_mass_distribution(
            name=f"Рассылка {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            token_address=token_address or "BNB",
            token_symbol=token_symbol,
            amount_per_tx=amount,
            total_addresses=len(self.mass_addresses_list),
            total_cycles=cycles,
            interval_seconds=interval
        )
        
        # Сбрасываем счетчики
        self.mass_current_cycle = 0
        for row in range(self.mass_addresses_table.rowCount()):
            self.mass_addresses_table.setItem(row, 1, QtWidgets.QTableWidgetItem("Ожидание"))
            self.mass_addresses_table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"0/{cycles}"))
        
        # Запускаем рассылку
        self.mass_distribution_active = True
        self.mass_distribution_paused = False
        
        # Обновляем UI
        self.mass_start_btn.setEnabled(False)
        self.mass_pause_btn.setEnabled(True)
        self.mass_stop_btn.setEnabled(True)
        self.mass_status_label.setText("Рассылка запущена")
        
        # Запускаем поток рассылки
        self.mass_distribution_thread = threading.Thread(
            target=self._mass_distribution_worker,
            args=(token_address, token_symbol, amount, interval, cycles),
            daemon=True
        )
        self.mass_distribution_thread.start()
        
        logger.info(f"Запущена массовая рассылка #{self.mass_distribution_id}")
    
    def _mass_distribution_worker(self, token_address, token_symbol, amount, interval, cycles):
        """Рабочий поток для массовой рассылки"""
        try:
            w3 = self.rpc.web3()
            account = Account.from_key(self.pk)
            
            for cycle in range(cycles):
                if not self.mass_distribution_active:
                    break
                
                self.mass_current_cycle = cycle + 1
                self.update_status_signal.emit(f"Цикл {cycle + 1} из {cycles}")
                
                for idx, address in enumerate(self.mass_addresses_list):
                    if not self.mass_distribution_active:
                        break
                    
                    # Проверка паузы
                    while self.mass_distribution_paused and self.mass_distribution_active:
                        time.sleep(0.5)
                    
                    if not self.mass_distribution_active:
                        break
                    
                    # Обновляем статус
                    self.update_address_status.emit(idx, "⟳ Отправка...")
                    
                    try:
                        # Отправка транзакции
                        if token_address:  # ERC20 токен
                            # Получаем контракт токена
                            token_contract = w3.eth.contract(
                                address=Web3.to_checksum_address(token_address),
                                abi=ERC20_ABI
                            )
                            
                            # Получаем decimals
                            decimals = token_contract.functions.decimals().call()
                            
                            # Конвертируем сумму
                            amount_wei = int(amount * (10 ** decimals))
                            
                            # Создаем транзакцию
                            tx = token_contract.functions.transfer(
                                Web3.to_checksum_address(address),
                                amount_wei
                            ).build_transaction({
                                'from': account.address,
                                'nonce': w3.eth.get_transaction_count(account.address),
                                'gas': 100000,
                                'gasPrice': w3.to_wei(self.cfg.get_gas_price(), 'gwei')
                            })
                        else:  # BNB (нативный токен)
                            tx = {
                                'from': account.address,
                                'to': Web3.to_checksum_address(address),
                                'value': w3.to_wei(amount, 'ether'),
                                'nonce': w3.eth.get_transaction_count(account.address),
                                'gas': 21000,
                                'gasPrice': w3.to_wei(self.cfg.get_gas_price(), 'gwei')
                            }
                        
                        # Подписываем и отправляем
                        signed_tx = account.sign_transaction(tx)
                        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                        tx_hash_hex = tx_hash.hex()
                        
                        # Сохраняем в БД
                        add_mass_distribution_item(
                            self.mass_distribution_id,
                            address,
                            cycle + 1,
                            tx_hash_hex,
                            'success'
                        )
                        
                        # Обновляем UI
                        self.update_address_status.emit(idx, "✓ Успешно")
                        
                        # Обновляем счетчик отправок
                        QtCore.QMetaObject.invokeMethod(
                            self.mass_addresses_table, "setItem",
                            QtCore.Qt.QueuedConnection,
                            QtCore.Q_ARG(int, idx),
                            QtCore.Q_ARG(int, 2),
                            QtCore.Q_ARG(QtWidgets.QTableWidgetItem, 
                                       QtWidgets.QTableWidgetItem(f"{cycle + 1}/{cycles}"))
                        )
                        
                        logger.info(f"Отправлено {amount} {token_symbol} на {address} (tx: {tx_hash_hex})")
                        
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"Ошибка отправки на {address}: {error_msg}")
                        
                        # Сохраняем ошибку в БД
                        add_mass_distribution_item(
                            self.mass_distribution_id,
                            address,
                            cycle + 1,
                            None,
                            'error',
                            error_msg
                        )
                        
                        # Обновляем UI
                        self.update_address_status.emit(idx, "✗ Ошибка")
                    
                    # Обновляем общую статистику
                    QtCore.QMetaObject.invokeMethod(
                        self, "_mass_update_statistics",
                        QtCore.Qt.QueuedConnection
                    )
                    
                    # Задержка между отправками
                    if idx < len(self.mass_addresses_list) - 1:
                        time.sleep(interval)
                
                # Задержка между циклами
                if cycle < cycles - 1 and self.mass_distribution_active:
                    self.update_status_signal.emit(f"Пауза перед циклом {cycle + 2}")
                    time.sleep(interval * 2)
            
            # Завершение рассылки
            if self.mass_distribution_active:
                update_mass_distribution_status(self.mass_distribution_id, 'completed')
                self.update_status_signal.emit("Рассылка завершена")
            else:
                update_mass_distribution_status(self.mass_distribution_id, 'cancelled')
                self.update_status_signal.emit("Рассылка отменена")
            
        except Exception as e:
            logger.error(f"Критическая ошибка в потоке рассылки: {e}")
            update_mass_distribution_status(self.mass_distribution_id, 'error')
            self.update_status_signal.emit(f"Ошибка: {str(e)}")
        
        finally:
            self.mass_distribution_active = False
            
            # Обновляем UI
            QtCore.QMetaObject.invokeMethod(
                self, "_mass_distribution_finished",
                QtCore.Qt.QueuedConnection
            )
    
    def _mass_distribution_finished(self):
        """Завершение массовой рассылки"""
        self.mass_start_btn.setEnabled(True)
        self.mass_pause_btn.setEnabled(False)
        self.mass_resume_btn.setEnabled(False)
        self.mass_stop_btn.setEnabled(False)
        self.mass_status_label.setText("Рассылка завершена")
        
        # Показываем итоговую статистику
        stats = get_mass_distribution_statistics(self.mass_distribution_id)
        
        msg = f"Рассылка завершена!\n\n"
        msg += f"Всего транзакций: {stats['total']}\n"
        msg += f"Успешно: {stats['success']}\n"
        msg += f"Ошибок: {stats['errors']}\n"
        
        QtWidgets.QMessageBox.information(
            self, 'Рассылка завершена',
            msg,
            QtWidgets.QMessageBox.Ok
        )
    
    def _mass_pause_distribution(self):
        """Приостановка рассылки"""
        self.mass_distribution_paused = True
        self.mass_pause_btn.setEnabled(False)
        self.mass_resume_btn.setEnabled(True)
        self.mass_status_label.setText("Рассылка приостановлена")
        logger.info("Массовая рассылка приостановлена")
    
    def _mass_resume_distribution(self):
        """Возобновление рассылки"""
        self.mass_distribution_paused = False
        self.mass_pause_btn.setEnabled(True)
        self.mass_resume_btn.setEnabled(False)
        self.mass_status_label.setText("Рассылка возобновлена")
        logger.info("Массовая рассылка возобновлена")
    
    def _mass_stop_distribution(self):
        """Остановка рассылки"""
        reply = QtWidgets.QMessageBox.question(
            self, 'Подтверждение',
            'Вы уверены, что хотите остановить рассылку?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            self.mass_distribution_active = False
            self.mass_distribution_paused = False
            self.mass_status_label.setText("Остановка рассылки...")
            logger.info("Массовая рассылка остановлена пользователем")
    
    def _mass_save_addresses(self):
        """Сохранение списка адресов в файл"""
        if not self.mass_addresses_list:
            QtWidgets.QMessageBox.warning(
                self, 'Предупреждение',
                'Нет адресов для сохранения',
                QtWidgets.QMessageBox.Ok
            )
            return
        
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Сохранить список адресов', '', 'Text files (*.txt);;CSV files (*.csv)'
        )
        
        if not path:
            return
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                if path.endswith('.csv'):
                    f.write('address\n')
                    for addr in self.mass_addresses_list:
                        f.write(f'{addr}\n')
                else:
                    f.write('\n'.join(self.mass_addresses_list))
            
            logger.info(f"Список адресов сохранен в {path}")
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении списка адресов: {e}")
            QtWidgets.QMessageBox.critical(
                self, 'Ошибка',
                f'Не удалось сохранить список адресов:\n{str(e)}',
                QtWidgets.QMessageBox.Ok
            )
    
    def _mass_load_addresses(self):
        """Загрузка списка адресов из файла"""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Загрузить список адресов', '', 'Text files (*.txt);;CSV files (*.csv);;All files (*.*)'
        )
        
        if not path:
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Добавляем к существующим адресам
            current_text = self.mass_addresses_text.toPlainText()
            if current_text:
                self.mass_addresses_text.setText(current_text + '\n' + content)
            else:
                self.mass_addresses_text.setText(content)
            
            logger.info(f"Список адресов загружен из {path}")
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке списка адресов: {e}")
            QtWidgets.QMessageBox.critical(
                self, 'Ошибка',
                f'Не удалось загрузить список адресов:\n{str(e)}',
                QtWidgets.QMessageBox.Ok
            )
    
    def _mass_export_results(self):
        """Экспорт результатов рассылки"""
        if not self.mass_distribution_id:
            QtWidgets.QMessageBox.warning(
                self, 'Предупреждение',
                'Нет данных для экспорта',
                QtWidgets.QMessageBox.Ok
            )
            return
        
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Экспорт результатов', 
            f'mass_distribution_{self.mass_distribution_id}.csv',
            'CSV files (*.csv)'
        )
        
        if not path:
            return
        
        try:
            # Получаем данные из БД
            items = get_mass_distribution_items(self.mass_distribution_id)
            
            with open(path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Адрес', 'Цикл', 'Хэш транзакции', 'Статус', 'Ошибка', 'Время'])
                
                for item in items:
                    writer.writerow([
                        item['address'],
                        item['cycle'],
                        item['tx_hash'] or '',
                        item['status'],
                        item['error_message'] or '',
                        item['sent_at'] or ''
                    ])
            
            logger.info(f"Результаты экспортированы в {path}")
            
            QtWidgets.QMessageBox.information(
                self, 'Успешно',
                f'Результаты экспортированы в:\n{path}',
                QtWidgets.QMessageBox.Ok
            )
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте результатов: {e}")
            QtWidgets.QMessageBox.critical(
                self, 'Ошибка',
                f'Не удалось экспортировать результаты:\n{str(e)}',
                QtWidgets.QMessageBox.Ok
            )
