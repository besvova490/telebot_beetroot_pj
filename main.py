import telebot
import datetime
import telebot_calendar
from telebot_calendar import CallbackData
import requests


TOKEN = '1317578331:AAEuCDPqvBDHMA68aWVuD5KdBAE92joNAqw'
API = 'http://127.0.0.1:5003/'

SUBJECTS = {}
TEACHERS = {}
STUDENTS = {}
MY_SCHEDULE = {}
IS_TEACHER = False
USER_ID = 0
SCHEDULE = {'teacher': 0, 'subject': 0, 'student': 0, 'time': datetime.datetime.now()}

ALL_SUBJECTS = {}
ALL_TEACHERS = {}
ALL_STUDENTS = {}

calendar_1 = CallbackData("calendar_1", "action", "year", "month", "day")

bot = telebot.TeleBot(TOKEN)


def check_user(url, telegram_id):
    resp = requests.post(f'{url}/telegram-check', json={'data': {'telegram_id': int(telegram_id)}})
    print(resp)
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
    global IS_TEACHER, USER_ID, TEACHERS, SUBJECTS, MY_SCHEDULE
    resp = requests.post(f'{url}/telegram-sign-in', json={'data': user_data}).json()
    IS_TEACHER = resp['data']['is_teacher']
    USER_ID = resp['data']['id']
    TEACHERS = {f"/{teacher['name'].replace(' ', '_')}": teacher['id'] for teacher in resp['data']['teachers']}
    SUBJECTS = {f"/{subject['title']}": subject['id'] for subject in resp['data']['subjects']}
    MY_SCHEDULE = (f"{schedule['time']} - {schedule['teacher']['name']} - {schedule['subject']}" for schedule in resp['data']['schedule'])

    return resp


def get_all_subjects(url):
    global ALL_SUBJECTS
    resp = requests.get(f"{url}/subjects")
    resp = resp.json()['data']
    ALL_SUBJECTS = {f"/{subject['title']}": subject['id'] for subject in resp}
    return ALL_SUBJECTS


def get_all_teachers(url):
    global ALL_TEACHERS
    resp = requests.get(f"{url}/tutors")
    resp = resp.json()['data']
    ALL_TEACHERS = {f"/{teacher['name'].replace(' ', '_')}": teacher['id'] for teacher in resp}
    return ALL_TEACHERS


def get_all_students(url):
    global ALL_STUDENTS
    resp = requests.get(f"{url}/students")
    resp = resp.json()['data']
    ALL_STUDENTS = {f"/{student['name'].replace(' ', '_')}": student['id'] for student in resp}
    return ALL_STUDENTS


def helper_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    if IS_TEACHER:
        return markup.add('/start', '/help', '/my_subjects', '/my_schedule', '/my_students', '/all_subjects', '/all_students')
    return markup.add('/start', '/help', '/my_subjects', '/my_schedule', '/my_teachers', '/all_subjects', '/all_teachers', '/schedule_lesson')


@bot.message_handler(commands=['start', 'help'])
def start(message):
    if not check_user(API, message.from_user.id):
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('teacher', 'student')
        bot.send_message(message.chat.id, 'Hy you are new user please choose role:', reply_markup=markup)
        bot.register_next_step_handler(message, create_user, url=API)
    else:
        resp = get_user(API, message.chat.id)
        print(resp)
        message_to_user = f'Hy this bot made your study more comfortable -- ' \
                          f'\n' \
                          f'\n/my_subjects \n/my_teachers \n/my_schedule'
        bot.reply_to(message, message_to_user, reply_markup=helper_menu())


@bot.message_handler(commands=['all_subjects'])
def all_subjects(message):
    global ALL_SUBJECTS

    if not ALL_SUBJECTS:
        ALL_SUBJECTS = get_all_subjects(API)
    resp = '\n'.join(ALL_SUBJECTS)
    bot.reply_to(message, f'Subjects: \n{resp}\n go back: /start')
    bot.register_next_step_handler(message, add_subject)


