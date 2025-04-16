import os
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin, unquote
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Optional, List
import logging
from parsers.base_parser import BaseParser, EventData

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../parser.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MTSParser(BaseParser):
    """Парсер событий с сайта MTS Live"""

    BASE_URL = 'https://live.mts.ru'
    THEATER_URL = f'{BASE_URL}/tula/collections/theater'
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _make_request(self, url: str) -> Optional[BeautifulSoup]:
        """Выполняет HTTP-запрос и возвращает BeautifulSoup объект"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Ошибка при запросе {url}: {str(e)}")
            return None

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Очищает название от недопустимых символов для файловой системы"""
        if not filename:
            return "Без названия"
        filename = unquote(filename)
        filename = filename.replace('&nbsp;', ' ').replace('\xa0', ' ')
        return re.sub(r'[<>:"/\\|?*]', '', filename).strip()

    def _parse_event_card(self, card: BeautifulSoup) -> Optional[Dict]:
        """Парсит карточку события с главной страницы"""
        try:
            title_tag = card.find('a', attrs={'data-type': 'nazvanie_meropriyatiya'})
            price_tag = card.find('a', attrs={'data-type': 'cena'})
            time_tag = card.find('time')
            venue_tag = card.find('a', attrs={'aria-disabled': 'false'})

            event_link = title_tag.get('href') if title_tag else None
            full_event_url = urljoin(self.BASE_URL, event_link) if event_link else None

            return {
                'title': title_tag.get('title') if title_tag else None,
                'price': price_tag.get_text(strip=True) if price_tag else "Цена не указана",
                'date': time_tag.get_text(strip=True) if time_tag else None,
                'venue': venue_tag.get('title') if venue_tag else None,
                'event_url': full_event_url
            }
        except Exception as e:
            logger.error(f"Ошибка при парсинге карточки события: {str(e)}")
            return None

    def _parse_event_page(self, event_url: str) -> Optional[Dict]:
        """Парсит страницу отдельного события"""
        try:
            soup = self._make_request(event_url)
            if not soup:
                return None

            # Основные данные
            description = soup.find('div', class_='CommonDescription_description__SSktZ')
            age_limit_tag = soup.find('div', class_='Badge_container__rAaAq')
            image = soup.find('img', class_='LazyImage_img__Nz285')

            # Место проведения
            venue_name_tag = soup.find('a', class_='VenueTitles_title__cttAS')
            venue_address_tag = soup.find('div', class_='VenueInfo_address__hH7tG')

            # Генерация тегов
            tags = self._generate_tags(
                age_limit=age_limit_tag.get_text(strip=True) if age_limit_tag else None,
                event_url=event_url
            )

            return {
                'description': description.get_text(strip=True) if description else None,
                'age_limit': age_limit_tag.get_text(strip=True) if age_limit_tag else None,
                'image': image.get('src') if image else None,
                'ticket_link': event_url,  # Используем URL события как ссылку на билеты
                'tags': tags,
                'venue_name': venue_name_tag.get_text(strip=True) if venue_name_tag else None,
                'venue_address': venue_address_tag.get_text(strip=True) if venue_address_tag else None
            }
        except Exception as e:
            logger.error(f"Ошибка при парсинге страницы события {event_url}: {str(e)}")
            return None

    @staticmethod
    def _generate_tags(age_limit: Optional[str], event_url: str) -> List[str]:
        """Генерирует теги на основе данных о событии"""
        tags = ['Культура', 'Искусство']

        # На основе возрастного ограничения
        if age_limit:
            if age_limit in ['0+', '6+', '12+']:
                tags.append('Для детей')
            elif age_limit in ['16+', '18+']:
                tags.append('Для взрослых')

        # На основе URL
        if 'theater' in event_url.lower():
            tags.append('Театр')
        elif 'concert' in event_url.lower():
            tags.append('Концерт')
        elif 'exhibition' in event_url.lower():
            tags.append('Выставка')

        return tags

    def _save_event(self, event: EventData) -> bool:
        """Сохраняет данные о событии в JSON файл"""
        try:
            if not event.title:
                return False

            safe_title = self._sanitize_filename(event.title)
            folder_path = os.path.join('../spectacles', 'mts', safe_title)
            os.makedirs(folder_path, exist_ok=True)

            json_path = os.path.join(folder_path, 'event_details.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(event.__dict__, f, ensure_ascii=False, indent=4)

            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении события {event.title}: {str(e)}")
            return False

    def parse_events(self, max_workers: int = 4) -> List[EventData]:
        """Основной метод парсинга событий"""
        logger.info("Начало парсинга событий")

        # Получаем главную страницу
        soup = self._make_request(self.THEATER_URL)
        if not soup:
            return []

        # Собираем все карточки событий
        event_cards = soup.find_all('div', class_='AnnouncementPreview_description__AVWrS')
        logger.info(f"Найдено {len(event_cards)} событий для парсинга")

        events = []

        # Используем ThreadPoolExecutor для ускорения парсинга
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []

            for card in event_cards:
                card_data = self._parse_event_card(card)
                if not card_data or not card_data.get('event_url'):
                    continue

                futures.append(executor.submit(self._process_single_event, card_data))

            for future in as_completed(futures):
                event = future.result()
                if event:
                    events.append(event)
                    self._save_event(event)

        logger.info(f"Парсинг завершен. Успешно обработано {len(events)} событий")
        return events

    def _process_single_event(self, card_data: Dict) -> Optional[EventData]:
        """Обрабатывает одно событие"""
        try:
            # Получаем данные со страницы события
            page_data = self._parse_event_page(card_data['event_url'])
            if not page_data:
                return None

            # Создаем объект события
            event = EventData(
                title=card_data['title'],
                price=card_data['price'],
                date=card_data['date'],
                place_name=card_data['venue'],
                age_limit=page_data['age_limit'],
                image=page_data['image'],
                ticket_link=page_data['ticket_link'],
                full_description=page_data['description'],
                place_address=page_data['venue_address'],
                tags=page_data['tags']
            )

            # Добавляем дополнительные теги на основе цены
            if event.price and event.price.lower() in ['бесплатно', 'free', '0']:
                event.tags.append('Бесплатно')
            else:
                event.tags.append('Платно')

            # Добавляем тег на основе даты (можно расширить логику)
            event.tags.append('Событие месяца')

            return event
        except Exception as e:
            logger.error(f"Ошибка при обработке события: {str(e)}")
            return None


if __name__ == "__main__":
    parser = MTSParser()
    events = parser.parse_events()