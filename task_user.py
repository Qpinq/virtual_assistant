from user import *
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


token = ''
bot = telebot.TeleBot(token)


def tasks_day(user_id, day):
    try:
        if user_id > 0:
            col = 'user_id'
        else:
            col = 'chat_id'
        conn = create_connection()
        c = conn.cursor()
        res = ''
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        if day == 'today' or day == 'tomorrow':
            if day == 'today':
                date = datetime.now().strftime('%d.%m.%Y')
                res = f'<b><u>Задачи на сегодня, {get_weekday(datetime.now())}, {date}:</u></b>\n\n'
            else:
                date = datetime.now() + timedelta(days=1)
                date = date.strftime('%d.%m.%Y')
                res = f'<b><u>Задачи на завтра, {get_weekday(datetime.now() + timedelta(days=1))}, {date}:</u></b>\n\n'

            c.execute(f'select id, task, date, time from tasks where {col} = %s and date = %s'
                      f' order by time', (user_id, date))
            rows = c.fetchall()
            if rows:
                for row in rows:
                    id_, task_, date, time = row
                    todo = types.KeyboardButton(text=f"Задача #{id_}")
                    keyboard.add(todo)
                    res += f'<b>Задача #{id_}</b>\n<i>{task_}</i>\n<b>Время:</b> {time}\n\n'
            else:
                res = f'<i><b>Задач на {date} нет</b></i>'
        elif day == 'all':
            res = f'<b><u>Все Ваши задачи:</u></b>\n\n'
            c.execute(f'select id, task, date, time from tasks where {col} = %s and chat_id is NULL'
                      f' order by date, time', (user_id, ))
            rows = c.fetchall()
            if rows:
                for row in rows:
                    id_, task_, date, time = row
                    todo = types.KeyboardButton(text=f"Задача #{id_}")
                    keyboard.add(todo)
                    res += f'<b>Задача #{id_}</b>\n<i>{task_}</i>\n<b>Дата и время:</b> {date} {time}\n\n'
            else:
                res = f'<i><b>У Вас задач на нет</b></i>'
        elif day == 'week':
            res = f'<b><u>Задачи на неделю:</u></b>\n\n'
            today = datetime.now()
            week = datetime.now().weekday()
            for i in range(-int(week)+7):
                date = (today + timedelta(days=i)).strftime('%d.%m.%Y')
                weekday = get_weekday(today + timedelta(days=i))
                res += f'<b>🗓На {weekday}, {date}:</b>\n'
                c.execute(f'select id, task, date, time from tasks where {col} = %s and date = %s and chat_id is NULL'
                          f' order by time', (user_id, date))
                rows = c.fetchall()
                if rows:
                    for row in rows:
                        id_, task_, date, time = row
                        todo = types.KeyboardButton(text=f"Задача #{id_}")
                        keyboard.add(todo)
                        res += f'<b>Задача #{id_}</b>\n<i>{task_}</i>\n<b>Время:</b> {time}\n\n'
                else:
                    res += '<i><b>Задач нет</b></i>\n\n'
        todo = types.KeyboardButton(text="Назад")
        keyboard.add(todo)
        bot.send_message(user_id, res, reply_markup=keyboard, parse_mode='HTML')
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code in [403]:
            if user_id > 0:
                user_off(user_id)
            else:
                chat_off(user_id)
        else:
            print(f"Произошла ошибка в функции tasks_day: {e}")


