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
