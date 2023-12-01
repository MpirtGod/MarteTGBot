import re
from time import sleep
import telebot
from telebot import types
from config import TOKEN, known_usernames
from main import make_statistic
from datetime import datetime, timedelta
from functools import wraps

bot = telebot.TeleBot(token=TOKEN)

last_message_is_city_statistic = False


def is_known_username(username):
    """
    Проверяет, есть ли указанное имя пользователя в списке известных.

    Parameters
    ----------
    username : str
        Имя пользователя для проверки.

    Returns
    -------
    bool
        True, если имя пользователя известно, False в противном случае.
    """

    return username in known_usernames


def private_access():
    """
    Декоратор, ограничивающий доступ к команде для пользователей, разрешенных функцией is_known_username.
    """
    def deco_restrict(f):
        """
        Функция-декоратор, проверяющая доступ пользователя к команде.

        Returns
        -------
        Значение, возвращаемое оригинальной функцией, если пользователь разрешен.
        Сообщение об отклонении доступа, если пользователь не разрешен.
        """
        @wraps(f)
        def f_restrict(message, *args, **kwargs):
            username = message.from_user.username
            if is_known_username(username):
                return f(message, *args, **kwargs)
            else:
                bot.send_message(message.chat.id, text=f'Твоего ника ({message.from_user.username}) нет в списке разрешенных пользователей. Доступ отклонен!')
        return f_restrict  # true decorator
    return deco_restrict


def check_date(date_string):
    """
    Проверяет правильный ли формат даты и существует ли такая дата.

    Parameters
    ----------
    date_string : str
        Дата в формате dd.mm.yyyy

    Returns
    -------
    bool
        True, если дата имеет правильный формат и существует; False в противном случае.
    """
    try:
        # Проверка формата даты
        datetime.strptime(date_string, '%d.%m.%Y')
        if datetime.strptime(date_string, '%d.%m.%Y') > datetime.now():
            return False
        return True
    except ValueError:
        return False


@bot.message_handler(commands=['start'])
@private_access()
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    statistic_sales = types.KeyboardButton('Статистика по продажам')
    statistic_by_cities = types.KeyboardButton('Статистика по городам')

    markup.add(statistic_sales, statistic_by_cities)
    text = f'Привет, <b>{message.from_user.first_name}</b>, для использования бота нажми на предложенные кнопки'
    bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)


@bot.message_handler(func=lambda message: message.text.lower() == 'старт' or message.text.lower() == 'привет')
@private_access()
def start_text(message):
    start(message)


# @bot.message_handler(commands=['help'])
# @private_access()
# def help(message):
#     markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
#     statistic_sales = types.KeyboardButton('Статистика по продажам')
#     statistic_by_cities = types.KeyboardButton('Статистика по городам')
#
#     markup.add(statistic_sales, statistic_by_cities)
#     text = f'Этот Бот создан для магазина Márte. Для вывода статистики за определенный промежуток времени нажмите "Статистика".'
#     bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)
#
#
# @bot.message_handler(func=lambda message: message.text.lower() == 'помощь')
# @private_access()
# def help_text(message):
#     help(message)


@bot.message_handler(func=lambda message: message.text.lower() == 'назад')
@private_access()
def back(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    statistic_sales = types.KeyboardButton('Статистика по продажам')
    statistic_by_cities = types.KeyboardButton('Статистика по городам')

    markup.add(statistic_sales, statistic_by_cities)
    text = f'Выберите команду'
    bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)


@bot.message_handler(commands=['statistic_sales'])
@private_access()
def statistics_sales(message):
    global last_message_is_city_statistic
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    statistic_day = types.KeyboardButton('Статистика за сегодня')
    statistic_week = types.KeyboardButton('Статистика за рабочую неделю')
    statistic_month = types.KeyboardButton('Статистика за месяц')
    statistic_all = types.KeyboardButton('Статистика за все время')
    back = types.KeyboardButton('Назад')

    last_message_is_city_statistic = False
    markup.add(statistic_day, statistic_week, statistic_month, statistic_all, back)
    text = f'Выберите период за который выведется статистика или введите одну или две даты (через тире) в формате 01.01.2001 для поиска по произвольному промежутку'
    bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)


@bot.message_handler(func=lambda message: message.text.lower() == 'статистика по продажам')
@private_access()
def statistics_sales_text(message):
    statistics_sales(message)


