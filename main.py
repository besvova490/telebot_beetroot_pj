import telebot
import datetime
import telebot_calendar
import requests
import time
from config import API, SAVED_DATA, TOKEN, calendar_1


bot = telebot.TeleBot(TOKEN)


def check_user(url, telegram_id):
    resp = requests.post(f'{url}/telegram-check', json={'data': {'telegram_id': telegram_id}}).json()
    return resp


def create_user(message, url):
    user_data = {'telegram_id': str(message.from_user.id),
                 'first_name': message.from_user.first_name,
                 'last_name': message.from_user.last_name,
                 'teacher': True if message.text == 'teacher' else False}
    resp = requests.post(f'{url}/telegram-sign-up',
                         json={'data': user_data})
    if resp.ok:
        return start(message)


def get_user(url, user_data):
    resp = requests.post(f'{url}/telegram-sign-in', json={'data': user_data}).json()
    SAVED_DATA['is_teacher'] = resp['data']['is_teacher']
    SAVED_DATA['user_id'] = resp['data']['id']
    if SAVED_DATA['is_teacher']:
        SAVED_DATA['students'] = {f"/{users['name'].replace(' ', '_')}": users['id'] for users in resp['data']['users']}
    else:
        SAVED_DATA['teachers'] = {f"/{users['name'].replace(' ', '_')}": users['id'] for users in resp['data']['users']}
    SAVED_DATA['subjects'] = {f"/{subject['title']}": subject['id'] for subject in resp['data']['subjects']}
    SAVED_DATA['my_schedule'] = resp['data']['lesson_date']

    return resp


def get_all_subjects(url):
    resp = requests.get(f"{url}/subjects")
    resp = resp.json()['data']
    SAVED_DATA['all_subjects'] = {f"/{subject['title']}": subject['id'] for subject in resp}
    return SAVED_DATA['all_subjects']


def get_all_teachers(url):
    resp = requests.get(f"{url}/tutors")
    resp = resp.json()['data']
    SAVED_DATA['all_teachers'] = {f"/{teacher['name'].replace(' ', '_')}": teacher['id'] for teacher in resp}
    return SAVED_DATA['all_teachers']


def get_all_students(url):
    resp = requests.get(f"{url}/students")
    resp = resp.json()['data']
    SAVED_DATA['all_students'] = {f"/{student['name'].replace(' ', '_')}": student['id'] for student in resp}
    return SAVED_DATA['all_students']


def confirm_schedule(message, url):
    resp = requests.post(f'{url}/user/{SAVED_DATA["user_id"]}/scheduling{message.text}')
    if resp.ok:
        bot.send_message(message.chat.id, 'You approved lesson')
        return start(message)
    bot.send_message(message.chat.id, 'Lesson not approved')
    return start(message)


def helper_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    if SAVED_DATA['is_teacher']:
        return markup.add('/start', '/help', '/my_subjects', '/my_schedule', '/my_students', '/all_subjects', '/all_students', '/schedule_lesson')
    return markup.add('/start', '/help', '/my_subjects', '/my_schedule', '/my_teachers', '/all_subjects', '/all_teachers', '/schedule_lesson')


@bot.message_handler(func=lambda x: x.text == f'Create Account')
def test(message):
    bot.reply_to(message, f'catch {message.text}')


@bot.message_handler(commands=['start', 'help'])
def start(message):
    user = check_user(API, message.from_user.id)
    if not user['exist']:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('teacher', 'student')
        bot.send_message(message.chat.id, 'Hy you are new user please choose role:', reply_markup=markup)
        bot.register_next_step_handler(message, create_user, url=API)
    else:
        students = "\n/my_subjects \n/my_teachers \n/my_schedule"
        teachers = "\n/my_subjects \n/my_students \n/my_schedule \n/confirm_schedule"
        get_user(API, {'telegram_id':  message.chat.id})
        message_to_user = f'Hy this bot made your study more comfortable' \
                          f'{teachers if SAVED_DATA["is_teacher"] else students}'
        bot.send_message(message.chat.id, message_to_user, reply_markup=helper_menu())


