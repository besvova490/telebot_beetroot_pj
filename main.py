import datetime
import re
import telebot
import telebot_calendar
import time
from bot_requests import (add_subject, create_schedule, get_user, get_all_users,
                          get_all_subjects, get_not_approved_schedule,
                          get_all_user_subjects, create_subject,
                          confirm_schedule, connect_teacher_with_student,
                          send_schedule_email)
from config import SAVED_DATA, calendar_1, bot
from telebot import types


def helper_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if SAVED_DATA['is_teacher']:
        return markup.add('/start', '/help', '/my_subjects', '/create_subject',
                          '/my_schedule', '/my_students', '/confirm_schedule',
                          '/schedule_lesson')
    return markup.add('/start', '/help', '/my_subjects', '/my_schedule',
                      '/my_teachers', '/schedule_lesson')


def start_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('/start')
    return markup


@bot.message_handler(commands=['start', 'help'])
def start(message):
    resp = get_user(message, message.from_user.id)
    if resp.status_code == 200:
        resp = resp.json()
        SAVED_DATA['is_teacher'] = resp['items']['is_teacher']
        SAVED_DATA['user_id'] = resp['items']['id']
        if SAVED_DATA['is_teacher']:
            SAVED_DATA['students'] = {
                f"/{users['full_name'].replace(' ', '_')}": users['id'] for users in
                resp['items']['users']}
        else:
            SAVED_DATA['teachers'] = {
                f"/{users['full_name'].replace(' ', '_')}": users['id'] for users in
                resp['items']['users']}
        SAVED_DATA['subjects'] = {f"/{subject['title']}": subject['id'] for
                                  subject
                                  in resp['items']['subjects']}
        SAVED_DATA['my_schedule'] = resp['items']['lesson_date']
        students = "\n/all_subjects \n/all_teachers \n/export_schedule"
        teachers = "\n/all_subjects \n/all_students \n/export_schedule" \
                   " \n/my_schedule \n/confirm_schedule"
        message_to_user = f'Hy this bot made your study more comfortable' \
                          f'{teachers if SAVED_DATA["is_teacher"] else students}'
        bot.send_message(message.chat.id, message_to_user,
                         reply_markup=helper_menu())


