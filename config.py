import datetime
import telebot
from telebot_calendar import CallbackData


TOKEN = '1317578331:AAEuCDPqvBDHMA68aWVuD5KdBAE92joNAqw'
API = 'http://127.0.0.1:5000'

SAVED_DATA = {'subjects': {}, 'teachers': {}, 'students': {}, 'email': '',
              'my_schedule': [], 'is_teacher': False, 'user_id': None,
              'schedule': {
                  'teacher': 0, 'subject': 0, 'student': 0,
                  'time': datetime.datetime.now()
                }
              }
calendar_1 = CallbackData("calendar_1", "action", "year", "month", "day")

bot = telebot.TeleBot(TOKEN)