@bot.message_handler(commands=['my_subjects'])
def my_subjects(message):
    resp = "\n".join(SUBJECTS.keys())
    bot.send_message(message.chat.id, resp)


@bot.message_handler(commands=['my_schedule'])
def my_schedule(message):
    resp = MY_SCHEDULE
    bot.send_message(message.chat.id, "\n".join(resp))


@bot.message_handler(commands=['add_subjects'])
def add_subject(message):
    if message.text == '/add_subjects':
        return all_subjects(message)
    if message.text == '/start':
        return start(message)
    subject_id = ALL_SUBJECTS.get(message.text)
    resp = requests.post(f'{API}/subjects/{subject_id}/{USER_ID}').json()
    bot.send_message(message.chat.id, resp['message'])


@bot.message_handler(commands=['my_teachers', 'my_students'])
def get_user_teachers_or_students(message):
    global TEACHERS, STUDENTS
    if message.text == '/my_teachers':
        resp = "\n".join(TEACHERS)
        resp = f'{resp} \n go back: /start'
    else:
        resp = "\n".join(STUDENTS)
        resp = f'{resp} \n go back: /start'
    bot.send_message(message.chat.id, resp)


@bot.message_handler(commands=['all_teachers', 'all_students'])
def get_teachers_or_students(message):
    global ALL_TEACHERS
    global ALL_STUDENTS

    if message.text == '/all_teachers':
        if not ALL_TEACHERS:
            ALL_TEACHERS = get_all_teachers(API)
        resp = '\n'.join(ALL_TEACHERS)
        resp = f'{resp} \n go back: /start'
    else:
        if not ALL_STUDENTS:
            ALL_STUDENTS = get_all_students(API)
        resp = '\n'.join(ALL_STUDENTS)
        resp = f'{resp} \n go back: /start'
    bot.send_message(message.chat.id, resp)
    bot.register_next_step_handler(message, connect_teacher_with_student)


def connect_teacher_with_student(message):
    global ALL_TEACHERS, USER_ID
    if message.text == '/start':
        return start(message)
    for teacher, id in ALL_TEACHERS.items():
        if teacher == message.text:
            resp = requests.post (
                f'{API}/telegram-user/{id}/{USER_ID}')
            bot.send_message(message.chat.id, resp.json()['message'])
            return


@bot.message_handler(commands=['schedule_lesson'])
def schedule_lesson(message):
    global TEACHERS

    resp = "\n".join(TEACHERS)
    bot.send_message(message.chat.id, f'Choose teacher: \n{resp}')
    bot.register_next_step_handler(message, schedule_lesson_subject)


def schedule_lesson_subject(message):
    global SCHEDULE
    global SUBJECTS
    global TEACHERS

    SCHEDULE['teacher'] = TEACHERS.get(message.text)
    resp = ''
    teacher_subjects = \
    requests.get(f'{API}/user/{SCHEDULE["teacher"]}').json()[
        'data']['subjects']
    teacher_subjects = tuple(f"/{subject['title']}" for subject in teacher_subjects)
    for subject in SUBJECTS:
        if subject in teacher_subjects:
            resp += f"\n {subject}"
    if not resp:
        bot.send_message(message.chat.id, 'This teacher has not subjects. Choose another')
        return schedule_lesson(message)
    bot.send_message(message.chat.id, f'Choose subject: \n{resp}')
    bot.register_next_step_handler(message, calendar)


def calendar(message):
    global SCHEDULE
    global SUBJECTS
    SCHEDULE['subject'] = SUBJECTS[message.text]
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
    global SCHEDULE
    name, action, year, month, day = call.data.split(calendar_1.sep)
    date = telebot_calendar.calendar_query_handler(
        bot=bot, call=call, name=name, action=action, year=year, month=month, day=day
    )
    if action == "DAY":
        SCHEDULE['time'] = date.strftime('%d-%m-%Y')
        SCHEDULE['student'] = USER_ID
        requests.post(f'{API}/scheduling', json={'data': SCHEDULE})
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


bot.polling()
