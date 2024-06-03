from task_user import *
import schedule
import time
import threading
import telebot
from telebot import types
import requests
import re


token = ''
bot = telebot.TeleBot(token)
user_condition = {}
FOLDER_ID = ""
MODEL_URI = ""
IAM_TOKEN = ""
chatting = False


@bot.message_handler(commands=['start'])
def start(message):
    add_user(message)
    if message.chat.type == 'private':
        bot.send_message(message.chat.id, "Здравствуйте, я - Ваш личный ассистент <b>Планик</b>. "
                                          "<i>Как я могу к Вам обращаться?</i>\n\nПродолжая работу со мной, "
                                          "Вы <b>соглашаетесь</b> на хранение Ваших персональных данных, а именно: "
                                          "<b>Ваши уникальные id, имя пользователя и имя, которое укажете ниже</b>",
                         parse_mode="HTML")
        user_condition[message.chat.id] = 'waiting_name'
    elif message.chat.type == 'supergroup':
        bot.send_message(message.chat.id, "Здравствуйте, я - Ваш ассистент <b>Планик</b>. "
                                          "\n\nПродолжая работу со мной, "
                                          "Вы <b>соглашаетесь</b> на хранение Ваших персональных данных, а именно: "
                                          "<b>уникальные id, имена пользователей</b>",
                         parse_mode="HTML")
        add_chat(message)


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        add_user(call.message)
        if call.message.chat.type == 'supergroup':
            add_chat(call.message)
        if call.data[:3] == 'do_':
            do_task(call.message.chat.id, call.data[3:])
        elif call.data[:5] == 'note_':
            set_up_notifications(call.message.chat.id, call.data[5:])
        elif call.data[:9] == 'add_note_':
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            a = types.KeyboardButton(text="единовременно")
            b = types.KeyboardButton(text="ежедневно")
            c = types.KeyboardButton(text="еженедельно")
            d = types.KeyboardButton(text="ежемесячно")
            e = types.KeyboardButton(text="ежегодно")
            f = types.KeyboardButton(text="Назад")
            keyboard.add(a, c)
            keyboard.add(b, d, e, f)
            user_condition[call.message.chat.id] = call.data[9:]
            bot.send_message(call.message.chat.id, 'Как часто Вы хотите получать уведомления?', reply_markup=keyboard)
        elif call.data[:4] == 'del_':
            del_note(call.message.chat.id, call.data[4:])
        elif call.data == 'no_ask':
            user_condition[call.message.chat.id] = ''
            main_menu(call.message.chat.id)
    except Exception as e:
        print(f"Произошла ошибка при обработке сообщения: {e}")
        bot.send_message(call.message.chat.id, "Повторите запрос позже")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        add_user(message)
        if message.chat.type == 'supergroup':
            add_chat(message)
        if user_condition.get(message.chat.id) is not None and user_condition.get(message.chat.id) == "waiting_name":
            name(message)
            bot.send_message(message.chat.id, f'<i>Приятно познакомится, {message.text}!</i>', parse_mode='HTML')
            user_condition[message.chat.id] = ''
            main_menu(message.chat.id)
        elif len(message.text) > 8 and message.text[:8] == 'Задача #':
            task(message.chat.id, message.text[8:])
            user_condition[message.chat.id] = 'main'
        elif len(message.text) > 14 and message.text[:14] == 'Для участника ':
            add_user_for_task(user_condition.get(message.chat.id), message.chat.id, message.text[14:])
        elif message.text == 'Создать задачу':
            bot.send_message(message.chat.id, "Напишите задачу")
            user_condition[message.chat.id] = 'task'
        elif message.text.lower() == 'меню':
            main_menu(message.chat.id)
        elif message.text == 'Задать вопрос':
            user_condition[message.chat.id] = 'ask'
            bot.send_message(message.chat.id, 'Конечно, я могу помочь вам с вопросом. О чём бы вы хотели спросить?')
        elif user_condition.get(message.chat.id) is not None and user_condition.get(message.chat.id) == "ask":
            global IAM_TOKEN
            if not message.text:
                return
            request_data = {
                    "modelUri": MODEL_URI,
                    "completionOptions": {
                        "stream": False,
                        "temperature": 0.9,
                        "maxTokens": "2000"
                    },
                    "messages": [
                        {
                            "role": "user",
                            "text": message.text
                        }
                    ]
                }
            url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
            headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {IAM_TOKEN}",
                    "x-folder-id": FOLDER_ID
                }
            response = requests.post(url, headers=headers, json=request_data)
            keyboard = types.InlineKeyboardMarkup()
            no_ask = types.InlineKeyboardButton(text="Вернуться к меню", callback_data=f"no_ask")
            keyboard.add(no_ask)
            try:
                response_data = response.json()["result"]["alternatives"][0]["message"]["text"]
                res = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', response_data)
                res = re.sub(r'_(.*?)_', r'<i>\1</i>', res)
                res = re.sub(r'~(.*?)~', r'<u>\1</u>', res)
                res = re.sub(r'-(.*?)-', r'<s>\1</s>', res)
                res = re.sub(r'`(.*?)`', r'<code>\1</code>', res)
                bot.reply_to(message, res, reply_markup=keyboard, parse_mode="HTML")
            except KeyError:
                bot.reply_to(message, "Извините, не удалось узнать ответ", reply_markup=keyboard)
        elif message.text == 'Задачи':
            tasks(message.chat.id)
            user_condition[message.chat.id] = 'main'
        elif message.text == 'Сегодня' or message.text == 'Завтра' or message.text == 'Неделю' or message.text == 'Все':
            if message.text == 'Сегодня':
                tasks_day(message.chat.id, 'today')
            elif message.text == 'Завтра':
                tasks_day(message.chat.id, 'tomorrow')
            elif message.text == 'Неделю':
                tasks_day(message.chat.id, 'week')
            elif message.text == 'Все':
                tasks_day(message.chat.id, 'all')
            user_condition[message.chat.id] = 'tasks'
        elif message.text == 'Назад':
            if user_condition.get(message.chat.id) is not None and user_condition.get(message.chat.id) == "tasks":
                tasks(message.chat.id)
            else:
                main_menu(message.chat.id)
        elif user_condition.get(message.chat.id) is not None and user_condition.get(message.chat.id) == "task":
            if message.chat.type == 'private':
                user_condition[message.chat.id] = f'date_{create_task(message.text, 'user_id', message.chat.id)}'
            else:
                user_condition[message.chat.id] = f'date_{create_task(message.text, 'chat_id', message.chat.id)}'
        elif user_condition.get(message.chat.id) is not None and user_condition.get(message.chat.id)[:5] == "date_":
            if message.chat.type == 'supergroup':
                add_date_time(message.chat.id, user_condition.get(message.chat.id)[5:], message.text, 'chat')
            else:
                add_date_time(message.chat.id, user_condition.get(message.chat.id)[5:], message.text)
            user_condition[message.chat.id] = f'{user_condition.get(message.chat.id)[5:]}'
        elif (message.text == 'единовременно' or message.text == 'ежедневно' or message.text == 'еженедельно' or
              message.text == 'ежемесячно' or message.text == 'ежегодно'):
            user_condition[message.chat.id] += f'_{message.text}_'
            if message.text == 'единовременно':
                bot.send_message(message.chat.id, 'Напишите дату для напоминания в формате <b>дд.мм.гггг</b>, '
                                                  'например, <b>26.05.2024</b>', parse_mode="HTML")
            else:
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                for i in ['00', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', 11, 12, 13, 14, 15, 16,
                          17, 18, 19, 20, 21, 22, 23, 'Назад']:
                    h = types.KeyboardButton(text=i)
                    keyboard.add(h)
                user_condition[message.chat.id] += f'{datetime.now().strftime('%d.%m.%Y')}_d'
                bot.send_message(message.chat.id, 'Выберите час, в который хотите получать напоминание',
                                 reply_markup=keyboard)
        elif (user_condition.get(message.chat.id) is not None and '_' in user_condition.get(message.chat.id) and
              user_condition.get(message.chat.id).split("_")[1] == "единовременно"):
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for i in ['00', '01', '02', '03', '04', '05', '06', '07', '08', '09', 10, 11, 12, 13, 14, 15, 16,
                      17, 18, 19, 20, 21, 22, 23, 'Назад']:
                h = types.KeyboardButton(text=i)
                keyboard.add(h)
            user_condition[message.chat.id] += f'{datetime.now().strftime('%d.%m.%Y')}_d'
            bot.send_message(message.chat.id, 'Выберите час, в который хотите получать напоминание',
                             reply_markup=keyboard)
        elif message.text == 'Для всех':
            add_user_for_task(user_condition.get(message.chat.id), message.chat.id)
        elif user_condition.get(message.chat.id) is not None and user_condition.get(message.chat.id)[-1] == "d":
            user_condition[message.chat.id] = user_condition[message.chat.id][:-1] + f'{message.text}'
            add_note(message.chat.id, user_condition[message.chat.id])
    except Exception as e:
        print(f"Произошла ошибка при обработке сообщения: {e}")
        bot.send_message(message.chat.id, "Повторите запрос позже")


def run_schedule():
    global IAM_TOKEN
    try:
        schedule.every().hour.at("22:30").do(notifications_for_all)
        schedule.every().minute.at(":00").do(notifications_task)
        while True:
            try:
                data = {"yandexPassportOauthToken": "y0_AgAAAAANsZY2AATuwQAAAAEEN_VfAAA0hxzlGwVMrZrshwoLkZp04NbisQ"}
                response = requests.post("https://iam.api.cloud.yandex.net/iam/v1/tokens", json=data)
                response_data = response.json()
                IAM_TOKEN = response_data.get("iamToken")
            except Exception as e:
                print("Error updating token:", e)
            schedule.run_pending()
            time.sleep(5)
    except Exception as e:
        print(f"Произошла ошибка в run_schedule: {e}")


schedule_lock = threading.Lock()
thread = threading.Thread(target=run_schedule)
thread.start()
bot.polling()