def notifications_for_all():
    try:
        hour = datetime.now().strftime("%H")
        today_date = datetime.now().strftime('%d.%m.%Y')
        conn = create_connection()
        c = conn.cursor()
        c.execute("SELECT DISTINCT t.chat_id, t.user_id FROM reminders r INNER JOIN tasks t ON t.id = r.task_id "
                  "where r.date = %s AND r.hour = %s", (today_date, hour))
        id_list = c.fetchall()
        if id_list:
            for user_id_tuple in id_list:
                chat_id, user_id = user_id_tuple
                if chat_id and user_id:
                    c.execute("SELECT t.id, t.task, f.name, t.date, t.time, r.hour, f.id, r.id, t.chat_id, u.tg_name "
                              "FROM reminders r INNER JOIN tasks t ON t.id = r.task_id "
                              "INNER JOIN frequency f ON f.id = r.frequency_id "
                              "INNER JOIN users u ON u.id = t.user_id "
                              "WHERE t.chat_id = %s AND r.hour = %s AND r.date = %s", (chat_id, hour, today_date))
                    rows = c.fetchall()
                    if rows:
                        for row in rows:
                            try:
                                t_id, t_task, f_name, t_date, t_time, r_hour, f_id, r_id, chat_id, u_name = row
                                keyboard = telebot.types.InlineKeyboardMarkup()
                                do = telebot.types.InlineKeyboardButton(text="Выполнено", callback_data=f"do_{t_id}")
                                note = telebot.types.InlineKeyboardButton(text="Настроить уведомления",
                                                                          callback_data=f"note_{t_id}")
                                keyboard.add(do, note)
                                bot.send_message(chat_id, f'<u><b>❗Внимание!</b></u>\n\nЗадача <b>#{t_id} для '
                                                          f'{u_name}\n{t_task}</b>'
                                                          f'\nНапоминание: <b>{f_name}</b>\nДата задачи: <b>{t_date} '
                                                          f'{t_time}</b>', parse_mode="HTML", reply_markup=keyboard)
                                if f_id == 1:
                                    new_date = (datetime.now() + timedelta(days=1)).strftime('%d.%m.%Y')
                                elif f_id == 2:
                                    new_date = (datetime.now() + timedelta(weeks=1)).strftime('%d.%m.%Y')
                                elif f_id == 3:
                                    new_date = (datetime.now() + relativedelta(months=1)).strftime('%d.%m.%Y')
                                elif f_id == 4:
                                    new_date = (datetime.now() + relativedelta(years=1)).strftime('%d.%m.%Y')
                                else:
                                    c.execute('DELETE FROM reminders WHERE id = %s', (r_id,))
                                    conn.commit()
                                    continue
                                c.execute('UPDATE reminders SET date = %s WHERE id = %s', (new_date, r_id))
                                conn.commit()
                            except telebot.apihelper.ApiTelegramException as e:
                                if e.error_code == 403:
                                    user_off(user_id)
                else:
                    if user_id:
                        c.execute("SELECT t.id, t.task, f.name, t.date, t.time, r.hour, f.id, r.id, t.user_id "
                                  "FROM reminders r INNER JOIN tasks t ON t.id = r.task_id INNER JOIN frequency f ON "
                                  "f.id = r.frequency_id INNER JOIN users u on u.id = t.user_id "
                                  "WHERE t.user_id = %s AND r.hour = %s AND r.date = %s", (user_id, hour, today_date))
                    else:
                        c.execute("SELECT t.id, t.task, f.name, t.date, t.time, r.hour, f.id, r.id, t.chat_id "
                                  "FROM reminders r INNER JOIN tasks t ON t.id = r.task_id INNER JOIN frequency f ON "
                                  "f.id = r.frequency_id "
                                  "WHERE t.chat_id = %s AND r.hour = %s AND r.date = %s", (chat_id, hour, today_date))
                    rows = c.fetchall()
                    if rows:
                        for row in rows:
                            try:
                                t_id, t_task, f_name, t_date, t_time, r_hour, f_id, r_id, _id = row
                                keyboard = telebot.types.InlineKeyboardMarkup()
                                do = telebot.types.InlineKeyboardButton(text="Выполнено", callback_data=f"do_{t_id}")
                                note = telebot.types.InlineKeyboardButton(text="Настроить уведомления",
                                                                          callback_data=f"note_{t_id}")
                                keyboard.add(do, note)
                                bot.send_message(_id, f'<u><b>❗Внимание!</b></u>\n\nЗадача <b>#{t_id}\n{t_task}</b>'
                                                      f'\nНапоминание: <b>{f_name}</b>\nДата задачи: <b>{t_date} '
                                                      f'{t_time}</b>', parse_mode="HTML", reply_markup=keyboard)
                                if f_id == 1:
                                    new_date = (datetime.now() + timedelta(days=1)).strftime('%d.%m.%Y')
                                elif f_id == 2:
                                    new_date = (datetime.now() + timedelta(weeks=1)).strftime('%d.%m.%Y')
                                elif f_id == 3:
                                    new_date = (datetime.now() + relativedelta(months=1)).strftime('%d.%m.%Y')
                                elif f_id == 4:
                                    new_date = (datetime.now() + relativedelta(years=1)).strftime('%d.%м.%Y')
                                else:
                                    c.execute('DELETE FROM reminders WHERE id = %s', (r_id,))
                                    conn.commit()
                                    continue
                                c.execute('UPDATE reminders SET date = %s WHERE id = %s', (new_date, r_id))
                                conn.commit()
                            except telebot.apihelper.ApiTelegramException as e:
                                if e.error_code == 403:
                                    if user_id > 0:
                                        user_off(user_id)
                                    else:
                                        chat_off(user_id)
        conn.close()
    except telebot.apihelper.ApiTelegramException as e:
        print(f"Произошла ошибка в функции notifications_for_all: {e}")
    except Exception as e:
        print(f"Произошла общая ошибка в функции notifications_for_all: {e}")


