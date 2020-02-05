# -*- coding: utf-8 -*-
import os
from datetime import datetime

import telebot
import random
from flask import Flask, request
from pymongo import MongoClient

token = os.environ['POKER_RANDOM_TOKEN']
bot = telebot.TeleBot(token)

server = Flask(__name__)


client = MongoClient(os.environ['MONGO_URL'], 63367)
db = client[os.environ['MONGODB']]
db.authenticate(os.environ['MONGO_USER'], os.environ['MONGO_PASSWORD'])
players_collection = db['lepers']

@bot.message_handler(commands=['start', 'help'])
def handle_start_help(message):
    result = "Привет! Я бот-рандомизаторов игроков в покер!\r\nЯ поддерживаю следующие команды:"
    result += "\r\n/start - запустить бота"
    result += "\r\n/setplayers <список игроков> - установить актуальный список игроков для жеребьевки (ввод через пробел)"
    result += "\r\n/getplayers - посмотреть актуальный список"
    result += "\r\n/randomize <количество игроков> - выбрать случайным образом заданное количество игроков из актуального списка"
    result += "\r\n/help - посмотреть справку"
    bot.send_message(message.chat.id, result)


@bot.message_handler(commands=['randomize'])
def handle_randomize(message):
    chat_id = message.chat.id
    username = message.from_user.username if message.from_user.username else ''
    bound_to = message.chat.title if message.chat.type == 'group' else username
    players_by_group = {players_group['chat_id']: players_group for players_group in players_collection.find({})}
    if chat_id not in players_by_group:
        new_element = {'chat_id': message.chat.id,
                       'bound_to': bound_to,
                       'last_edit_date': datetime.fromtimestamp(message.date),
                       'last_edited_by': username,
                       'members': [],
                       'number': 0}
        players_by_group[chat_id] = new_element
        players_collection.insert_one(new_element)

    msg = message.text[len('/randomize'):]
    if msg.startswith('@'):
        if msg.startswith('@PokerRandomBot ') or msg == '@PokerRandomBot':
            msg = msg[len('@PokerRandomBot '):]
        else:
            msg = '0'
    members = players_by_group[message.chat.id]['members']
    if len(members) == 0:
        bot.send_message(message.chat.id, 'Актуальный список пуст. Я не смогу ничего нарандомить.')
        return
    if not msg:
        number = players_by_group[message.chat.id]['number']
        if not number:
            bot.send_message(message.chat.id, 'Нужно задать количество участников.')
            return
    else:
        try:
            number = int(msg)
        except:
            bot.send_message(message.chat.id, 'Что это за число? Не пойму.')
            return
        if not number:
            bot.send_message(message.chat.id, 'Ну нет, так нельзя.')
            return
    new_values = {
        'last_edit_date': datetime.fromtimestamp(message.date),
        'last_edited_by': username,
        'number': number
    }
    players_collection.update_one({'chat_id': chat_id}, {'$set': new_values}, upsert=False)
    members = [member for member in members if member]
    if len(members) < number:
        bot.send_message(message.chat.id, 'Позвольте, но я не могу выбрать %s из %s.' % (number, len(members)))
        return
    players = random.sample(members, number)
    losers = set(members).difference(players)
    players = [player for player in members if player in players]
    players_enumerated = ['%s. %s' % (i + 1, player) for i, player in enumerate(players)]
    result = 'Рандом выбрал следующих игроков:\r\n%s' % '\r\n'.join(players_enumerated)
    result += '\r\nПоздравим счастливчиков!🌟'
    if len(losers) > 0:
        losers = [player for player in members if player in losers]
        players_enumerated = ['%s. %s' % (i + 1, player) for i, player in enumerate(losers)]
        result += '\r\n\r\nЖдут следующего шанса:\r\n%s' % '\r\n'.join(players_enumerated)
    bot.send_message(message.chat.id, result)


@bot.message_handler(commands=['setplayers'])
def handle_set_players(message):
    chat_id = message.chat.id
    username = message.from_user.username if message.from_user.username else ''
    bound_to = message.chat.title if message.chat.type == 'group' else username
    players_by_group = {players_group['chat_id']: players_group for players_group in players_collection.find({})}
    if chat_id not in players_by_group:
        new_element = {'chat_id': message.chat.id,
                       'bound_to': bound_to,
                       'last_edit_date': datetime.fromtimestamp(message.date),
                       'last_edited_by': username,
                       'members': [],
                       'number': 0}
        players_collection.insert_one(new_element)

    msg = message.text[len('/setplayers'):]
    if msg.startswith('@'):
        if msg.startswith('@PokerRandomBot ') or msg == '@PokerRandomBot':
            msg = msg[len('@PokerRandomBot '):]
        else:
            bot.send_message(message.chat.id, 'Непонятно. Давайте еще раз.')
            return
    else:
        msg = msg[1:]
    if not msg:
        bot.send_message(message.chat.id, 'Укажите, пожалуйста, хотя бы одного человека.')
        return
    players = msg.split(' ')
    players_copy = players
    players = []
    for player in players_copy:
        if player not in players:
            players.append(player)
    if len(players) > 100:
        bot.send_message(message.chat.id, 'Вас слишком много! Дайте мне поменьше людей, пожалуйста.')
        return
    if max([len(player) for player in players]) > 32:
        bot.send_message(message.chat.id, 'Кажется, у кого-то слишком длинное имя. Попробуйте еще раз...')
        return
    new_values = {
        'last_edit_date': datetime.fromtimestamp(message.date),
        'last_edited_by': username,
        'members': players
    }
    players_collection.update_one({'chat_id': chat_id}, {'$set': new_values}, upsert=False)
    bot.send_message(message.chat.id, 'Готово! Актуальный список обновлён.')


@bot.message_handler(commands=['getplayers'])
def handle_get_players(message):
    players_by_group = {players_group['chat_id']: players_group for players_group in players_collection.find({})}
    if message.chat.id not in players_by_group:
        username = message.from_user.username if message.from_user.username else ''
        bound_to = message.chat.title if message.chat.type == 'group' else username
        new_element = {'chat_id': message.chat.id,
                       'bound_to': bound_to,
                       'last_edit_date': datetime.fromtimestamp(message.date),
                       'last_edited_by': username,
                       'members': [],
                       'number': 0}
        players_by_group[message.chat.id] = new_element
        players_collection.insert_one(new_element)
    players = players_by_group[message.chat.id]['members']
    if len(players) == 0:
        result = 'В актуальном списке никого нет'
    else:
        players_enumerated = ['%s. %s' % (i + 1, player) for i, player in enumerate(players)]
        result = 'Актуальный список:\r\n%s' % '\r\n'.join(players_enumerated)
    bot.send_message(message.chat.id, result)


@server.route('/%s' % token, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200

@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=os.environ['POKER_HEROKU_URL'] + token)
    return "!", 200

port = int(os.environ.get('PORT', 5000))
server.run(host="0.0.0.0", port=port)