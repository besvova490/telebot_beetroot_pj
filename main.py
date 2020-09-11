import telebot
import datetime
import telebot_calendar
from telebot_calendar import CallbackData
import requests


TOKEN = '1317578331:AAEuCDPqvBDHMA68aWVuD5KdBAE92joNAqw'
API = ' https://beetroot-flask-pj.herokuapp.com'

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

bot = telebot.AsyncTeleBot(TOKEN)


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
    global IS_TEACHER, USER_ID, TEACHERS, SUBJECTS, MY_SCHEDULE, STUDENTS
    resp = requests.post(f'{url}/telegram-sign-in', json={'data': user_data}).json()
    IS_TEACHER = resp['data']['is_teacher']
    USER_ID = resp['data']['id']
    if IS_TEACHER:
        STUDENTS = {f"/{student['name'].replace(' ', '_')}": student['id'] for student in resp['data']['students']}
    else:
        TEACHERS = {f"/{teacher['name'].replace(' ', '_')}": teacher['id'] for teacher in resp['data']['teachers']}
    SUBJECTS = {f"/{subject['title']}": subject['id'] for subject in resp['data']['subjects']}
    if IS_TEACHER:
        MY_SCHEDULE = tuple(f"{schedule['time']}"
                            f" - {schedule['student']['name']}"
                            f" - {schedule['subject']}"
                            f" - {schedule['confirmed']}"
                            for schedule in resp['data']['schedule'])
    else:
        MY_SCHEDULE = tuple(f"{schedule['time']} "
                            f"- {schedule['teacher']['name']}"
                            f" - {schedule['subject']}"
                            f" - {schedule['confirmed']}"
                            for schedule in resp['data']['schedule'])

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


def confirm_schedule(message, url):
    global USER_ID

    requests.post(f'{url}/user/{USER_ID}/scheduling{message.text}')
    return start(message)


def helper_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    if IS_TEACHER:
        return markup.add('/start', '/help', '/my_subjects', '/my_schedule', '/my_students', '/all_subjects', '/all_students', '/schedule_lesson')
    return markup.add('/start', '/help', '/my_subjects', '/my_schedule', '/my_teachers', '/all_subjects', '/all_teachers', '/schedule_lesson')


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
        message_to_user = f'Hy this bot made your study more comfortable -- ' \
                          f'{teachers if IS_TEACHER else students}'
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
    if not resp:
        resp = 'Now subjects'
    bot.send_message(message.chat.id, resp)


@bot.message_handler(commands=['my_schedule'])
def my_schedule(message):
    global MY_SCHEDULE
    resp = MY_SCHEDULE
    if not resp:
        bot.send_message(message.chat.id, 'Now schedules')
        return
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
        if not TEACHERS:
            bot.send_message(message.chat.id, 'now teachers')
            return
        resp = "\n".join(TEACHERS)
        resp = f'{resp} \n go back: /start'
    else:
        if not STUDENTS:
            bot.send_message(message.chat.id, 'now students')
            return
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
    global ALL_TEACHERS, ALL_STUDENTS, USER_ID, IS_TEACHER
    if message.text == '/start':
        return start(message)
    users = ALL_TEACHERS if not IS_TEACHER else ALL_STUDENTS
    for user, _id in users.items():
        if user == message.text:
            if IS_TEACHER:
                 resp = requests.post(
                    f'{API}/telegram-user/{USER_ID}/{_id}')
            else:
                resp = requests.post(
                    f'{API}/telegram-user/{_id}/{USER_ID}')
            bot.send_message(message.chat.id, resp.json()['message'])
            return


@bot.message_handler(commands=['confirm_schedule'])
def not_confirm_schedule(message):
    global MY_SCHEDULE, API, USER_ID

    resp = requests.get(f'{API}/user/{USER_ID}/schedule/not-confirmed').json()
    if not resp['data']:
        bot.send_message(message.chat.id, 'All schedule approved')
        return start(message)
    resp = "\n".join(f"/{schedule['id']} - {schedule['student']['name']} - {schedule['time']}" for schedule in resp['data'])
    bot.send_message(message.chat.id, f"You must confirm these lessons: \n{resp}")
    bot.register_next_step_handler(message, confirm_schedule, url=API)


@bot.message_handler(commands=['schedule_lesson'])
def schedule_lesson(message):
    global TEACHERS, STUDENTS, IS_TEACHER

    if IS_TEACHER:
        users = STUDENTS
    else:
        users = TEACHERS

    resp = "\n".join(users)
    bot.send_message(message.chat.id, f'Choose: \n{resp}')
    bot.register_next_step_handler(message, schedule_lesson_subject)


def schedule_lesson_subject(message):
    global SCHEDULE
    global SUBJECTS
    global TEACHERS
    global IS_TEACHER

    if IS_TEACHER:
        SCHEDULE['student'] = STUDENTS.get(message.text)
        user_subjects = \
            requests.get(f'{API}/user/{SCHEDULE["student"]}').json()[
                'data']['subjects']

    else:
        SCHEDULE['teacher'] = TEACHERS.get(message.text)
        user_subjects = \
            requests.get(f'{API}/user/{SCHEDULE["teacher"]}').json()[
                'data']['subjects']
    resp = ''
    user_subjects = tuple(f"/{subject['title']}" for subject in user_subjects)
    for subject in SUBJECTS:
        if subject in user_subjects:
            resp += f"\n {subject}"
    if not resp:
        bot.send_message(message.chat.id, 'This user has not subjects. Choose another')
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
    global SCHEDULE, IS_TEACHER, USER_ID
    name, action, year, month, day = call.data.split(calendar_1.sep)
    date = telebot_calendar.calendar_query_handler(
        bot=bot, call=call, name=name, action=action, year=year, month=month, day=day
    )
    if action == "DAY":
        SCHEDULE['time'] = date.strftime('%d-%m-%Y')
        if IS_TEACHER:
            SCHEDULE['teacher'] = USER_ID
        else:
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


bot.set_webhook()
bot.polling()