@bot.message_handler(commands=['create_subject'])
def new_subject(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('cancel')
    bot.send_message(message.chat.id, 'Please write tittle of'
                                      'lesson but it mas by unique', reply_markup=markup)
    bot.register_next_step_handler(message, create_subject)


@bot.message_handler(commands=['all_subjects'])
def all_subjects(message):
    markup = types.InlineKeyboardMarkup()
    resp = get_all_subjects()
    if not resp.json().get('items', False):
        bot.send_message(message.chat.id, 'Subjects not exist')
        return start(message)
    for subject in resp.json()['items']:
        markup.add(types.InlineKeyboardButton(
            text=subject['title'],
            callback_data=f'all_subjects_:{subject["id"]}'))
    bot.send_message(message.chat.id, 'Subjects', reply_markup=markup)


@bot.message_handler(commands=['my_subjects'])
def my_subjects(message):
    resp = "\n".join(SAVED_DATA['subjects'].keys())
    if not resp:
        resp = 'Now subjects'
    bot.send_message(message.chat.id, resp)


@bot.message_handler(commands=['my_schedule'])
def my_schedule(message):
    resp = '\n'.join(
        f"{schedule['subject']} -- "
        f"{schedule['time'].replace(':00 GMT', '')}" for schedule in
        SAVED_DATA['my_schedule'] if schedule['status'])
    if not resp:
        bot.send_message(message.chat.id, 'Now schedules')
        return
    bot.send_message(message.chat.id, resp)


@bot.message_handler(commands=['my_teachers', 'my_students'])
def get_user_teachers_or_students(message):
    if message.text == '/my_teachers':
        if not SAVED_DATA['teachers']:
            bot.send_message(message.chat.id, 'now teachers')
            return
        resp = "\n".join(SAVED_DATA['teachers'])
        resp = f'{resp} \n go back: /start'
    else:
        if not SAVED_DATA['students']:
            bot.send_message(message.chat.id, 'now students')
            return
        resp = "\n".join(SAVED_DATA['students'])
        resp = f'{resp} \n go back: /start'
    bot.send_message(message.chat.id, resp)


@bot.message_handler(commands=['all_teachers', 'all_students'])
def get_teachers_or_students(message):
    resp = get_all_users(SAVED_DATA['is_teacher'])
    if not resp.get('items', False):
        bot.send_message(message.chat.id,
                         f'Now {"students" if SAVED_DATA["is_teacher"] else "teachers"}')
        return start(message)
    markup = types.InlineKeyboardMarkup()
    for user in resp['items']:
        markup.add(types.InlineKeyboardButton(
            text=user['full_name'],
            callback_data=f'all_users_:{user["id"]}'))
    bot.send_message(message.chat.id,
                     f'All {"Students:" if SAVED_DATA["is_teacher"] else "Teachers:"}',
                     reply_markup=markup)


@bot.message_handler(commands=['export_schedule'])
def export_schedule(message):
    send_schedule_email(message)


@bot.message_handler(commands=['confirm_schedule'])
def not_confirm_schedule(message):
    resp = get_not_approved_schedule().json()
    if not resp['items']:
        bot.send_message(message.chat.id, 'All schedule approved')
        return start(message)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for schedule in resp['items']:
        markup.add(types.InlineKeyboardButton(
            text=f"{schedule['time'].replace('00:00:00 GMT', '')} - {schedule['subject']}",
            callback_data=f"not_confirmed_schedule_:{schedule['id']}"))
        markup.add(types.InlineKeyboardButton(
            text='\u274C',
            callback_data=f"remove_confirmed_schedule_:{schedule['id']}"))
    bot.send_message(message.chat.id,
                     f"You must confirm these lessons:", reply_markup=markup)


@bot.message_handler(commands=['schedule_lesson'])
def schedule_lesson(message):
    if SAVED_DATA["is_teacher"]:
        users = SAVED_DATA['students']
    else:
        users = SAVED_DATA['teachers']

    resp = "\n".join(users)
    bot.send_message(message.chat.id, f'Choose: \n{resp}',
                     reply_markup=start_markup())
    bot.register_next_step_handler(message, schedule_lesson_subject)


def schedule_lesson_subject(message):
    if message.text == '/start':
        return start(message)
    SAVED_DATA['schedule']['users'] = []
    if SAVED_DATA['is_teacher']:
        user = SAVED_DATA['students'].get(message.text)
        SAVED_DATA['schedule']['users'].append(user)
        user_subjects = get_all_user_subjects(user)
    else:
        user = SAVED_DATA['teachers'].get(message.text)
        SAVED_DATA['schedule']['users'].append(user)
        user_subjects = get_all_user_subjects(user)
    resp = ''
    user_subjects = tuple(f"/{subject['title']}" for subject in user_subjects)
    for subject in SAVED_DATA['subjects']:
        if subject in user_subjects:
            resp += f"\n {subject}"
    if not resp:
        bot.send_message(message.chat.id,
                         f'This user has not subjects. Choose another \nThis teacher has subjects: {" ".join(user_subjects)}')
        return schedule_lesson(message)
    bot.send_message(message.chat.id, f'Choose subject: \n{resp}',
                     reply_markup=start_markup())
    bot.register_next_step_handler(message, calendar)


def calendar(message):
    if message.text == '/start':
        return start(message)
    SAVED_DATA['schedule']['subject'] = SAVED_DATA['subjects'][message.text]
    now = datetime.datetime.now()
    bot.send_message(
        message.chat.id,
        "Selected date",
        reply_markup=telebot_calendar.create_calendar(
            name=calendar_1.prefix,
            year=now.year,
            month=now.month,
        ),
    )


def clock(message, date):
    year = datetime.datetime.now().year
    month = datetime.datetime.now().month
    day = datetime.datetime.now().day
    markup = types.InlineKeyboardMarkup(row_width=2)
    start_time = datetime.datetime(year=year, month=month, day=day, hour=11, minute=0)
    buttons_time = []
    for i in range(8):
        buttons_time.append(types.InlineKeyboardButton(
            text=start_time.strftime('\u23F0 %H:%M'),
            callback_data=f'time_:{start_time}'))
        start_time += datetime.timedelta(hours=1, minutes=10)
    markup.add(*buttons_time)
    bot.send_message(message.chat.id, f'Choose time for this date {date.strftime("%d-%m")}:', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call: types.CallbackQuery):
    if 'all_subjects' in call.data:
        subject_id = re.search(r'\d+$', call.data).group()
        return add_subject(call.message, subject_id)
    elif 'all_users' in call.data:
        user_id = re.search(r'\d+$', call.data).group()
        return connect_teacher_with_student(call.message, user_id)
    elif 'not_confirmed_schedule' in call.data:
        schedule_id = re.search(r'\d+$', call.data).group()
        return confirm_schedule(call.message, schedule_id)
    elif 'remove_confirmed_schedule' in call.data:
        schedule_id = re.search(r'\d+$', call.data).group()
        return confirm_schedule(call.message, schedule_id, False)
    elif 'time_' in call.data:
        lesson_time = re.search(r'(?<=_:).*', call.data).group()
        lesson_time = datetime.datetime.strptime(lesson_time, '%Y-%m-%d %H:%M:%S')
        SAVED_DATA['schedule']['lesson_time'] = lesson_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        create_schedule(SAVED_DATA['schedule'])
        bot.send_message(
            chat_id=call.from_user.id,
            text=f"Schedule created\nGo too main: /start",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        return
    name, action, year, month, day = call.data.split(calendar_1.sep)
    date = telebot_calendar.calendar_query_handler(
        bot=bot, call=call, name=name, action=action, year=year, month=month,
        day=day
    )
    if action == "DAY":
        if date < datetime.datetime.now():
            bot.send_message(call.message.chat.id, "You can choose date older than today, try one more time")
            return schedule_lesson(call.message)
        SAVED_DATA['schedule']['users'].append(SAVED_DATA['user_id'])
        return clock(call.message, date)
    elif action == "CANCEL":
        bot.send_message(
            chat_id=call.from_user.id,
            text="Cancellation \ngo too main: \start",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        return start(call.message)


if __name__ == '__main__':
    while True:
        try:
            bot.set_webhook()
            bot.polling(none_stop=True)
        except Exception as e:
            telebot.logger.error(e)
            time.sleep(15)
