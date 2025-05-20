import telebot
from telebot import types

bot = telebot.TeleBot('7676825171:AAFvsruijy_YBxZHFQd4e-MshvzVCUpkYXI')

menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
loggs = types.KeyboardButton("Логи бота")
menu.add(loggs)

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "Прибыль! Только прибыль!", reply_markup=menu)
    bot.send_photo(message.chat.id, photo=open('backtest_images/xrp.png', 'rb'))

@bot.message_handler(commands=['money'])
def text_message(message):
    bot.send_message(message.chat.id, "Ало, бизнес? Да-да деньги", reply_markup=menu)

@bot.message_handler(content_types=['text'])
def text_messages(message):
    if message.text == "Логи бота":
        bot.send_message(message.chat.id, "Отчет формируется...", reply_markup=menu)
        bot.send_document(message.chat.id, open(r'futures_bot_loggs.log', 'rb'))

bot.infinity_polling()