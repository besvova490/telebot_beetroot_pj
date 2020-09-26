import re
import requests
from config import API, SAVED_DATA, bot
from telebot import types


def create_user(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('/start')
    user_data = {'telegram_id': message.from_user.id,
                 'email': SAVED_DATA['email'],
                 'first_name': message.from_user.first_name if message.from_user.first_name else '',
                 'last_name': message.from_user.last_name if message.from_user.last_name else '',
                 'teacher': True if message.text == 'Teacher' else False}
    resp = requests.post(f'{API}/telegram-sign-up', json={'data': user_data})
    if resp.ok:
        bot.send_message(message.chat.id,
                         f'User created with role'
                         f' {"teacher" if message.text == "Teacher" else "student"}.'
                         f'\nNow you can star using this bot',
                         reply_markup=markup)
        return get_user(message, user_data['telegram_id'])


def get_user(message, user_data):
    resp = requests.post(f'{API}/telegram-sign-in',
                         json={'data': {'telegram_id': user_data}})
    if resp.status_code == 401 or resp.status_code == 404:
        bot.send_message(message.chat.id,
                         'Hi you are a new user,'
                         'Please write your email for start using this bot:')
        bot.register_next_step_handler(message, email_validation)
        return resp
    return resp


def confirm_schedule(message, schedule_id, approved=True):
    if approved:
        resp = requests.get(
            f'{API}/schedule/{schedule_id}', params={'set_conformation': 'True', 'user_id': SAVED_DATA['user_id']})
    else:
        resp = requests.delete(
            f'{API}/schedule/{schedule_id}')
        bot.send_message(message.chat.id, 'Lesson rejected \nGo to /start')
        return
    if resp.ok:
        bot.send_message(message.chat.id, 'You approved lesson \nGo to /start')
        return
    bot.send_message(message.chat.id, 'Lesson not approved \nGo to /start')


def connect_teacher_with_student(message, user_id):
    resp = requests.get(f'{API}/users/{SAVED_DATA["user_id"]}', params={'action': 'follow_user', 'user_id': {user_id}})
    bot.send_message(message.chat.id, f"{resp.json()['msg']} \nGo to /start")
    return


def add_subject(message, subject_id):
    resp = requests.get(
        f'{API}/users/{SAVED_DATA["user_id"]}', params={'action': 'follow_subject', 'subject_id': subject_id})
    bot.send_message(message.chat.id, f"{resp.json()['msg']} \nGo to /start")
    return


def get_all_users(is_teacher=False):
    if is_teacher:
        resp = requests.get(f"{API}/users", params={'users': 'students'})
        return resp.json()
    resp = requests.get(f"{API}/users", params={'users': 'teachers'})
    return resp.json()


def get_all_subjects():
    resp = requests.get(f"{API}/subjects")
    return resp


def get_not_approved_schedule():
    resp = requests.get(
        f'{API}/users/{SAVED_DATA["user_id"]}', params={'action': 'get_schedule', 'approved': False})
    return resp


def get_all_user_subjects(user_id):
    resp = requests.get(
        f'{API}/users/{user_id}'
    ).json()['items']['subjects']
    return resp


def create_schedule(schedule_data):
    resp = requests.post(f'{API}/schedule/', json={'data': schedule_data})
    return resp


def create_subject(message):
    if message.text == 'cancel':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('/start')
        bot.send_message(message.chat.id, f'You can go back to /start', reply_markup=markup)
        return
    resp = requests.post(f'{API}/subjects/',
                         json={'data': {'title': message.text.title().strip()}})
    if resp.status_code == 201:
        bot.send_message(message.chat.id, 'Subject created successful')
        return
    if resp.status_code == 409:
        bot.send_message(message.chat.id, 'Subject exist')
        return


def email_validation(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Teacher', 'Student')
    if re.search(r'^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$', message.text):
        SAVED_DATA['email'] = message.text
        bot.send_message(
            message.chat.id, 'Email is correct. \n Choose you role:',
            reply_markup=markup
        )
        bot.register_next_step_handler(message, create_user)
        return
    bot.send_message(message.chat.id, 'Email is invalid try one more time')
    return get_user(message, message.from_user.id)


def send_schedule_email(message):
    resp = requests.post(f'{API}/export-schedule',
                         json={'data': {'user_id': SAVED_DATA['user_id']}})
    if resp.status_code == 200:
        bot.send_message(message.chat.id, 'Schedule sanded for your email you'
                                          '\nGo too /start')
        return
    bot.send_message(message.chat.id, 'Sms wrong please try again later')
    return
