import telebot
from telebot import types
import mysql.connector


token = ''
bot = telebot.TeleBot(token)


def create_connection():
    try:
        conn = mysql.connector.connect(host='', user='', password='', database='')
        return conn
    except Exception as e:
        print(e)


def add_user(message):
    try:
        conn = create_connection()
        c = conn.cursor()
        c.execute('INSERT IGNORE INTO users (id, tg_name) VALUES (%s, %s)',
                  (message.from_user.id, '@' + message.from_user.username))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Произошла ошибка в функции add_user: {e}")


def name(message):
    try:
        conn = create_connection()
        c = conn.cursor()
        c.execute(f"UPDATE users SET name = %s WHERE id = %s",
                  (message.text, message.chat.id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Произошла ошибка в функции name: {e}")


def user_off(user_id):
    try:
        conn = create_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM tasks WHERE user_id = %s", (user_id,))
        ids = c.fetchall()
        if ids:
            question_ids_tuple = tuple(id_[0] for id_ in ids)
            c.execute("DELETE FROM reminders WHERE task_id IN %s", question_ids_tuple)
        c.execute("DELETE FROM tasks WHERE user_id = %s", (user_id,))
        c.execute(f"delete from users WHERE id = %s", (user_id,))
        conn.commit()
        conn.close()
        print(f'Пользователь {user_id} удален из базы данных')
    except telebot.apihelper.ApiTelegramException as e:
        print(f"Произошла ошибка в функции user_off: {e}")


def info(col_info, col, val, table):
    try:
        conn = create_connection()
        c = conn.cursor()
        c.execute(f"SELECT {col_info} FROM {table} where {col} = %s", (val,))
        result = c.fetchone()
        conn.close()
        if result is not None:
            return result[0]
        else:
            return None
    except Exception as e:
        print(f"Произошла ошибка в функции info: {e}")


def main_menu(user_id):
    try:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        create_task_btn = types.KeyboardButton(text="Создать задачу")
        ask = types.KeyboardButton(text="Задать вопрос")
        my_tasks_btn = types.KeyboardButton(text="Задачи")
        keyboard.add(create_task_btn, my_tasks_btn, ask)
        bot.send_message(user_id, 'Меню:', reply_markup=keyboard)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code in [403]:
            user_off(user_id)
        else:
            print(f"Произошла ошибка в функции main_menu: {e}")


def tasks(user_id):
    try:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        today = types.KeyboardButton(text="Сегодня")
        tomorrow = types.KeyboardButton(text="Завтра")
        week = types.KeyboardButton(text="Неделю")
        all_tasks = types.KeyboardButton(text="Все")
        back = types.KeyboardButton(text="Назад")
        keyboard.add(today, tomorrow, week)
        keyboard.add(all_tasks, back)
        bot.send_message(user_id, "Ваши задачи на...", reply_markup=keyboard)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code in [403]:
            user_off(user_id)
        else:
            print(f"Произошла ошибка в функции tasks: {e}")


def get_weekday(date):
    try:
        weekdays = ['Понедельник', 'Вторник', 'Среду', 'Четверг', 'Пятницу', 'Субботу', 'Воскресенье']
        today_weekday = date.weekday()
        return weekdays[today_weekday]
    except Exception as e:
        print('Ошибка в функции get_weekday:', e)


def chat_off(chat_id):
    try:
        conn = create_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM tasks WHERE chat_id = %s", (chat_id,))
        ids = c.fetchall()
        if ids:
            question_ids_tuple = tuple(id_[0] for id_ in ids)
            c.execute("DELETE FROM reminders WHERE task_id IN %s", question_ids_tuple)
        c.execute("DELETE FROM tasks WHERE chat_id = %s", (chat_id,))
        c.execute(f"delete from chats WHERE id = %s", (chat_id,))
        conn.commit()
        conn.close()
        print(f'Чат {chat_id} удален из базы данных')
    except telebot.apihelper.ApiTelegramException as e:
        print(f"Произошла ошибка в функции chat_off: {e}")


def add_chat(message):
    try:
        conn = create_connection()
        c = conn.cursor()
        c.execute('INSERT IGNORE INTO chats (id, title) VALUES (%s, %s)',
                  (message.chat.id, message.chat.title))
        c.execute('INSERT IGNORE INTO users_chats (user_id, chat_id) VALUES (%s, %s)',
                  (message.from_user.id, message.chat.id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Произошла ошибка в функции add_chat: {e}")
