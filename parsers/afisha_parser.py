import os
import aiohttp
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin, unquote
import re
import asyncio
from typing import Dict, Optional, List
import logging
from parsers.base_parser import BaseParser, EventData
from datetime import datetime

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


class AsyncAfishaParser(BaseParser):
    """Асинхронный парсер событий с сайта Afisha Goroda"""

    BASE_URL = 'https://tula.afishagoroda.ru'
    THEATER_URL = f'{BASE_URL}/events/teatr'
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    CONCURRENCY_LIMIT = 10

    def __init__(self):
        self.session = None
        self.semaphore = asyncio.Semaphore(self.CONCURRENCY_LIMIT)

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.HEADERS)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Очищает название от недопустимых символов для файловой системы"""
        if not filename:
            return "Без названия"
        filename = unquote(filename)
        filename = filename.replace('&nbsp;', ' ').replace('\xa0', ' ')
        return re.sub(r'[<>:"/\\|?*]', '', filename).strip()

    @staticmethod
    def _parse_event_date(date_text: str) -> Optional[str]:
        """Парсит строку с датой события в формат DD.MM.YYYY HH:MM"""
        try:
            # Нормализуем строку: удаляем лишние пробелы и приводим к нижнему регистру
            date_text = ' '.join(date_text.strip().split()).lower()

            # Словарь для преобразования месяцев
            month_map = {
                "января": "01", "февраля": "02", "марта": "03", "апреля": "04",
                "мая": "05", "июня": "06", "июля": "07", "августа": "08",
                "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12"
            }

            # Удаляем названия дней недели (понедельник, вторник и т.д.)
            days_of_week = ["понедельник", "вторник", "среда", "четверг",
                            "пятница", "суббота", "воскресенье"]
            for day in days_of_week:
                date_text = date_text.replace(day, '')

            # Разделяем дату и время
            if ' ' in date_text:
                date_part, *time_parts = date_text.split()
                time_part = time_parts[-1] if time_parts and ':' in time_parts[-1] else "00:00"
            else:
                date_part = date_text
                time_part = "00:00"

            # Проверяем и нормализуем время
            if ':' in time_part:
                hours, minutes = time_part.split(':')[:2]
                time_part = f"{hours.zfill(2)}:{minutes.zfill(2)}"
            else:
                time_part = "00:00"

            # Извлекаем день и месяц
            day = ''
            month_name = ''

            # Ищем цифры в начале строки (день)
            for i, char in enumerate(date_part):
                if char.isdigit():
                    day += char
                else:
                    break

            # Остаток строки после дня - это месяц
            if day:
                month_part = date_part[len(day):].strip()

                # Ищем полное название месяца
                for month in month_map:
                    if month_part.startswith(month):
                        month_name = month
                        break

            if not day or not month_name:
                logger.warning(f"Не удалось извлечь дату из: {date_text}")
                return None

            # Проверяем корректность дня
            day = day.zfill(2)
            if not day.isdigit() or int(day) < 1 or int(day) > 31:
                logger.warning(f"Некорректный день: {day}")
                return None

            month = month_map.get(month_name)
            if not month:
                logger.warning(f"Неизвестный месяц: {month_name}")
                return None

            # Определяем год
            current_year = datetime.now().year
            try:
                event_date = datetime.strptime(f"{day}.{month}.{current_year} {time_part}", "%d.%m.%Y %H:%M")
            except ValueError as e:
                logger.warning(f"Ошибка при парсинге даты {date_text}: {str(e)}")
                return None

            # Проверяем, не прошла ли дата
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if event_date <= today:
                event_date = event_date.replace(year=current_year + 1)

            return event_date.strftime("%d.%m.%Y %H:%M")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при обработке даты {date_text}: {str(e)}")
            return None

    async def _make_request(self, url: str) -> Optional[BeautifulSoup]:
        """Выполняет асинхронный HTTP-запрос"""
        async with self.semaphore:
            try:
                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    response.raise_for_status()
                    html = await response.text()
                    return BeautifulSoup(html, 'html.parser')
            except Exception as e:
                logger.error(f"Ошибка при запросе {url}: {str(e)}")
                return None

    async def _parse_event_card(self, card: BeautifulSoup) -> Optional[Dict]:
        """Парсит карточку события с главной страницы"""
        try:
            title_tag = card.find('a', class_='title')
            event_url = urljoin(self.BASE_URL, title_tag['href']) if title_tag else None
            title = title_tag.get_text(strip=True) if title_tag else None

            return {
                'title': title,
                'event_url': event_url
            }
        except Exception as e:
            logger.error(f"Ошибка при парсинге карточки события: {str(e)}")
            return None

    async def _parse_event_page(self, event_url: str) -> Optional[Dict]:
        """Парсит страницу отдельного события"""
        try:
            soup = await self._make_request(event_url)
            if not soup:
                return None

            event_data = {}

            # Название
            title_tag = soup.find('h1')
            event_data['title'] = title_tag.get_text(strip=True) if title_tag else None

            # Возрастное ограничение
            info_line = soup.find('div', class_='info-line')
            if info_line:
                parts = info_line.get_text(strip=True).split('•')
                if len(parts) > 1:
                    event_data['age_limit'] = parts[-1].strip()
                else:
                    event_data['age_limit'] = None

            # Изображение
            image_tag = soup.find('img', class_='img')
            event_data['image'] = urljoin(self.BASE_URL, image_tag['src']) if image_tag and image_tag.has_attr(
                'src') else None

            # Дата и время
            date_block = soup.find('div', class_='date-start')
            if date_block:
                date_text = date_block.get_text(strip=True)
                event_data['date'] = self._parse_event_date(date_text)

            # Место проведения
            place_block = soup.find('div', class_='place')
            if place_block:
                place_text = place_block.get_text(strip=True).replace('\xa0', ' ')
                place_parts = place_text.split('г. ', 1)
                event_data['place_name'] = place_parts[0].strip()
                event_data['place_address'] = f"г. {place_parts[1].strip()}" if len(place_parts) > 1 else None

            # Цена
            price_block = soup.find('div', class_='price')
            if price_block:
                price_text = price_block.get_text(strip=True).replace('\xa0', ' ')
                event_data['price'] = price_text.replace('Стоимость билетов', '').strip()

            # Ссылка на билеты
            ticket_link = (
                    soup.find('a', class_='btn', target='_blank',
                              string=lambda text: text and "Купить билет" in text.strip()) or
                    soup.find('a', class_='js-yaticket-button', target='_blank')
            )

            if not ticket_link:
                span = soup.find('span', string=lambda text: text and "Купить билет" in text.strip())
                ticket_link = span.find_parent('a', target='_blank') if span else None

            event_data['ticket_link'] = ticket_link['href'] if ticket_link and ticket_link.has_attr('href') else None

            # Полное описание
            full_desc = []
            main_desc_block = soup.find('div', class_='redactor content')
            if main_desc_block:
                full_desc.append(main_desc_block.get_text(strip=True).replace('\xa0', ' '))

            additional_block = soup.find('div', class_='redactor content-bottom')
            if additional_block:
                full_desc.append(additional_block.get_text(separator=' ').strip())

            event_data['full_description'] = '\n\n'.join(full_desc) if full_desc else None

            # Галерея изображений
            gallery = soup.find_all('a', {'data-fancybox': 'events-gallery'})[:3]
            event_data['gallery_images'] = [
                urljoin(self.BASE_URL, img['href'])
                for img in gallery
                if not img['href'].startswith('https://')
            ]

            # Генерация тегов
            event_data['tags'] = self._generate_tags(
                age_limit=event_data.get('age_limit'),
                event_url=event_url,
                price=event_data.get('price')
            )

            return event_data
        except Exception as e:
            logger.error(f"Ошибка при парсинге страницы события {event_url}: {str(e)}")
            return None

    @staticmethod
    def _generate_tags(age_limit: Optional[str], event_url: str, price: Optional[str]) -> List[str]:
        """Генерирует теги на основе данных о событии"""
        tags = ['Театр', 'Культура']  # Базовые теги

        # На основе возрастного ограничения
        if age_limit:
            if age_limit in ['0+', '6+', '12+']:
                tags.append('Для детей')
            elif age_limit in ['16+', '18+']:
                tags.append('Для взрослых')

        # На основе цены
        if price and ('бесплатно' in price.lower() or 'free' in price.lower() or price == '0'):
            tags.append('Бесплатно')
        elif price:
            tags.append('Платно')

        # Общие теги
        tags.append('Событие месяца')

        return tags

    async def _save_event(self, event: EventData) -> bool:
        """Сохраняет данные о событии в JSON файл"""
        try:
            if not event.title:
                return False

            safe_title = self._sanitize_filename(event.title)
            folder_path = os.path.join('../spectacles', 'afisha', safe_title)
            os.makedirs(folder_path, exist_ok=True)

            json_path = os.path.join(folder_path, 'event_details.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(event.__dict__, f, ensure_ascii=False, indent=4)

            logger.info(f"Сохранено событие: {event.title}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении события {event.title}: {str(e)}")
            return False

    async def parse_events(self) -> List[EventData]:
        """Основной метод парсинга событий"""
        logger.info("Начало парсинга событий")
        soup = await self._make_request(self.THEATER_URL)
        if not soup:
            return []

        event_cards = soup.find_all('div', class_='events-elem')
        logger.info(f"Найдено {len(event_cards)} событий для парсинга")

        tasks = []
        for card in event_cards:
            card_data = await self._parse_event_card(card)
            if card_data and card_data.get('event_url'):
                tasks.append(self._process_single_event(card_data))

        results = await asyncio.gather(*tasks)
        return [event for event in results if event]

    async def _process_single_event(self, card_data: Dict) -> Optional[EventData]:
        """Обрабатывает одно событие"""
        try:
            page_data = await self._parse_event_page(card_data['event_url'])
            if not page_data:
                return None

            event = EventData(
                title=card_data['title'],
                age_limit=page_data.get('age_limit'),
                image=page_data.get('image'),
                date=page_data.get('date'),
                place_name=page_data.get('place_name'),
                place_address=page_data.get('place_address'),
                price=page_data.get('price'),
                ticket_link=page_data.get('ticket_link'),
                full_description=page_data.get('full_description'),
                gallery_images=page_data.get('gallery_images', []),
                tags=page_data.get('tags', [])
            )

            await self._save_event(event)
            return event
        except Exception as e:
            logger.error(f"Ошибка при обработке события: {str(e)}")
            return None


async def main():
    async with AsyncAfishaParser() as parser:
        events = await parser.parse_events()
        logger.info(f"Успешно обработано {len(events)} событий")


if __name__ == "__main__":
    asyncio.run(main())