@bot.message_handler(commands=['all_subjects'])
def all_subjects(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('/start')
    if not SAVED_DATA['all_subjects']:
        SAVED_DATA['all_subjects'] = get_all_subjects(API)
    resp = '\n'.join(SAVED_DATA['all_subjects'])
    bot.send_message(message.chat.id, f'Subjects: \n{resp}\n go back: /start', reply_markup=markup)
    bot.register_next_step_handler(message, add_subject)


@bot.message_handler(commands=['my_subjects'])
def my_subjects(message):
    resp = "\n".join(SAVED_DATA['subjects'].keys())
    if not resp:
        resp = 'Now subjects'
    bot.send_message(message.chat.id, resp)


@bot.message_handler(commands=['my_schedule'])
def my_schedule(message):
    resp = '\n'.join(f"{schedule['subject']} -- {schedule['time']}" for schedule in SAVED_DATA['my_schedule'] if schedule['confirmation'])
    if not resp:
        bot.send_message(message.chat.id, 'Now schedules')
        return
    bot.send_message(message.chat.id, resp)


@bot.message_handler(commands=['add_subjects'])
def add_subject(message):
    if message.text == '/add_subjects':
        return all_subjects(message)
    if message.text == '/start':
        return start(message)
    subject_id = SAVED_DATA['all_subjects'].get(message.text)
    resp = requests.post(f'{API}/subjects/{subject_id}/{SAVED_DATA["user_id"]}').json()
    bot.send_message(message.chat.id, resp['message'])


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
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('/start')
    if message.text == '/all_teachers':
        if not SAVED_DATA['all_teachers']:
            SAVED_DATA['all_teachers'] = get_all_teachers(API)
        resp = '\n'.join(SAVED_DATA['all_teachers'])
        resp = f'{resp} \n go back: /start'
    else:
        if not SAVED_DATA['all_students']:
            SAVED_DATA['all_students'] = get_all_students(API)
        resp = '\n'.join(SAVED_DATA['all_students'])
        resp = f'{resp} \n go back: /start'
    bot.send_message(message.chat.id, resp, reply_markup=markup)
    bot.register_next_step_handler(message, connect_teacher_with_student)


def connect_teacher_with_student(message):
    if message.text == '/start':
        return start(message)
    users = SAVED_DATA['all_students'] if SAVED_DATA['is_teacher'] else SAVED_DATA['all_teachers']
    for user, _id in users.items():
        if user == message.text:
            if SAVED_DATA['is_teacher']:
                 resp = requests.post(
                    f'{API}/user/{SAVED_DATA["user_id"]}/{_id}')
            else:
                resp = requests.post(
                    f'{API}/user/{_id}/{SAVED_DATA["user_id"]}')
            bot.send_message(message.chat.id, resp.json()['message'])
            return


@bot.message_handler(commands=['confirm_schedule'])
def not_confirm_schedule(message):
    resp = requests.get(f'{API}/user/{SAVED_DATA["user_id"]}/schedule/not-confirmed').json()
    if not resp['data']:
        bot.send_message(message.chat.id, 'All schedule approved')
        return start(message)
    resp = "\n".join(f"/{schedule['id']} - {schedule['lesson_time']} - {schedule['subject']['title']}" for schedule in resp['data'])
    bot.send_message(message.chat.id, f"You must confirm these lessons: \n{resp}")
    bot.register_next_step_handler(message, confirm_schedule, url=API)


@bot.message_handler(commands=['schedule_lesson'])
def schedule_lesson(message):
    if SAVED_DATA["is_teacher"]:
        users = SAVED_DATA['students']
    else:
        users = SAVED_DATA['teachers']

    resp = "\n".join(users)
    bot.send_message(message.chat.id, f'Choose: \n{resp}')
    bot.register_next_step_handler(message, schedule_lesson_subject)


def schedule_lesson_subject(message):
    if SAVED_DATA['is_teacher']:
        SAVED_DATA['schedule']['student'] = SAVED_DATA['students'].get(message.text)
        user_subjects = \
            requests.get(f'{API}/user/{SAVED_DATA["schedule"]["student"]}').json()[
                'data']['subjects']

    else:
        SAVED_DATA['schedule']['teacher'] = SAVED_DATA['teachers'].get(message.text)
        user_subjects = \
            requests.get(f'{API}/{SAVED_DATA["schedule"]["teachers"]}').json()[
                'data']['subjects']
    resp = ''
    user_subjects = tuple(f"/{subject['name']}" for subject in user_subjects)
    for subject in SAVED_DATA['subjects']:
        if subject in user_subjects:
            resp += f"\n {subject}"
    if not resp:
        bot.send_message(message.chat.id, 'This user has not subjects. Choose another')
        return schedule_lesson(message)
    bot.send_message(message.chat.id, f'Choose subject: \n{resp}')
    bot.register_next_step_handler(message, calendar)


def calendar(message):
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


@bot.callback_query_handler(func=lambda call: call.data.startswith(calendar_1.prefix))
def callback_inline(call: telebot.types.CallbackQuery):
    name, action, year, month, day = call.data.split(calendar_1.sep)
    date = telebot_calendar.calendar_query_handler(
        bot=bot, call=call, name=name, action=action, year=year, month=month, day=day
    )
    if action == "DAY":
        SAVED_DATA['schedule']['time'] = date.strftime('%d-%m-%Y')
        if SAVED_DATA['is_teacher']:
            SAVED_DATA['schedule']['teacher'] = SAVED_DATA
        else:
            SAVED_DATA['schedule']['student'] = SAVED_DATA
        requests.post(f'{API}/scheduling', json={'data': SAVED_DATA['schedule']})
        bot.send_message(
            chat_id=call.from_user.id,
            text=f"Schedule created\nGo too main: /start",
            reply_markup=telebot.types.ReplyKeyboardRemove(),
        )
    elif action == "CANCEL":
        bot.send_message(
            chat_id=call.from_user.id,
            text="Cancellation \ngo too main: \start",
            reply_markup=telebot.types.ReplyKeyboardRemove(),
        )


if __name__ == '__main__':
    while True:
        try:
            bot.set_webhook()
            bot.polling(none_stop=True)
        except Exception as e:
            telebot.logger.error(e)
            time.sleep(5)
