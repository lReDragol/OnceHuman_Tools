import sys
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QFileDialog, QPushButton
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QRect, QPoint
import pyautogui
import json

class MainMenu(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Главное меню')
        self.setGeometry(100, 100, 400, 200)

        load_button = QPushButton('Загрузить скриншот', self)
        load_button.setGeometry(50, 80, 150, 40)
        load_button.clicked.connect(self.load_screenshot)

        screenshot_button = QPushButton('Сделать скриншот', self)
        screenshot_button.setGeometry(210, 80, 150, 40)
        screenshot_button.clicked.connect(self.take_screenshot)

        self.show()

    def load_screenshot(self):
        image_path, _ = QFileDialog.getOpenFileName(self, 'Выберите изображение', '', 'PNG files (*.png)')
        if image_path:
            self.open_screenshot_selector(image_path)

    def take_screenshot(self):
        self.hide()
        screenshot = pyautogui.screenshot()
        screenshot_path = "screenshot.png"
        screenshot.save(screenshot_path)
        self.open_screenshot_selector(screenshot_path)
        self.show()

    def open_screenshot_selector(self, image_path):
        self.selector_window = ScreenshotSelector(image_path)
        self.selector_window.show()


class ScreenshotSelector(QMainWindow):
    def __init__(self, image_path):
        super().__init__()
        self.setWindowTitle('Выбор областей')
        self.setGeometry(100, 100, 800, 600)

        self.image_label = QLabel(self)
        self.image_label.setGeometry(0, 0, 800, 600)
        self.image_label.setAlignment(Qt.AlignCenter)

        self.start_point = QPoint()
        self.end_point = QPoint()
        self.rectangles = []

        self.load_image(image_path)
        self.initUI()

    def initUI(self):
        self.image_label.mousePressEvent = self.on_mouse_press
        self.image_label.mouseMoveEvent = self.on_mouse_move
        self.image_label.mouseReleaseEvent = self.on_mouse_release

        self.save_button = QPushButton('Сохранить', self)
        self.save_button.setGeometry(10, 10, 100, 30)
        self.save_button.clicked.connect(self.save_config)

        self.clear_button = QPushButton('Очистить', self)
        self.clear_button.setGeometry(120, 10, 100, 30)
        self.clear_button.clicked.connect(self.clear_rectangles)

    def load_image(self, image_path):
        self.image = QPixmap(image_path)
        self.image_label.setPixmap(self.image)
        self.image_label.adjustSize()

    def on_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self.start_point = event.pos()
            self.end_point = self.start_point
            self.backup_image = self.image.copy()  # Сохраняем исходное изображение

    def on_mouse_move(self, event):
        if event.buttons() & Qt.LeftButton:
            self.end_point = event.pos()
            self.image_label.setPixmap(self.backup_image)  # Восстанавливаем исходное изображение
            self.update()

    def on_mouse_release(self, event):
        if event.button() == Qt.LeftButton:
            if len(self.rectangles) < 3:  # Проверка на количество областей
                rect = QRect(self.start_point, self.end_point).normalized()
                self.rectangles.append(rect)
                self.start_point = QPoint()
                self.end_point = QPoint()
                self.backup_image = self.image.copy()  # Обновляем исходное изображение после завершения выделения
                self.update()

    def paintEvent(self, event):
        if self.image_label.pixmap():
            painter = QPainter(self.image_label.pixmap())
            pen = QPen(QColor(255, 0, 0), 2)
            painter.setPen(pen)
            font = painter.font()
            font.setPointSize(20)
            painter.setFont(font)

            for i, rect in enumerate(self.rectangles):
                painter.drawRect(rect)
                text = str(i + 1)
                painter.drawText(rect.center(), text)

            if len(self.rectangles) < 3 and not self.start_point.isNull() and not self.end_point.isNull():
                painter.drawRect(QRect(self.start_point, self.end_point).normalized())

            painter.end()

    def save_config(self):
        modified_areas = {str(i+1): [rect.topLeft().x(), rect.topLeft().y(), rect.bottomRight().x(), rect.bottomRight().y()]
                          for i, rect in enumerate(self.rectangles)}

        with open("coordinates.json", "w") as f_coords:
            json.dump(modified_areas, f_coords, indent=2)
        print("Данные сохранены в coordinates.json")

    def clear_rectangles(self):
        self.rectangles = []
        self.image_label.setPixmap(self.backup_image)
        self.update()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_menu = MainMenu()
    sys.exit(app.exec_())