def notifications_task():
    try:
        time_ = datetime.now().strftime("%H:%M")
        date = datetime.now().strftime('%d.%m.%Y')
        conn = create_connection()
        c = conn.cursor()
        c.execute("SELECT id, task, chat_id, user_id FROM tasks WHERE time = %s AND date = %s ORDER BY time",
                  (time_, date))
        rows = c.fetchall()
        if rows:
            for row in rows:
                id_, task_, chat_id, user_id = row
                if chat_id:
                    try:
                        keyboard = types.InlineKeyboardMarkup()
                        do = types.InlineKeyboardButton(text="Выполнено", callback_data=f"do_{id_}")
                        note = types.InlineKeyboardButton(text="Настроить уведомления", callback_data=f"note_{id_}")
                        keyboard.add(do, note)
                        bot.send_message(chat_id, f'<u><b>📢Уведомление!</b></u>\n\nЗадача <b>#{id_}\n{task_}</b>',
                                         parse_mode="HTML", reply_markup=keyboard)
                    except telebot.apihelper.ApiTelegramException as e:
                        if e.error_code in [403]:
                            chat_off(chat_id)
                        else:
                            print(f"Произошла ошибка при отправке сообщения: {e}")
                else:
                    try:
                        keyboard = types.InlineKeyboardMarkup()
                        do = types.InlineKeyboardButton(text="Выполнено", callback_data=f"do_{id_}")
                        note = types.InlineKeyboardButton(text="Настроить уведомления", callback_data=f"note_{id_}")
                        keyboard.add(do, note)
                        bot.send_message(user_id, f'<u><b>📢Уведомление!</b></u>\n\nЗадача <b>#{id_}\n{task_}</b>',
                                         parse_mode="HTML", reply_markup=keyboard)
                    except telebot.apihelper.ApiTelegramException as e:
                        if e.error_code in [403]:
                            user_off(user_id)
                        else:
                            print(f"Произошла ошибка при отправке сообщения: {e}")
        conn.close()
    except telebot.apihelper.ApiTelegramException as e:
        print(f"Произошла ошибка в функции notifications_task: {e}")
    except Exception as e:
        print(f"Произошла общая ошибка в функции notifications_task: {e}")


