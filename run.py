#!/usr/bin/python3
# -*- coding: utf-8 -*

"""
Core script of the project.
"""

import json
import uuid
import logging
import configparser
import html
import requests
import urllib
import urllib.request
import tempfile
import os, io
import subprocess
import sys
import dialogflow_v2beta1 as dialogflow
import wikipedia
import time
import datetime as dtm
from telegram import ParseMode, MessageEntity, ChatAction, ReplyKeyboardMarkup
from telegram.error import BadRequest, Unauthorized
#from telegram.ext import CommandHandler, Updater, MessageHandler, Filters, CallbackContext
from telegram.utils.helpers import escape_markdown
from google.protobuf.json_format import MessageToJson, MessageToDict, Parse
from google.cloud import vision_v1
from google.cloud.vision_v1 import types

from telegram.ext import Updater, CommandHandler, Filters, \
    MessageHandler, InlineQueryHandler, CallbackContext, ConversationHandler
import telegram
from telegram import InlineQueryResultArticle, InputTextMessageContent

from wit import Wit
from wit.wit import WitError

from urllib.request import Request, urlopen, ssl, socket

from config import TELEGRAM_TOKEN, ADMIN_CHAT_ID, DIALOGFLOW_KEY, WIT_TOKEN, LANG
from lang import NOT_UNDERSTOOD

from uuid import uuid4

#import img_rec
#from img_rec import recog

#import pymysql.cursors

#from utils import get_reply, fetch_news, topics_keyboard
'''
#from util import get_reply_id, reply_or_edit, get_text_not_in_entities, github_issues, rate_limit, rate_limit_tracker
#from telegram import ParseMode, MessageEntity, ChatAction, Update, Bot, InlineQueryResultArticle, InputTextMessageContent
from telegram import ParseMode, MessageEntity, ChatAction, Update, Bot
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CommandHandler, Updater, MessageHandler, Filters, CallbackContext
from telegram.utils.helpers import escape_markdown
'''
'''
import const
from components import inlinequeries, taghints
from const import (ENCLOSING_REPLACEMENT_CHARACTER, GITHUB_PATTERN, OFFTOPIC_CHAT_ID, OFFTOPIC_RULES,
                   OFFTOPIC_USERNAME, ONTOPIC_RULES, ONTOPIC_USERNAME, ONTOPIC_RULES_MESSAGE_LINK,
                   OFFTOPIC_RULES_MESSAGE_LINK, ONTOPIC_RULES_MESSAGE_ID,
                   OFFTOPIC_RULES_MESSAGE_ID)
'''
from gnewsclient import gnewsclient

class Getip():
    def __init__(self):
        wan_ip = self.get_wan_ip()
        lan_ip = self.get_local_ip()
    def get_wan_ip(self):
        w_ip = urlopen('http://ipecho.net/plain').read().decode('utf-8')
        #print("External IP: ", w_ip)
        self.wan_ip = w_ip
        #return w_ip
    def get_local_ip(self):
        try:
            l_ip = (socket.gethostbyname(socket.gethostname()))
            #print("Internal IP: ", l_ip)
            self.lan_ip = l_ip
        except:
            #res.configure(text='Unkown Error', fg='#red')
            self.lan_ip = 'none'

Getip1 = Getip()
srvwanip = str(Getip1.wan_ip)

topics_keyboard = ('World', 'Nation', 'Business', 'Technology', 'Entertainment', 'Sports', 'Science', 'Health')
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'vidkey.json'

result_storage_path = 'tmp'
client = vision_v1.ImageAnnotatorClient()
clientn = gnewsclient.NewsClient()


def notify_admins(message):
    for admin_id in ADMIN_CHAT_ID:
        try:
            BOT.sendMessage(admin_id, text=message)
        except (telegram.error.BadRequest, telegram.error.Unauthorized):
            logging.warning('Admin chat_id %s unreachable', admin_id)

botinfo = '''
<b>Добро пожаловать!</b>
Спросите меня что-нибудь или скажите любую фразу. Можно голосовым сообщением.
Или отправьте картинку для распознавания объектов на ней.
Или отправьте /news для получения новостей.
введите команду /wiki и запрос: Пример: /wiki машина
'''

