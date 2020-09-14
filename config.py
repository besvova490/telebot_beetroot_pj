import datetime
from telebot_calendar import CallbackData


TOKEN = ''
API = 'https://beetroot-besvova490.herokuapp.com'

SAVED_DATA = {'subjects': {}, 'teachers': {}, 'students': {},
              'my_schedule': [], 'is_teacher': False, 'user_id': 0,
              'schedule': {
                  'teacher': 0, 'subject': 0, 'student': 0,
                  'time': datetime.datetime.now()
              },
              'all_subjects': {}, 'all_teachers': {}, 'all_students': {}
              }
calendar_1 = CallbackData("calendar_1", "action", "year", "month", "day")