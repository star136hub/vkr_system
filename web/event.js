// Функция для получения параметра из URL
function getParameterByName(name, url = window.location.href) {
    name = name.replace(/[\[\]]/g, '\\$&');
    const regex = new RegExp('[?&]' + name + '(=([^&#]*)|&|#|$)');
    const results = regex.exec(url);
    if (!results) return null;
    if (!results[2]) return '';
    return decodeURIComponent(results[2].replace(/\+/g, ' '));
}

// Загрузка данных события по пути
const eventPath = getParameterByName('path');

if (eventPath) {
    eel.load_event(eventPath)(function(data) {
        if (data) {
            displayEventData(data);
        } else {
            console.error('Событие не найдено.');
        }
    });
} else {
    console.error('Путь к событию не указан.');
}

// Функция для отображения данных на странице
function displayEventData(data) {
    // Первый блок: Основная информация
    document.getElementById('event-title').textContent = data.title;
    document.getElementById('event-date').textContent = data.date;
    document.getElementById('event-place').textContent = data.place_name;
    document.getElementById('event-price').textContent = data.price;
    document.getElementById('event-short-description').textContent = data.short_description;

    // Обработчик для кнопки "Выбрать места"
    const ticketLink = document.getElementById('event-ticket-link');
    if (data.ticket_link) {
        ticketLink.href = `place.html?ticket_link=${encodeURIComponent(data.ticket_link)}`;
    } else {
        ticketLink.style.display = 'none'; // Скрываем кнопку, если ссылки нет
    }

    // Основное изображение
    if (data.main_image) {
        document.getElementById('event-image').src = data.main_image;
    }

    // Второй блок: Полное описание
    if (data.full_description) {
        document.getElementById('event-full-description').textContent = data.full_description;
    } else {
        document.getElementById('full-description-container').style.display = 'none';
    }

    // Третий блок: Галерея изображений
    if (data.gallery_images && data.gallery_images.length > 0) {
        const galleryImages = document.getElementById('gallery-images');
        data.gallery_images.forEach(image => {
            const img = document.createElement('img');
            img.src = image;
            img.alt = "Галерея мероприятия";
            img.classList.add('gallery-image');
            galleryImages.appendChild(img);
        });

        // Обработчик для открытия модального окна
        const modal = document.getElementById('modal');
        const modalImg = document.getElementById('modal-image');
        const closeModal = document.getElementsByClassName('close')[0];

        document.querySelectorAll('.gallery-image').forEach(img => {
            img.addEventListener('click', () => {
                modal.style.display = 'block';
                modalImg.src = img.src;
            });
        });

        closeModal.onclick = () => {
            modal.style.display = 'none';
        };

        window.onclick = (event) => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        };
    } else {
        document.getElementById('gallery-container').style.display = 'none';
    }

    // Четвертый блок: Дополнительная информация
    const additionalInfoContent = document.getElementById('additional-info-content');
    if (data.additional_info) {
        // Разделяем текст на строки и выводим каждую строку как отдельный абзац
        const lines = data.additional_info.split('\n');
        lines.forEach(line => {
            if (line.trim()) { // Проверяем, что строка не пустая
                const p = document.createElement('p');

                // Если строка содержит двоеточие, выделяем текст до двоеточия жирным
                const colonIndex = line.indexOf(':');
                if (colonIndex !== -1) {
                    const key = line.substring(0, colonIndex + 1); // Текст до двоеточия (включая двоеточие)
                    const value = line.substring(colonIndex + 1).trim(); // Текст после двоеточия
                    p.innerHTML = `<strong>${key}</strong> ${value}`;
                } else {
                    p.textContent = line.trim(); // Если двоеточия нет, выводим строку как есть
                }

                additionalInfoContent.appendChild(p);
            }
        });
    } else {
        document.getElementById('additional-info-container').style.display = 'none';
    }
}