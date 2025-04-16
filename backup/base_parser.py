import re
from dataclasses import dataclass
from typing import List, Optional
import logging
import os
import json
from urllib.parse import unquote


@dataclass
class EventData:
    """Класс для хранения данных о событии"""
    title: str
    age_limit: Optional[str] = None
    image: Optional[str] = None
    date: Optional[str] = None
    place_name: Optional[str] = None
    place_address: Optional[str] = None
    price: Optional[str] = None
    ticket_link: Optional[str] = None
    full_description: Optional[str] = None
    tags: Optional[List[str]] = None
    gallery_images: Optional[List[str]] = None


class BaseParser:
    """Базовый класс для всех парсеров"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Очищает название от недопустимых символов для файловой системы"""
        if not filename:
            return "Без названия"
        filename = unquote(filename)
        filename = filename.replace('&nbsp;', ' ').replace('\xa0', ' ')
        return re.sub(r'[<>:"/\\|?*]', '', filename).strip()

    def _save_event(self, event: EventData, source_name: str) -> bool:
        """Сохраняет данные о событии в JSON файл"""
        try:
            if not event.title:
                return False

            safe_title = self._sanitize_filename(event.title)
            folder_path = os.path.join('spectacles', source_name, safe_title)
            os.makedirs(folder_path, exist_ok=True)

            json_path = os.path.join(folder_path, 'event_details.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(event.__dict__, f, ensure_ascii=False, indent=4)

            self.logger.info(f"Сохранено событие: {event.title}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении события {event.title}: {str(e)}")
            return False