def weather(bot, update):
    s_city = "Moscow,RU"
    city_id = 0
    appid = ""
    try:
        res = requests.get("http://api.openweathermap.org/data/2.5/find",
                           params={'q': s_city, 'type': 'like', 'units': 'metric', 'APPID': appid})
        data = res.json()
        cities = ["{} ({})".format(d['name'], d['sys']['country'])
                  for d in data['list']]
        print("city:", cities)
        city_id = data['list'][0]['id']
        print('city_id=', city_id)
    except Exception as e:
        print("Exception (find):", e)
        pass
    try:
        res = requests.get("http://api.openweathermap.org/data/2.5/weather",
                           params={'id': city_id, 'units': 'metric', 'lang': 'ru', 'APPID': appid})
        data = res.json()
        print("conditions:", data['weather'][0]['description'])
        print("temp:", data['main']['temp'])
        print("temp_min:", data['main']['temp_min'])
        print("temp_max:", data['main']['temp_max'])
        reply = "погода в Москве: " + str(data['weather'][0]['description'] + ', ' + str(data['main']['temp']))
        bot.send_message(chat_id=update.message.chat_id, text=reply)
    except Exception as e:
        print("Exception (weather):", e)
        pass

def wiki(bot, update):
    chat_id=update.message.chat_id
    query_in = str(update.message.text)
    if len(query_in.split()) == 1:
        reply = 'введите команду /wiki и запрос' + '\n' \
                + 'Пример: /wiki машина'
        bot.send_message(chat_id=chat_id, text=reply, parse_mode=ParseMode.HTML)
        return
    else:
        try:
            query_in = str(update.message.text).strip('/wiki  ')
            print(query_in)
            wikipedia.set_lang("RU")
            wiksearch = wikipedia.summary(query_in, sentences=10)
            bot.sendMessage(chat_id, wiksearch + '\n' + wikipedia.page(query_in).url)
        except Exception as e:
            bot.sendMessage(chat_id, 'Error :' + str(e))
        return 0

def start(bot, update):
    chat_id = update.message.chat_id
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    reply = botinfo
    bot.send_message(chat_id=chat_id, text=reply, parse_mode=ParseMode.HTML, disable_web_page_preview=False)
    reply1 = dialogflow_event_request('TELEGRAM_WELCOME', chat_id)
    bot.send_message(chat_id=chat_id, text=reply1)


topics_keyboard = [
        ['Top Stories', 'World', 'Nation'],
        ['Business', 'Technology', 'Entertainment'],
        ['Sports', 'Science', 'Health']
    ]
tk = str(topics_keyboard)

def news(bot, update):
    """callback function for /news handler"""
    bot.send_message(chat_id=update.message.chat_id, text="Choose a category",
                     reply_markup=ReplyKeyboardMarkup(keyboard=topics_keyboard, one_time_keyboard=True))
    #bot.send_message(chat_id=update.message.chat_id, text=text,
    #                 reply_markup=ReplyKeyboardMarkup.from_row(topics_keyboard))(one_time_keyboard=True)

def send_news(bot, update):
    reply = update.message.text
    chat_id = update.message.chat_id
    clientn.language = 'Ru'
    clientn.location = 'Russia'
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    clientn.topic = reply
    articles = clientn.get_news()[:5]
    for article in articles:
        bot.send_message(chat_id=update.message.chat_id, text=article['link'])

'''    
def tghelp(bot, update):
    chat_id = update.message.chat_id
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    reply = dialogflow_event_request('TELEGRAM_WELCOME', chat_id)
    bot.send_message(chat_id=chat_id, text=reply)
'''

