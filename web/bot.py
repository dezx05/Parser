from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import sqlite3
import logging
from main import get_vacancies, experience_dict, employment_dict, schedule_dict
from aiogram.utils.exceptions import Unauthorized

# Ваш токен должен быть скрыт
TOKEN = '7255706311:AAEmLmaUnSW0XMdqMGWuHx0FnOJFVfcGF-o'
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=storage)

class Form(StatesGroup):
    search_word = State()  # Слово для поиска
    employment = State()  # Тип занятости
    experience = State()  # Опыт работы
    schedule = State()  # График работы

# Создание таблицы для нового пользователя
def create_user_table(username):
    conn = sqlite3.connect('vacancies.db')
    cursor = conn.cursor()
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS "{username}" (
            id TEXT PRIMARY KEY,
            name TEXT,
            url TEXT,
            requirement TEXT,
            schedule TEXT,
            experience TEXT,
            employment TEXT,
            responsibility TEXT,
            employer TEXT,
            salary TEXT,
            search_word TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Добавление вакансии в таблицу пользователя
def add_vacancy_to_db(username, vacancy_data, search_word):
    conn = sqlite3.connect('vacancies.db')
    cursor = conn.cursor()
    # Преобразование всех параметров в строки
    values = (
        str(vacancy_data['id']),
        str(vacancy_data['name']),
        str(vacancy_data['alternate_url']),
        str(vacancy_data.get("snippet", {}).get('requirement', 'Не указано')).replace("<highlighttext>", "").replace("</highlighttext>", ""),
        str(vacancy_data['schedule']['name']),
        str(vacancy_data['experience']['name']),
        str(vacancy_data['employment']['name']),
        str(vacancy_data.get("snippet", {}).get('responsibility', 'Не указано')).replace("<highlighttext>", "").replace("</highlighttext>", ""),
        str(vacancy_data['employer']['name'] if vacancy_data['employer'] else 'Не указано'),
        f"{str(vacancy_data['salary'].get('from', 'Не указано'))} - {str(vacancy_data['salary'].get('to', 'Не указано'))} {str(vacancy_data['salary'].get('currency', ''))}" if vacancy_data['salary'] else 'Не указано',
        str(search_word)
    )
    cursor.execute(f'''
        INSERT INTO "{username}" (
            id, name, url, requirement, schedule, experience, employment,
            responsibility, employer, salary, search_word
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', values)
    conn.commit()
    conn.close()

# Функция для вывода вакансий из базы данных
def show_vacancies_from_db(username, limit=5):
    conn = sqlite3.connect('vacancies.db')
    cursor = conn.cursor()
    cursor.execute(f'SELECT * FROM "{username}" LIMIT ?', (limit,))
    vacancies = cursor.fetchall()
    conn.close()
    return vacancies

# Функция для создания клавиатуры поиска
def get_search_keyboard(buttons_dict):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for button_text in buttons_dict.keys():
        keyboard.add(button_text)
    return keyboard

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Я бот для поиска вакансий. Напиши /search, чтобы начать поиск.")

# Обработчик команды /search
@dp.message_handler(commands=['search'])
async def search_vacancies(message: types.Message):
    await Form.search_word.set()
    await message.reply("Введите слово для поиска вакансий:", reply_markup=types.ReplyKeyboardRemove())

# Обработчик для ввода слова поиска
@dp.message_handler(state=Form.search_word)
async def input_search_word(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['search_word'] = message.text
    await Form.next()
    await message.reply("Выберите тип занятости:", reply_markup=get_search_keyboard(employment_dict))

# Обработчик для выбора типа занятости
@dp.message_handler(lambda message: message.text in employment_dict, state=Form.employment)
async def input_employment(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['employment'] = message.text
    await Form.next()
    await message.reply("Выберите опыт работы:", reply_markup=get_search_keyboard(experience_dict))

# Обработчик для выбора опыта работы
@dp.message_handler(lambda message: message.text in experience_dict, state=Form.experience)
async def input_experience(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['experience'] = message.text
    await Form.next()
    await message.reply("Выберите график работы:", reply_markup=get_search_keyboard(schedule_dict))

# Обработчик для выбора графика работы
@dp.message_handler(lambda message: message.text in schedule_dict, state=Form.schedule)
async def input_schedule(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['schedule'] = message.text
    user_data = await state.get_data()
    username = message.from_user.username
    create_user_table(username)  # Создание таблицы пользователя, если она еще не существует
    vacancies = get_vacancies(
        user_data['search_word'],
        user_data['employment'],
        user_data['experience'],
        user_data['schedule']
    )
    # Сохранение вакансий в базу данных без их вывода пользователю
    if vacancies:
        for vacancy in vacancies:
            add_vacancy_to_db(username, vacancy, user_data['search_word'])
        await message.reply("Вакансии успешно сохранены в базе данных.")
    else:
        await message.reply("По вашему запросу вакансий не найдено. Поробуйте еще раз /search")
    await state.finish()

# Обработчик команды /show_vacancies
@dp.message_handler(commands=['show_vacancies'])
async def show_vacancies(message: types.Message):
    username = message.from_user.username
    vacancies = show_vacancies_from_db(username, limit=3)  # Устанавливаем лимит на вывод вакансий
    try:
        for vacancy in vacancies:
            # Использование Markdown для форматирования сообщения
            vacancy_message = (
                f"[Ссылка]{vacancy[2]}\n"
                f"*Название:* {vacancy[1]}\n"
                f"*Компания:* {vacancy[8]}\n"
                f"*Зарплата:* {vacancy[9]}\n"
                f"*График:* {vacancy[4]}\n"
                f"*Опыт:* {vacancy[5]}\n"
                f"*Тип занятости:* {vacancy[6]}"
            )
            await message.answer(vacancy_message, parse_mode='Markdown')
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")


# Обработчик команды /clear_all
@dp.message_handler(commands=['clear_all'])
async def clear_all_data(message: types.Message):
    try:
        if message.from_user.id == 773361425:  # ID пользователя @dezx0937
            conn = sqlite3.connect('vacancies.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            for table in tables:
                # Очистка всех значений в таблице, не удаляя саму таблицу
                cursor.execute(f'DELETE FROM {table[0]}')
            conn.commit()
            conn.close()
            await message.reply("Все значения в таблицах были успешно очищены.")
        else:
            await message.reply("У вас нет доступа к этой команде.")
    except Unauthorized:
        await message.reply("Ошибка авторизации. Пожалуйста, попробуйте снова.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)