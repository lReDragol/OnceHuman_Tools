import os
from PIL import Image

# Путь к директории с изображениями
base_path = r'D:\Python Program\once human\data\icons\mods'

# Размер для обрезки
new_size = (85, 85)

def resize_and_crop_image(image_path, save_path, size):
    with Image.open(image_path) as img:
        width, height = img.size
        # Найдем минимальную сторону для обрезки
        min_side = min(width, height)
        # Рассчитываем координаты для обрезки по центру
        left = (width - min_side) / 2
        top = (height - min_side) / 2
        right = (width + min_side) / 2
        bottom = (height + min_side) / 2
        # Обрезаем изображение по квадрату
        img_cropped = img.crop((left, top, right, bottom))
        # Изменяем размер до 85x85
        img_resized = img_cropped.resize(size)
        # Сохраняем обработанное изображение
        img_resized.save(save_path)

def process_directory(directory_path, size):
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                file_path = os.path.join(root, file)
                print(f'Processing: {file_path}')
                # Генерируем путь для сохранения
                save_path = file_path  # Можно изменить, если нужно сохранить в другой папке
                # Обрезаем и изменяем размер
                resize_and_crop_image(file_path, save_path, size)

# Запускаем обработку
process_directory(base_path, new_size)
