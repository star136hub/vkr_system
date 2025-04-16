import eel
import json
import os
import shutil

# Инициализация Eel
eel.init('web')

# Путь к папке с избранными
FAVOURITES_PATH = os.path.join(os.path.dirname(__file__), 'favourites')

# Создаем папку favourites, если её нет
if not os.path.exists(FAVOURITES_PATH):
    os.makedirs(FAVOURITES_PATH)

# Список папок со спектаклями
SPECTACLE_FOLDERS = [
    'spectacles/afisha',
    'spectacles/culture',
    'spectacles/mts'
]


@eel.expose
def load_events():
    events = []
    source_names = {
        'afisha': 'Афиша города',
        'culture': 'Культура.рф',
        'mts': 'МТС'
    }

    for folder in SPECTACLE_FOLDERS:
        spectacle_path = os.path.join(os.path.dirname(__file__), folder)

        if not os.path.exists(spectacle_path):
            continue

        # Получаем название источника из пути
        source = folder.split('/')[-1]
        source_name = source_names.get(source, 'Неизвестный источник')

        for root, dirs, files in os.walk(spectacle_path):
            for dir_name in dirs:
                event_path = os.path.join(root, dir_name)
                event_details_path = os.path.join(event_path, 'event_details.json')

                if os.path.exists(event_details_path):
                    with open(event_details_path, 'r', encoding='utf-8') as file:
                        event_data = json.load(file)

                    # Добавляем информацию об источнике
                    event_data['source'] = source_name
                    event_data['source_slug'] = source  # сохраняем и slug для возможного использования

                    # Остальные поля как раньше...
                    event_data['main_image'] = os.path.join(folder, dir_name, 'main_image.jpg')

                    gallery_images = []
                    for file_name in os.listdir(event_path):
                        if file_name.startswith('gallery_image') and file_name.endswith('.jpg'):
                            gallery_images.append(os.path.join(folder, dir_name, file_name))

                    event_data['gallery_images'] = gallery_images
                    event_data['path'] = os.path.join(folder, dir_name)

                    events.append(event_data)

            break

    return events


@eel.expose
def load_favourites():
    events = []

    # Сканируем папку /favourites
    for root, dirs, files in os.walk(FAVOURITES_PATH):
        for dir_name in dirs:
            event_path = os.path.join(root, dir_name)

            # Проверяем, есть ли файл event_details.json
            event_details_path = os.path.join(event_path, 'event_details.json')
            if os.path.exists(event_details_path):
                with open(event_details_path, 'r', encoding='utf-8') as file:
                    event_data = json.load(file)

                # Добавляем путь к основному изображению
                event_data['main_image'] = os.path.join('favourites', dir_name, 'main_image.jpg')

                # Добавляем галерею изображений
                gallery_images = []
                for file_name in os.listdir(event_path):
                    if file_name.startswith('gallery_image') and file_name.endswith('.jpg'):
                        gallery_images.append(os.path.join('favourites', dir_name, file_name))

                event_data['gallery_images'] = gallery_images

                # Добавляем путь к папке спектакля
                event_data['path'] = dir_name

                events.append(event_data)

        break  # Останавливаемся на первом уровне вложенности (только папки спектаклей)

    return events


@eel.expose
def add_to_favourites(event_path):
    # Нормализуем путь (заменяем все слеши на системные разделители)
    normalized_path = event_path.replace('/', os.sep).replace('\\', os.sep)

    # Полный путь к исходной папке
    source_path = os.path.join(os.path.dirname(__file__), normalized_path)

    # Проверяем существование исходного пути
    if not os.path.exists(source_path):
        print(f"Source path not found: {source_path}")
        return False

    # Путь для избранного (берем только имя папки события)
    event_name = os.path.basename(normalized_path)
    destination_path = os.path.join(FAVOURITES_PATH, event_name)

    if not os.path.exists(destination_path):
        shutil.copytree(source_path, destination_path)
        return True
    return False


@eel.expose
def check_if_favourite(event_path):
    # Берем только имя папки события (последнюю часть пути)
    event_name = os.path.basename(event_path.replace('/', os.sep).replace('\\', os.sep))
    return os.path.exists(os.path.join(FAVOURITES_PATH, event_name))

@eel.expose
def remove_from_favourites(event_path):
    # Берем только имя папки события
    event_name = os.path.basename(event_path.replace('/', os.sep).replace('\\', os.sep))
    destination_path = os.path.join(FAVOURITES_PATH, event_name)
    if os.path.exists(destination_path):
        shutil.rmtree(destination_path)
        return True
    return False


@eel.expose
def load_event(event_path):
    # Полный путь к папке с событием
    event_path_full = os.path.join(os.path.dirname(__file__), event_path)

    # Проверяем, есть ли файл event_details.json
    event_details_path = os.path.join(event_path_full, 'event_details.json')
    if os.path.exists(event_details_path):
        with open(event_details_path, 'r', encoding='utf-8') as file:
            event_data = json.load(file)

        # Удаляем поля со значением null
        event_data = {k: v for k, v in event_data.items() if v is not None}

        # Добавляем путь к основному изображению
        event_data['main_image'] = os.path.join(event_path, 'main_image.jpg')

        # Добавляем галерею изображений, если она есть
        gallery_images = []
        for file_name in os.listdir(event_path_full):
            if file_name.startswith('gallery_image') and file_name.endswith('.jpg'):
                gallery_images.append(os.path.join(event_path, file_name))

        if gallery_images:
            event_data['gallery_images'] = gallery_images

        return event_data
    return None


# Путь к папке с аккаунтами
ACCOUNTS_PATH = os.path.join(os.path.dirname(__file__), 'Accounts')

# Создаем папку Accounts, если её нет
if not os.path.exists(ACCOUNTS_PATH):
    os.makedirs(ACCOUNTS_PATH)
    print(f"Папка {ACCOUNTS_PATH} создана.")
else:
    print(f"Папка {ACCOUNTS_PATH} уже существует.")


# main.py
@eel.expose
def add_user(username, encrypted_password):
    # print(f"Получены данные: username={username}, password={encrypted_password}")
    # Путь к файлу пользователя
    user_file_path = os.path.join(ACCOUNTS_PATH, f"{username}.json")

    # Проверяем, существует ли пользователь
    if os.path.exists(user_file_path):
        print(f"Пользователь {username} уже существует.")
        return False  # Пользователь уже существует

    # Создаем данные пользователя
    user_data = {
        "username": username,
        "password": encrypted_password
    }

    # Сохраняем данные пользователя в файл
    try:
        with open(user_file_path, 'w', encoding='utf-8') as file:
            json.dump(user_data, file, ensure_ascii=False, indent=4)
        print(f"Пользователь {username} успешно добавлен.")
        return True  # Пользователь успешно добавлен
    except Exception as e:
        print(f"Ошибка при сохранении пользователя {username}: {e}")
        return False  # Ошибка при сохранении


@eel.expose
def check_user(username, encrypted_password):
    # Путь к файлу пользователя
    user_file_path = os.path.join(ACCOUNTS_PATH, f"{username}.json")

    # Проверяем, существует ли файл пользователя
    if not os.path.exists(user_file_path):
        return False  # Пользователь не найден

    # Загружаем данные пользователя
    try:
        with open(user_file_path, 'r', encoding='utf-8') as file:
            user_data = json.load(file)
        # Проверяем пароль
        return user_data["password"] == encrypted_password
    except Exception as e:
        print(f"Ошибка при загрузке пользователя: {e}")
        return False  # Ошибка при загрузке


# Запуск приложения
eel.start('login.html', mode='chrome', position=(0, 0), size=(1920, 1080))