'''
def subscripslist(bot, update):
    chat_id = update.message.chat_id
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    connection = pymysql.connect(host='54.189.52.114',
                                 user='ubuntu',
                                 password='',
                                 database='',
                                 cursorclass=pymysql.cursors.DictCursor)

    with connection.cursor() as cursor:
        # Read a single record
        sql = "SELECT `contactFirstName`, `contactLastName`, `phone`, `addressLine1` FROM mainbulka.customers"
        cursor.execute(sql)
        res = cursor.fetchall()
        res1 = json.JSONEncoder().encode(res)
        res2 = json.loads(res1)
        count = cursor.rowcount
        reply = ''
        i = 0
        for i in range(0, count, 1):
            reply = reply + '<b>' + res2[i]["contactFirstName"] \
                    +' ' + res2[i]["contactLastName"] +'</b>' \
                    + ':\n' + res2[i]["phone"] +'\n'\
                    + res2[i]["addressLine1"] + '\n' + '\n'
        cursor.close()
    connection.close()
    chatstr = "-485348087 76978130"
    if str(chat_id) in chatstr:
        bot.send_message(chat_id=chat_id, text=reply, parse_mode=ParseMode.HTML)
    else: bot.send_message(chat_id=chat_id, text='U R NOT ADMIN', parse_mode=ParseMode.HTML)
    #update.message.reply_text("Okay.", quote=True)
'''
'''
def productslist(bot, update):
    chat_id = update.message.chat_id
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    connection = pymysql.connect(host='54.189.52.114',
                                 user='ubuntu',
                                 password='zyrzak-kizfa4-nAcdog',
                                 database='wordpress',
                                 cursorclass=pymysql.cursors.DictCursor)

    with connection.cursor() as cursor:
        # Read a single record
        sql = "SELECT `post_title`, `post_excerpt` FROM `wp_posts` WHERE `post_type` IN ('product')"
        cursor.execute(sql)
        res = cursor.fetchall()
        res1 = json.JSONEncoder().encode(res)
        res2 = json.loads(res1)
        count = cursor.rowcount
        reply = ''
        i = 0
        for i in range(0,count,1):
            reply = reply +'<b>'+ res2[i]["post_title"] +'</b>' + ':\n' + res2[i]["post_excerpt"] + '\n'+'\n'
        #print(res3)
        # dbinfo = pymysql.Connection.close(connection)
        # out = result[0]
        # print(out)
        print(pymysql.get_client_info())
        cursor.close()
    connection.close()
    bot.send_message(chat_id=chat_id, text=reply, parse_mode=ParseMode.HTML)
    #update.message.reply_text("Okay.", quote=True)
'''

def sandwich(bot, update):
    chat_id = update.message.chat_id
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    #reply = dialogflow_event_request('TELEGRAM_WELCOME', chat_id)
    #bot.send_message(chat_id=chat_id, text=reply)
    update.message.reply_text("Okay.", quote=True)

def tghelp(bot, update):
    chat_id = update.message.chat_id
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    #reply = dialogflow_event_request('TELEGRAM_WELCOME', chat_id)
    #bot.send_message(chat_id=chat_id, text=reply)
    update.message.reply_text(
        'Спросите меня что-нибудь или скажите любую фразу. Можно голосовым сообщением.'
        'Или отправьте картинку для распознавания объектов на ней.'
        'Или отправьте /news для получения новостей.'
        ' '
        'Наш сайт [здесь](http://faceai.aihere.ru/). '
        'Присоединяйся!',
        quote=True, disable_web_page_preview=False, parse_mode=ParseMode.MARKDOWN)

def text(bot, update):
    chat_id = update.message.chat_id
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    try:
        reply = dialogflow_text_request(update.message.text, chat_id)
        try:
            audio = open("tmp/response.wav", "rb")
            bot.send_audio(chat_id=chat_id, audio=audio)
            audio.close()
            os.remove("tmp/response.wav")
        except:
            pass
    except:
        reply = "не понятно, выражайся ясно, бади"
    reply = dialogflow_text_request(update.message.text, chat_id)
    bot.send_message(chat_id=chat_id, text=reply)

def img(bot, update):
    chat_id = update.message.chat_id
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    image_id  = update.message.photo[-1].get_file()
    image_id = image_id.file_id

    bot.send_message(chat_id=chat_id, text='🔥 Analyzing image, be patient ! 🔥')

    # prepare image for downlading
    file_path = bot.get_file(image_id).file_path

    # generate image download url
    # image_url = "https://api.telegram.org/file/bot{0}/{1}".format(TELEGRAM_TOKEN, file_path)
    image_url = file_path
    print(image_url)

    # create folder to store pic temporary, if it doesnt exist
    if not os.path.exists(result_storage_path):
        os.makedirs(result_storage_path)

    # retrieve and save image
    image_name = "{0}.jpg".format(image_id)
    urllib.request.urlretrieve(image_url, "{0}/{1}".format(result_storage_path, image_name))

    #return image_name

    print(image_name)
    image_name = result_storage_path + '/'+ image_name
    print(image_name)
    #r = recog(image_name)
    #reply = out

    with io.open(os.path.join(image_name), 'rb') as image_file:
        content = image_file.read()
    # image = vision_v1.types.Image(content=content)
    image = vision_v1.Image(content=content)
    response = client.web_detection(image=image)
    annotations = response.web_detection
    res = annotations.__class__.to_json(annotations)
    dataimg = json.loads(res)
    jdump = json.dumps(res, indent=4)
    #print(dataimg["webEntities"][0]["description"])
    #print(res)
    #print(dataimg)
    #print(jdump)

    '''
    out = []
    for outi in range (0,4):
        out.append(dataimg["webEntities"][outi]["description"] + '\n' + '\n')
    '''
    out = dataimg["webEntities"][0]["description"] + '\n' + '\n'
    out = out + dataimg["webEntities"][1]["description"] + '\n' + '\n'
    out = out + dataimg["webEntities"][2]["description"] + '\n' + '\n'
    out = out + dataimg["webEntities"][3]["description"] + '\n' + '\n'

    bot.send_message(chat_id=chat_id, text=out)

    #os.remove('{0}/{1}'.format(result_storage_path, image_name))
    #image_name = save_image_from_message()

    #reply = dataimg
    #reply = dialogflow_text_request(update.message.text, chat_id)