@bot.message_handler(commands=['statistic_by_cities'])
@private_access()
def statistics_by_cities(message):
    global last_message_is_city_statistic
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    statistic_day = types.KeyboardButton('Статистика за сегодня')
    statistic_week = types.KeyboardButton('Статистика за рабочую неделю')
    statistic_month = types.KeyboardButton('Статистика за месяц')
    statistic_all = types.KeyboardButton('Статистика за все время')
    back = types.KeyboardButton('Назад')

    last_message_is_city_statistic = True
    markup.add(statistic_day, statistic_week, statistic_month, statistic_all, back)
    text = f'Выберите период за который выведется статистика или введите одну или две даты (через тире) в формате 01.01.2001 для поиска по произвольному промежутку'
    bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)


@bot.message_handler(func=lambda message: message.text.lower() == 'статистика по городам')
@private_access()
def statistics_by_cities_text(message):
    statistics_by_cities(message)


@bot.message_handler(func=lambda message: message.text.lower() == 'статистика за сегодня' or
                                          message.text.lower() == 'статистика за рабочую неделю' or
                                          message.text.lower() == 'статистика за месяц' or
                                          message.text.lower() == 'статистика за все время')
@private_access()
def make_statistic_cities(message):
    global last_message_is_city_statistic
    time_dict = {'сегодня': (datetime.now()),
                 'неделю': (datetime.today() - timedelta(days=datetime.today().weekday() % 7)),
                 'месяц': datetime(datetime.now().year, datetime.now().month, 1),
                 'время': datetime(2023, 7, 8)}
    bot.send_message(message.chat.id, 'Загрузка...', parse_mode='html')
    print('send_message')
    start_date = time_dict[message.text.split(' ')[-1]]

    statistic = make_statistic(start_date=start_date, end_date=datetime.now(), by_cities=last_message_is_city_statistic)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    statistic_sales = types.KeyboardButton('Статистика по продажам')
    statistic_by_cities = types.KeyboardButton('Статистика по городам')

    markup.add(statistic_sales, statistic_by_cities)
    text = statistic
    bot.delete_message(message.chat.id, message_id=message.id + 1)
    bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)


@bot.message_handler(func=lambda message: re.match(r'\d{2}\.\d{2}\.\d{4}', message.text) or
                                          re.match(r'\d{2}\.\d{2}\.\d{4}[-]\d{2}\.\d{2}\.\d{4}',
                                                   message.text.replace(' ', '')))
@private_access()
def make_statistic_with_user_date(message):
    global last_message_is_city_statistic
    message_text = message.text.replace(' ', '').split('-')
    if (len(message_text) == 1 and check_date(message_text[0])) or \
            (len(message_text) == 2 and check_date(message_text[0]) and check_date(message_text[1])):
        bot.send_message(message.chat.id, 'Загрузка...', parse_mode='html')
        start_date = datetime.strptime(message_text[0], '%d.%m.%Y')
        end_date = datetime.strptime(message_text[1], '%d.%m.%Y') if len(message_text) == 2 else datetime.now()

        statistic = make_statistic(start_date=start_date, end_date=end_date, by_cities=last_message_is_city_statistic)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        statistic_sales = types.KeyboardButton('Статистика по продажам')
        statistic_by_cities = types.KeyboardButton('Статистика по городам')

        markup.add(statistic_sales, statistic_by_cities)
        text = statistic
        bot.delete_message(message.chat.id, message_id=message.id + 1)
        bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        statistic_sales = types.KeyboardButton('Статистика по продажам')
        statistic_by_cities = types.KeyboardButton('Статистика по городам')

        markup.add(statistic_sales, statistic_by_cities)
        bot.send_message(message.chat.id, "Некорректная дата", parse_mode='html', reply_markup=markup)


@bot.message_handler()
@private_access()
def get_user_text(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    statistic_sales = types.KeyboardButton('Статистика по продажам')
    statistic_by_cities = types.KeyboardButton('Статистика по городам')

    markup.add(statistic_sales, statistic_by_cities)
    text = f'Неизвестная команда'
    bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)


while True:
    try:
        bot.polling(none_stop=True)
    except Exception as _ex: #Предотвращения остановки работы бота при неудачной попытке подключения к серверам Telegram.
        print(_ex)
        sleep(15)