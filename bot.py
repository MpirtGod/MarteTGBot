import re

import telebot
from telebot import types
from config import TOKEN
from main import make_statistic
from datetime import datetime, timedelta

bot = telebot.TeleBot(token=TOKEN)

time_dict = {'сегодня': (datetime.now()),
             'неделю': (datetime.today() - timedelta(days=datetime.today().weekday() % 7)),
             'месяц': datetime(datetime.now().year, datetime.now().month, 1),
             'время': datetime(2023, 7, 8)}


def check_date(date_string):
    try:
        # Проверка формата даты
        datetime.strptime(date_string, '%d.%m.%Y')
        return True
    except ValueError:
        return False


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    statistic_button = types.KeyboardButton('Статистика')
    help_button = types.KeyboardButton('Помощь')
    markup.add(help_button, statistic_button)

    text = f'Привет, <b>{message.from_user.first_name}</b>, для использования бота нажми на предложенные кнопки'

    bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)


@bot.message_handler(commands=['help'])
def help(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    statistic_button = types.KeyboardButton('Статистика')
    help_button = types.KeyboardButton('Помощь')

    markup.add(help_button, statistic_button)
    text = f'Этот Бот создан для магазина Márte. Для вывода статистики за определенный промежуток времени нажмите "Статистика".'
    bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)


@bot.message_handler(commands=['statistic'])
def statistics(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    statistic_day = types.KeyboardButton('Статистика за сегодня')
    statistic_week = types.KeyboardButton('Статистика за рабочую неделю')
    statistic_month = types.KeyboardButton('Статистика за месяц')
    statistic_all = types.KeyboardButton('Статистика за все время')
    statistic_cities = types.KeyboardButton('Статистика по городам')
    back = types.KeyboardButton('Назад')

    markup.add(statistic_day, statistic_week, statistic_month, statistic_all, statistic_cities, back)
    text = f'Выберите период за который выведется статистика или введите одну или две даты (через тире) в формате 01.01.2001 для поиска по произвольному промежутку'
    bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)


@bot.message_handler()
def get_user_text(message):
    if message.text.lower() == "помощь":
        help(message)
    elif message.text.lower() == "старт" or message.text.lower() == "привет":
        start(message)
    elif message.text.lower() == 'статистика':
        statistics(message)
    elif message.text.lower() == 'статистика за сегодня' or message.text.lower() == 'статистика за рабочую неделю' or message.text.lower() == 'статистика за месяц' or message.text.lower() == 'статистика за все время':
        bot.send_message(message.chat.id, 'Загрузка...', parse_mode='html')
        start_date = time_dict[message.text.split(' ')[-1]]

        statistic = make_statistic(start_date=start_date)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        statistic_button = types.KeyboardButton('Статистика')
        help_button = types.KeyboardButton('Помощь')

        markup.add(help_button, statistic_button)
        text = statistic
        bot.delete_message(message.chat.id, message_id=message.id+1)
        bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)
    elif re.match(r'\d{2}\.\d{2}\.\d{4}', message.text) or re.match(r'\d{2}\.\d{2}\.\d{4}[ -]\d{2}\.\d{2}\.\d{4}', message.text.replace(' ', '')):
        message_text = message.text.replace(' ', '').split('-')
        if check_date(message_text[0]) and len(message_text) == 1:
            bot.send_message(message.chat.id, 'Загрузка...', parse_mode='html')
            start_date = datetime.strptime(message_text[0], '%d.%m.%Y')

            statistic = make_statistic(start_date=start_date)
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            statistic_button = types.KeyboardButton('Статистика')
            help_button = types.KeyboardButton('Помощь')

            markup.add(help_button, statistic_button)
            text = statistic
            bot.delete_message(message.chat.id, message_id=message.id + 1)
            bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)
        elif len(message_text) == 2 and check_date(message_text[1]) and check_date(message_text[0]) and message_text[0] < message_text[1]:
            bot.send_message(message.chat.id, 'Загрузка...', parse_mode='html')
            start_date = datetime.strptime(message_text[0], '%d.%m.%Y')
            end_date = datetime.strptime(message_text[1], '%d.%m.%Y')

            statistic = make_statistic(start_date=start_date, end_date=end_date)
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            statistic_button = types.KeyboardButton('Статистика')
            help_button = types.KeyboardButton('Помощь')

            markup.add(help_button, statistic_button)
            text = statistic
            bot.delete_message(message.chat.id, message_id=message.id + 1)
            bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            statistic_button = types.KeyboardButton('Статистика')
            help_button = types.KeyboardButton('Помощь')

            markup.add(help_button, statistic_button)
            bot.send_message(message.chat.id, "Некорректная дата", parse_mode='html', reply_markup=markup)
    elif message.text.lower() == 'назад':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        statistic_button = types.KeyboardButton('Статистика')
        help_button = types.KeyboardButton('Помощь')

        markup.add(help_button, statistic_button)
        text = f'Выберите команду'
        bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        statistic_button = types.KeyboardButton('Статистика')
        help_button = types.KeyboardButton('Помощь')

        markup.add(help_button, statistic_button)
        text = f'Неизвестная команда'
        bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)


bot.polling(none_stop=True)