'''
def get_image_id_from_message(bot, update):
    # there are multiple array of images, check the biggest
    return update.message.photo[len(update.message.photo) - 1].file_id
def save_image_from_message(bot, update):
    image_id = BOT.get_file(update.message.photo)

    #image_id = update.message.photo.file_id
    bot.send_message(chat_id=chat_id, text = '🔥 Analyzing image, be patient ! 🔥')

    # prepare image for downlading
    file_path = bot.get_file(image_id).file_path

    # generate image download url
    image_url = "https://api.telegram.org/file/bot{0}/{1}".format(environ['TELEGRAM_TOKEN'], file_path)
    print(image_url)

    # create folder to store pic temporary, if it doesnt exist
    if not os.path.exists(result_storage_path):
        os.makedirs(result_storage_path)

    # retrieve and save image
    image_name = "{0}.jpg".format(image_id)
    urllib.request.urlretrieve(image_url, "{0}/{1}".format(result_storage_path, image_name))

    return image_name;
'''

def voice(bot, update):
    chat_id = update.message.chat_id
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    new_file = BOT.get_file(update.message.voice.file_id)
    file_audio_from = tempfile.mkstemp(suffix=".ogg")
    file_audio_to = tempfile.mkstemp(suffix=".mp3")
    os.close(file_audio_from[0])
    os.close(file_audio_to[0])
    new_file.download(file_audio_from[1])
    ogg_to_mp3(file_audio_from[1], file_audio_to[1])
    os.remove(file_audio_from[1])
    message = wit_voice_request(file_audio_to[1])
    os.remove(file_audio_to[1])
    if message is None:
        reply = NOT_UNDERSTOOD[LANG]
    else:
        reply = dialogflow_text_request(message, chat_id)
    bot.send_message(chat_id=chat_id, text=reply)

def inline(bot, update):
    query = update.inline_query.query
    if not query:
        return
    session_id = update.inline_query.from_user.id
    dialogflow_reply = dialogflow_text_request(query, session_id)
    reply = list()
    reply.append(
        InlineQueryResultArticle(
            id=uuid.uuid4(),
            title=query.capitalize(),
            input_message_content=InputTextMessageContent(dialogflow_reply),
            description=dialogflow_reply
        )
    )
    bot.answer_inline_query(update.inline_query.id, reply)
    '''
    def inlinequery(bot, update):
        """Handle the inline query."""
        query = update.inline_query.query

        if query == "":
            return

        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Caps",
                input_message_content=InputTextMessageContent(query.upper()),
            ),
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Bold",
                input_message_content=InputTextMessageContent(
                    f"*{escape_markdown(query)}*", parse_mode=ParseMode.MARKDOWN
                ),
            ),
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Italic",
                input_message_content=InputTextMessageContent(
                    f"_{escape_markdown(query)}_", parse_mode=ParseMode.MARKDOWN
                ),
            ),
        ]

        update.inline_query.answer(results)
    '''

def dialogflow_detect_intent(query_input, session_id):
    session = DIALOGFLOW.session_path(PROJECT_ID, session_id)
    response = DIALOGFLOW.detect_intent(session=session, query_input=query_input)
    r_audio = response.output_audio
    wav_file = open("tmp/response.wav", "wb")
    wav_file.write(r_audio)
    wav_file.close()
    #q = response.query_result.intent.training_phrases[0]
    return response.query_result.fulfillment_messages[0].text.text[0]

def dialogflow_event_request(event, session_id):
    event_input = dialogflow.types.EventInput(name=event, language_code=LANG)
    query_input = dialogflow.types.QueryInput(event=event_input)
    return dialogflow_detect_intent(query_input, session_id)

def dialogflow_text_request(query, session_id):
    text_input = dialogflow.types.TextInput(text=query, language_code=LANG)
    query_input = dialogflow.types.QueryInput(text=text_input)
    return dialogflow_detect_intent(query_input, session_id)

