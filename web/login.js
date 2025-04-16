// login.js
// Функция для шифрования пароля
function encryptPassword(password) {
    return CryptoJS.SHA256(password).toString();
}

// Функция для показа формы регистрации
function showRegisterForm() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = 'block';
}

// Функция для показа формы авторизации
function showLoginForm() {
    document.getElementById('registerForm').style.display = 'none';
    document.getElementById('loginForm').style.display = 'block';
}

// Остальные функции (register, login и т.д.) остаются без изменений

// Функция для регистрации нового пользователя
async function register() {
    const username = document.getElementById('registerUsername').value;
    const password = document.getElementById('registerPassword').value;

    if (!username || !password) {
        alert('Заполните все поля');
        return;
    }

    // Шифруем пароль
    const encryptedPassword = encryptPassword(password);
    console.log("Зашифрованный пароль:", encryptedPassword);

    // Добавляем нового пользователя
    try {
        const isAdded = await eel.add_user(username, encryptedPassword)();
        console.log("Результат add_user:", isAdded);  // Логируем результат
        if (isAdded) {
            alert('Регистрация прошла успешно');
            showLoginForm();
        } else {
            alert('Ошибка: Пользователь с таким логином уже существует или произошла ошибка при сохранении.');
        }
    } catch (error) {
        console.error("Ошибка при вызове add_user:", error);
        alert('Произошла ошибка при регистрации. Проверьте консоль для подробностей.');
    }
}

// Функция для авторизации пользователя
async function login() {
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;

    if (!username || !password) {
        alert('Заполните все поля');
        return;
    }

    // Шифруем пароль
    const encryptedPassword = encryptPassword(password);

    // Проверяем, существует ли пользователь
    try {
        const isValid = await eel.check_user(username, encryptedPassword)();
        if (isValid) {
            alert('Авторизация прошла успешно');
            window.location.href = 'index.html'; // Переход на index.html
        } else {
            alert('Ошибка: Неверный логин или пароль.');
        }
    } catch (error) {
        console.error("Ошибка при вызове check_user:", error);
        alert('Произошла ошибка при авторизации.');
    }
}

// Проверка соединения с Python при загрузке страницы
window.onload = async function () {
    try {
        const response = await eel.test_connection()();
        console.log(response);  // Должно вывести "Соединение с Python установлено!"
    } catch (error) {
        console.error("Ошибка при подключении к Python:", error);
    }
};