def create_task(task_, col, id_):
    try:
        conn = create_connection()
        c = conn.cursor()
        c.execute(f'insert into tasks ({col}, task) values (%s, %s)', (id_, task_))
        conn.commit()
        c.execute(f'select id from tasks where {col} = %s and task = %s and date is NULL and time is NULL',
                  (id_, task_))
        row = c.fetchone()
        bot.send_message(id_, f'<u><i>Задача <b>#{row[0]}</b> создана</i></u>\n{task_}\n\n'
                              f'<i>Теперь напишите дату и время, на которую хотите заплонировать задачу, в формате '
                              f'<b>дд.мм.гггг чч:мм</b>, например:</i>', parse_mode="HTML")
        bot.send_message(id_, '25.05.2024 14:45')
        return row[0]
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code in [403]:
            if id_ > 0:
                user_off(id_)
            else:
                chat_off(id_)
        else:
            print(f"Произошла ошибка в функции create_task: {e}")


def add_date_time(user_id, id_task, datetime_, chat=None):
    try:
        date, time_ = datetime_.split(' ')
        conn = create_connection()
        c = conn.cursor()
        c.execute('update tasks set date = %s, time = %s where id = %s', (date, time_, id_task))
        conn.commit()
        if chat is None:
            task(user_id, id_task)
        else:
            c.execute('select u.tg_name from users u INNER JOIN users_chats uc on u.id = uc.user_id')
            rows = c.fetchall()
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for row in rows:
                c = types.KeyboardButton(text=f"Для участника {row[0]}")
                keyboard.add(c)
            c = types.KeyboardButton(text=f"Для всех")
            b = types.KeyboardButton(text='Меню')
            keyboard.add(c, b)
            bot.send_message(user_id, 'Для кого эта задача?', reply_markup=keyboard)
        conn.close()
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code in [403]:
            chat_off(user_id)
        else:
            print(f"Произошла ошибка в функции add_date_time: {e}")


def add_user_for_task(id_task, chat_id, tg_name=None):
    try:
        if tg_name:
            conn = create_connection()
            c = conn.cursor()
            c.execute('SELECT id FROM users WHERE tg_name = %s', (tg_name,))
            result = c.fetchone()
            if result is None:
                bot.send_message(chat_id, f"Пользователь {tg_name} не найден в бд. Скорее всего он "
                                          f"ни разу не обращался ко мне. Созданная задача:")
                task(chat_id, id_task)
                return
            id_ = result[0]
            print(id_)
            c.execute('UPDATE tasks SET user_id = %s WHERE id = %s', (id_, id_task))
            conn.commit()
            conn.close()
        task(chat_id, id_task)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code in [403]:
            chat_off(id_)
        print(f"Произошла ошибка в функции add_user_for_task: {e}")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")


def task(user_id, id_task):
    try:
        conn = create_connection()
        c = conn.cursor()
        c.execute('select id, user_id, chat_id, task, date, time from tasks where id = %s', (id_task, ))
        id_, user_id, chat_id, task_, date, time_ = c.fetchone()
        keyboard = types.InlineKeyboardMarkup()
        do = types.InlineKeyboardButton(text="Выполнено", callback_data=f"do_{id_task}")
        note = types.InlineKeyboardButton(text="Настроить уведомления", callback_data=f"note_{id_task}")
        keyboard.add(do, note)
        if chat_id and user_id:
            tg_name = info('tg_name', 'id', user_id, 'users')
            res = f'<u>Задача <b>#{id_} для {tg_name}</b></u>\n{task_}\n\nДата: <b>{date} {time_}</b>'
        else:
            res = f'<u>Задача <b>#{id_}</b></u>\n{task_}\n\nДата: <b>{date} {time_}</b>'
        c.execute('select r.hour, f.name, r.date from tasks t INNER JOIN reminders r on r.task_id = t.id '
                  'INNER JOIN frequency f on f.id = r.frequency_id where t.id = %s', (id_task, ))
        row = c.fetchone()
        if row is not None:
            res += (f'\n\nНапоминания настроены <b>{row[1]} в {row[0]}:00</b>\nДата следующего напоминания: '
                    f'<b>{row[2]}</b>')
        conn.close()
        res += '\n\n<i>При выполнении задача удаляется</i>'
        if chat_id is None:
            chat_id = user_id
        bot.send_message(chat_id, res, parse_mode="HTML", reply_markup=keyboard)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code in [403]:
            if e.error_code in [403]:
                if chat_id > 0:
                    user_off(chat_id)
                else:
                    chat_off(chat_id)
        else:
            print(f"Произошла ошибка в функции task: {e}")