def wit_voice_request(audio_path):
    message = None
    with open(audio_path, 'rb') as voice_file:
        try:
            reply = WIT.speech(voice_file, {'Content-Type': 'audio/mpeg3'}, None)
            message = str(reply)
        except WitError:
            logging.warning(sys.exc_info()[1])
    return message

def ogg_to_mp3(ogg_path, mp3_path):
    proc = subprocess.Popen(["ffmpeg", "-i", ogg_path,
                             "-acodec", "libmp3lame",
                             "-y", mp3_path], stderr=subprocess.PIPE)
    logging.debug(proc.stderr.read().decode())


logging.info('Program started')

# Init dialogflow
try:
    PROJECT_ID = json.load(open(DIALOGFLOW_KEY))["project_id"]
except FileNotFoundError:
    logging.fatal("Unable to retrieve the PROJECT_ID of Dialogflow")
    sys.exit(-1)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = DIALOGFLOW_KEY
DIALOGFLOW = dialogflow.SessionsClient()

# Init WIT.ai
if WIT_TOKEN:
    WIT = Wit(WIT_TOKEN)

# Init telegram
BOT = telegram.Bot(TELEGRAM_TOKEN)
UPDATER = Updater(token=TELEGRAM_TOKEN, use_context=False)
DISPATCHER = UPDATER.dispatcher
logging.info('Bot started')
notify_admins('AITALKBOT started')
notify_admins("My server: wan: " + srvwanip + ' , lan: ' + str(Getip1.lan_ip))

# set commands
UPDATER.bot.set_my_commands([
    ('/start', 'Запускает бота заново'),
    ('/help', 'Помощь в использовании бота.'),
    #('/products', 'Список товаров в продаже'),
    ('/news', 'Новости'),
    ('/wiki', 'wikipedia'),
    ('/weather', 'погода'),
])

# Add telegram handlers
START_HANDLER = CommandHandler('start', start)
DISPATCHER.add_handler(START_HANDLER)

TGHELP_HANDLER = CommandHandler('help', tghelp)
DISPATCHER.add_handler(TGHELP_HANDLER)

NEWS_HANDLER = CommandHandler('news', news)
DISPATCHER.add_handler(NEWS_HANDLER)

WIKI_HANDLER = CommandHandler('wiki', wiki)
DISPATCHER.add_handler(WIKI_HANDLER)

#PRODUCTS_LIST = CommandHandler('products', productslist)
#DISPATCHER.add_handler(PRODUCTS_LIST)

#SUBSCRIPTIONS_LIST = CommandHandler('subs', subscripslist)
#DISPATCHER.add_handler(SUBSCRIPTIONS_LIST)

'''
ENTRY, EXIT = range(2)
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],

    states={

        ENTRY: [CommandHandler('start', start), MessageHandler(Filters.text, fullname)],

        EXIT: [MessageHandler(Filters.photo | Filters.document, photo)],

        PHONE: [MessageHandler(Filters.contact |
                               Filters.regex('^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}$'),
                               contact_callback)]
    },

    fallbacks=[CommandHandler('cancel', cancel)]
)
DISPATCHER.add_handler(conv_handler)
'''


sandwich_handler = MessageHandler(Filters.regex(r'(?i)[\s\S]*?((sudo )?make me a sandwich)[\s\S]*?'),
                                      sandwich)
DISPATCHER.add_handler(sandwich_handler)

newnews_handler = MessageHandler(Filters.text(tk), send_news)
DISPATCHER.add_handler(newnews_handler)

WEATHER = CommandHandler('weather', weather)
DISPATCHER.add_handler(WEATHER)

img_handler = MessageHandler(Filters.photo, img)
DISPATCHER.add_handler(img_handler)

TEXT_HANDLER = MessageHandler(Filters.text, text)
DISPATCHER.add_handler(TEXT_HANDLER)

INLINE_HANDLER = InlineQueryHandler(inline)
DISPATCHER.add_handler(INLINE_HANDLER)

'''
SEARCH_HANDLER = CommandHandler('search', search)
DISPATCHER.add_handler(SEARCH_HANDLER)
'''

if WIT_TOKEN:
    VOICE_HANDLER = MessageHandler(Filters.voice, voice)
    DISPATCHER.add_handler(VOICE_HANDLER)

# Start polling and wait on idle state
UPDATER.start_polling()
UPDATER.idle()
notify_admins('Program aborted')
logging.info('Program aborted')
