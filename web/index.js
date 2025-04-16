let events = [];
let isFavoritesView = false; // Флаг для отслеживания режима избранного

// Функция для проверки, находится ли спектакль в избранном
async function isEventInFavourites(eventPath) {
    return await eel.check_if_favourite(eventPath)();
}

function parseCustomDate(dateString) {
    const [datePart, timePart] = dateString.split(' ');
    const [day, month, year] = datePart.split('.');
    return `${year}-${month}-${day}T${timePart}`;
}

// Функция для применения фильтров
async function applyFilters() {
    const theater = document.getElementById('theater').value;
    const priceMin = document.getElementById('price-min').value;
    const priceMax = document.getElementById('price-max').value;
    const sort = document.getElementById('sort').value;

    let filteredEvents = events.filter(event => {
        return (theater === 'all' || event.place_name === theater) &&
               (!priceMin || parsePrice(event.price)[1] >= parseFloat(priceMin)) &&
               (!priceMax || parsePrice(event.price)[1] <= parseFloat(priceMax));
    });

    // Если включен режим избранного, загружаем избранные события
    if (isFavoritesView) {
        const favourites = await eel.load_favourites()();
        displayEvents(favourites);
        return;
    }

    // Сортировка
    if (sort === 'date_asc') {
        filteredEvents.sort((a, b) => new Date(parseCustomDate(a.date)) - new Date(parseCustomDate(b.date)));
    } else if (sort === 'date_desc') {
        filteredEvents.sort((a, b) => new Date(parseCustomDate(b.date)) - new Date(parseCustomDate(a.date)));
    } else if (sort === 'price_asc') {
        filteredEvents.sort((a, b) => parsePrice(a.price)[1] - parsePrice(b.price)[1]);
    } else if (sort === 'price_desc') {
        filteredEvents.sort((a, b) => parsePrice(b.price)[1] - parsePrice(a.price)[1]);
    } else if (sort === 'age_asc') {
        filteredEvents.sort((a, b) => parseInt(a.age_limit) - parseInt(b.age_limit));
    } else if (sort === 'age_desc') {
        filteredEvents.sort((a, b) => parseInt(b.age_limit) - parseInt(a.age_limit));
    }

    // Отображаем события с учетом избранного
    const eventsWithFavourites = await Promise.all(filteredEvents.map(async event => {
        const isFavourite = await isEventInFavourites(event.path);
        return { ...event, isFavourite };
    }));

    displayEvents(eventsWithFavourites);
}

// Функция для отображения событий
async function displayEvents(events) {
    const eventsContainer = document.getElementById('events');
    const favouritesHintContainer = document.getElementById('favourites-hint');

    // Очищаем контейнеры
    eventsContainer.innerHTML = '';
    favouritesHintContainer.innerHTML = '';

    // Добавляем подсказку для выхода из избранного
    if (isFavoritesView) {
        const hint = document.createElement('p');
        hint.textContent = 'Нажмите на ❤️ еще раз, чтобы выйти из избранного.';
        favouritesHintContainer.appendChild(hint);
    }

    // Отображаем события
    for (const event of events) {
        const isFavourite = await eel.check_if_favourite(event.path)();
        const eventElement = document.createElement('div');
        eventElement.className = 'event';
        eventElement.innerHTML = `
            <div class="event-header">
                <h2>${event.title}</h2>
                <i class="fas fa-heart ${isFavourite ? 'favorite' : ''}" 
                   onclick="toggleFavorite('${event.path}', event)"></i>
            </div>
            <img src="${event.main_image}" alt="${event.title}">
            <p>${event.date}</p>
            <p>${event.place_name}</p>
            <p>Цена: ${event.price}</p>
            <p>Возрастной рейтинг: ${event.age_limit}</p>
            <a href="#" onclick="loadEventPage('${event.id}', '${event.path}')">Подробнее</a>
        `;
        eventsContainer.appendChild(eventElement);
    }
}

// Функция для добавления/удаления из избранного
async function toggleFavorite(eventPath, event) {
    event.preventDefault(); // Предотвращаем обновление страницы

    // Проверяем, находится ли спектакль в избранном
    const isFavourite = await eel.check_if_favourite(eventPath)();

    if (isFavourite) {
        // Удаляем из избранного
        await eel.remove_from_favourites(eventPath)();
    } else {
        // Добавляем в избранное
        await eel.add_to_favourites(eventPath)();
    }

    // Обновляем отображение событий
    applyFilters();
}

// Функция для переключения между всеми событиями и избранными
function toggleFavoritesView() {
    isFavoritesView = !isFavoritesView;
    applyFilters(); // Применяем фильтры с учетом текущего режима
}

// Функция для загрузки страницы события
function loadEventPage(eventId, eventPath) {
    window.location.href = `event.html?id=${eventId}&path=${encodeURIComponent(eventPath)}`;
}

// Функция для преобразования цены в число
function parsePrice(price) {
    const prices = price.split('-').map(p => parseFloat(p.trim()));
    return [prices[0], prices[1] || prices[0]];
}

// Загрузка данных при старте
eel.load_events()(function(data) {
    events = data;
    applyFilters(); // Отображаем события с учетом фильтров

    // Заполнение выпадающего списка театров
    const theaterSelect = document.getElementById('theater');
    const theaters = [...new Set(data.map(event => event.place_name))];
    theaters.forEach(theater => {
        const option = document.createElement('option');
        option.value = theater;
        option.textContent = theater;
        theaterSelect.appendChild(option);
    });
});

