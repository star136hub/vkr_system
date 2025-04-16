// Функция для получения параметра из URL
function getParameterByName(name, url = window.location.href) {
    name = name.replace(/[\[\]]/g, '\\$&');
    const regex = new RegExp('[?&]' + name + '(=([^&#]*)|&|#|$)');
    const results = regex.exec(url);
    if (!results) return null;
    if (!results[2]) return '';
    return decodeURIComponent(results[2].replace(/\+/g, ' '));
}

// Загрузка iframe с билетами и настройка кнопки "Назад"
window.onload = function () {
    const ticketLink = getParameterByName('ticket_link');
    const iframe = document.getElementById('ticket-iframe');
    const backButton = document.getElementById('back-button');

    // Загрузка iframe
    if (ticketLink) {
        iframe.src = ticketLink;
    } else {
        console.error('Ссылка на билеты не указана.');
        iframe.style.display = 'none'; // Скрываем iframe, если ссылки нет
    }

    // Настройка кнопки "Назад"
    const eventData = JSON.parse(localStorage.getItem('currentEvent'));
    if (eventData && eventData.path) {
        backButton.href = `event.html?path=${encodeURIComponent(eventData.path)}`;
    } else {
        console.warn('Данные о событии не найдены. Кнопка "Назад" ведет на event.html без параметров.');
        backButton.href = 'event.html';
    }
};