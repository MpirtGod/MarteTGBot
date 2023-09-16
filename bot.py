import telebot
from telebot import types
from config import TOKEN

bot = telebot.TeleBot(token=TOKEN)


@bot.message_handler(commands=['start'])
def help(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    statistic = types.KeyboardButton('Статистика')
    start = types.KeyboardButton('Помощь')

    markup.add(start, statistic)
    text = f'Привет, <b>{message.from_user.first_name}</b>, для использования бота нажми на предложенные кнопки'
    bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)


@bot.message_handler(commands=['help', 'Помощь'])
def help(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    statistic = types.KeyboardButton('Статистика')
    start = types.KeyboardButton('Помощь')

    markup.add(start, statistic)
    text = f'Привет, <b>{message.from_user.first_name}</b>'
    bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup)


@bot.message_handler()
def get_user_text(message):
    bot.send_message(message.chat.id, message, parse_mode='html')


bot.polling(none_stop=True)