def do_task(user_id, id_task):
    try:
        conn = create_connection()
        c = conn.cursor()
        c.execute("DELETE FROM reminders WHERE task_id = %s", (id_task, ))
        c.execute("DELETE FROM tasks WHERE id = %s", (id_task,))
        conn.commit()
        conn.close()
        bot.send_message(user_id, f'<i>Задача #{id_task} выполнена</i>', parse_mode='HTML')
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code in [403]:
            if e.error_code in [403]:
                if user_id > 0:
                    user_off(user_id)
                else:
                    chat_off(user_id)
        else:
            print(f"Произошла ошибка в функции do_task: {e}")


def set_up_notifications(user_id, id_task):
    try:
        conn = create_connection()
        c = conn.cursor()
        c.execute('select r.hour, f.name, r.id from tasks t INNER JOIN reminders r on r.task_id = t.id '
                  'INNER JOIN frequency f on f.id = r.frequency_id where t.id = %s', (id_task, ))
        rows = c.fetchall()
        if rows:
            keyboard = types.InlineKeyboardMarkup()
            note = types.InlineKeyboardButton(text="Добавить", callback_data=f"add_note_{id_task}")
            keyboard.add(note)
            bot.send_message(user_id, f'<u><b>Напоминания для задачи #{id_task}:</b></u>\n\n', parse_mode="HTML",
                             reply_markup=keyboard)
            for row in rows:
                keyboard_in = types.InlineKeyboardMarkup()
                res = f'<i>{row[1]} в {row[0]}:00</i>\n\n'
                delete = types.InlineKeyboardButton(text="Удалить", callback_data=f"del_{row[2]}")
                keyboard_in.add(delete)
                bot.send_message(user_id, res, reply_markup=keyboard_in, parse_mode="HTML")
        else:
            keyboard = types.InlineKeyboardMarkup()
            note = types.InlineKeyboardButton(text="Добавить", callback_data=f"add_note_{id_task}")
            keyboard.add(note)
            bot.send_message(user_id, f'<u><b>Напоминаний для задачи #{id_task} нет</b></u>\n\n',
                             parse_mode="HTML", reply_markup=keyboard)
        conn.close()
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code in [403]:
            if e.error_code in [403]:
                if user_id > 0:
                    user_off(user_id)
                else:
                    chat_off(user_id)
        else:
            print(f"Произошла ошибка в функции set_up_notifications: {e}")


def del_note(user_id, id_note):
    try:
        conn = create_connection()
        c = conn.cursor()
        c.execute('delete from reminders where id = %s', (id_note, ))
        conn.commit()
        bot.send_message(user_id, 'Напоминание удалено', parse_mode="HTML")
        conn.close()
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code in [403]:
            if e.error_code in [403]:
                if user_id > 0:
                    user_off(user_id)
                else:
                    chat_off(user_id)
        else:
            print(f"Произошла ошибка в функции del_note: {e}")


def add_note(user_id, info_):
    try:
        id_task, f, date, hour = info_.split('_')
        conn = create_connection()
        c = conn.cursor()
        c.execute('SELECT id FROM frequency where name = %s', (f, ))
        f = c.fetchone()[0]
        c.execute('insert into reminders (task_id, frequency_id, date, hour) values (%s, %s, %s, %s)',
                  (id_task, f, date, hour))
        conn.commit()
        bot.send_message(user_id, 'Напоминание добавлено')
        conn.close()
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code in [403]:
            if e.error_code in [403]:
                if user_id > 0:
                    user_off(user_id)
                else:
                    chat_off(user_id)
        else:
            print(f"Произошла ошибка в функции add_note: {e}")
