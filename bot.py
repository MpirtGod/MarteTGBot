import telebot
from telebot import types
from config import TOKEN
from main import make_statistic
from datetime import datetime, timedelta
import dateutil.relativedelta

bot = telebot.TeleBot(token=TOKEN)

time_dict = {'сегодня': (datetime.now()).strftime('%d-%b-%Y'),
             'неделю': (datetime.today() - timedelta(days=datetime.today().weekday() % 7)).strftime('%d-%b-%Y'),
             'месяц': datetime(datetime.now().year, datetime.now().month, 1).strftime('%d-%b-%Y'),
             'время': datetime(2010, 1, 1).strftime('%d-%b-%Y')}


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
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    statistic_day = types.KeyboardButton('Статистика за сегодня')
    statistic_week = types.KeyboardButton('Статистика за неделю')
    statistic_month = types.KeyboardButton('Статистика за месяц')
    statistic_all = types.KeyboardButton('Статистика за все время')
    statistic_cities = types.KeyboardButton('Статистика по городам')
    back = types.KeyboardButton('Назад')

    markup.add(statistic_day, statistic_week, statistic_month, statistic_all, statistic_cities, back)
    text = f'Выберите период за который выведется статистика'
    bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)


@bot.message_handler()
def get_user_text(message):
    if message.text.lower() == "помощь":
        help(message)
    elif message.text.lower() == "старт" or message.text.lower() == "привет":
        start(message)
    elif message.text.lower() == 'статистика':
        statistics(message)
    elif message.text.lower() == 'статистика за сегодня' or message.text.lower() == 'статистика за неделю' or message.text.lower() == 'статистика за месяц' or message.text.lower() == 'статистика за все время':
        bot.send_message(message.chat.id, 'Загрузка...', parse_mode='html')
        start_date = time_dict[message.text.split(' ')[-1]]
        sender = 'noreply@tilda.ws'
        search_criteria = f'(FROM "{sender}" SINCE "{start_date}")'
        statistic = make_statistic(search_criteria)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        statistic_button = types.KeyboardButton('Статистика')
        help_button = types.KeyboardButton('Помощь')

        markup.add(help_button, statistic_button)
        text = statistic
        bot.delete_message(message.chat.id, message_id=message.id+1)
        bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)
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


