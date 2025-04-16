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


class AsyncCultureParser(BaseParser):
    """Асинхронный парсер событий с сайта Culture.ru"""

    BASE_URL = 'https://www.culture.ru'
    THEATER_URL = f'{BASE_URL}/afisha/tulskaya-oblast-tula/instituteType-theater'
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    CONCURRENCY_LIMIT = 10  # Ограничение одновременных запросов

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

    async def _make_request(self, url: str) -> Optional[BeautifulSoup]:
        """Выполняет асинхронный HTTP-запрос и возвращает BeautifulSoup объект"""
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
            title_tag = card.find('div', class_='p1Gbz')
            link_tag = card.find('a')

            event_url = urljoin(self.BASE_URL, link_tag['href']) if link_tag else None
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

            # Основные данные
            info_block = soup.find('div', class_='Jds71')
            desc_block = soup.find('div', class_='xZmPc')
            ticket_button = soup.find('button', class_='_7V9xp')
            tags_container = soup.find('div', class_='ciUqX')

            # Изображение
            image_tag = soup.find('img', class_='KRQ9s')
            image_url = None
            if image_tag and 'src' in image_tag.attrs:
                src = image_tag['src']
                if src.startswith('/_next/image?'):
                    # Извлекаем URL из параметра url
                    from urllib.parse import parse_qs, urlparse
                    parsed = urlparse(src)
                    params = parse_qs(parsed.query)
                    image_url = params.get('url', [None])[0]
                else:
                    image_url = src

            # Место проведения и адрес
            place_name = soup.find('div', class_='Heq3A')
            place_address = soup.find('div', class_='C3QPv')

            # Обработка информации
            age_limit, event_date, price = self._parse_info_block(info_block)

            return {
                'age_limit': age_limit,
                'date': event_date,
                'price': price if price else 'Бесплатно' if 'Бесплатно' in str(info_block) else None,
                'ticket_link': event_url if ticket_button else None,
                'full_description': desc_block.get_text(separator=' ', strip=True) if desc_block else None,
                'tags': [tag.text.strip() for tag in
                         tags_container.find_all('a', class_='Bgm4p')] if tags_container else [],
                'image': image_url,
                'place_name': place_name,
                'place_address': place_address
            }
        except Exception as e:
            logger.error(f"Ошибка при парсинге страницы события {event_url}: {str(e)}")
            return None

    @staticmethod
    def _parse_info_block(info_block: Optional[BeautifulSoup]) -> tuple:
        """Парсит информационный блок события с учётом разных вариантов структуры"""
        age_limit = None
        event_date = None
        price = None

        if not info_block:
            return age_limit, event_date, price

        info_items = info_block.find_all('div', class_='_19IwE')
        if not info_items:
            return age_limit, event_date, price

        # Сначала пробуем найти возрастное ограничение и цену по характерным признакам
        for item in info_items:
            text = item.get_text(strip=True)

            # Пропускаем элементы с иконками (как доступная среда)
            if item.find('svg'):
                continue

            if '+' in text:  # Возрастное ограничение
                age_limit = text
            elif 'руб' in text or '₽' in text or 'Бесплатно' in text:  # Цена
                price = text.replace('от', '').strip()
                if 'Бесплатно' in price:
                    price = 'Бесплатно'
            elif 'С ' in text or ' по ' in text or any(char.isdigit() for char in text):  # Дата
                # Обработка формата "С [дата] по [дата]"
                if text.startswith('С ') and ' по ' in text:
                    try:
                        _, date_part = text.split('С ', 1)
                        start_date, end_date = date_part.split(' по ', 1)
                        event_date = f"{start_date.strip()} - {end_date.strip()}"
                    except ValueError:
                        event_date = text
                else:
                    event_date = text

        # Если не нашли дату в цикле, но есть элементы, пробуем взять первый подходящий
        if not event_date and info_items:
            first_item = info_items[0]
            if not first_item.find('svg'):  # Пропускаем если это иконка
                first_text = first_item.get_text(strip=True)
                if not ('+' in first_text or 'руб' in first_text or '₽' in first_text or 'Бесплатно' in first_text):
                    event_date = first_text

        return age_limit, event_date, price

    async def _save_event(self, event: EventData) -> bool:
        """Асинхронно сохраняет данные о событии в JSON файл"""
        try:
            if not event.title:
                return False

            safe_title = self._sanitize_filename(event.title)
            folder_path = os.path.join('../spectacles', 'culture', safe_title)
            os.makedirs(folder_path, exist_ok=True)

            json_path = os.path.join(folder_path, 'event_details.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(event.__dict__, f, ensure_ascii=False, indent=4)

            logger.info(f"Сохранено событие: {event.title}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении события {event.title}: {str(e)}")
            return False

    async def _process_single_event(self, card_data: Dict) -> Optional[EventData]:
        """Асинхронно обрабатывает одно событие"""
        try:
            # Получаем данные со страницы события
            page_data = await self._parse_event_page(card_data['event_url'])
            if not page_data:
                return None

            # Создаем объект события
            event = EventData(
                title=card_data['title'],
                age_limit=page_data['age_limit'],
                image=page_data['image'],
                date=page_data['date'],
                place_name=page_data['place_name'],
                place_address=page_data['place_address'],
                price=page_data['price'],
                ticket_link=page_data['ticket_link'],
                full_description=page_data['full_description'],
                tags=page_data['tags']
            )

            # Немедленно сохраняем событие
            await self._save_event(event)
            return event
        except Exception as e:
            logger.error(f"Ошибка при обработке события: {str(e)}")
            return None

    async def parse_page_events(self, page: int) -> List[EventData]:
        """Парсит события с одной страницы"""
        url = f'{self.THEATER_URL}?page={page}'
        soup = await self._make_request(url)
        if not soup:
            return []

        # Проверка на последнюю страницу
        no_events = soup.find('div', class_='Lhfwa')
        if no_events and "К сожалению, событий по вашему запросу не найдено" in no_events.text:
            return []

        event_cards = soup.find_all('div', class_='CHPy6')
        if not event_cards:
            return []

        # Создаем задачи для обработки карточек событий
        tasks = []
        for card in event_cards:
            card_data = await self._parse_event_card(card)
            if card_data and card_data.get('event_url'):
                tasks.append(self._process_single_event(card_data))

        # Ожидаем завершения всех задач
        results = await asyncio.gather(*tasks)
        return [event for event in results if event]

    async def parse_events(self) -> List[EventData]:
        """Основной асинхронный метод парсинга событий"""
        logger.info("Начало парсинга событий")
        page = 1
        total_processed = 0
        all_events = []

        async with self:
            while True:
                events = await self.parse_page_events(page)
                if not events:
                    break

                all_events.extend(events)
                total_processed += len(events)
                logger.info(f"Обработано страниц: {page}, событий: {total_processed}")
                page += 1

        logger.info(f"Парсинг завершен. Успешно обработано {total_processed} событий")
        return all_events


async def main():
    parser = AsyncCultureParser()
    await parser.parse_events()


if __name__ == "__main__":
    asyncio.run(main())