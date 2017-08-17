#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Simple Bot to reply to Telegram messages
# This program is dedicated to the public domain under the CC0 license.
"""
This Bot uses the Updater class to handle the bot.
First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
from telegram import (ReplyKeyboardMarkup,InlineKeyboardMarkup,InlineKeyboardButton)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler,CallbackQueryHandler)
import logging
import re
import datetime

from config import *
#watson imports
import json
from watson_developer_cloud import NaturalLanguageUnderstandingV1
import watson_developer_cloud.natural_language_understanding.features.v1 as \
    Features

#import google map
import googlemaps
from datetime import datetime

#wikipedia import
import wikipedia

gmaps = googlemaps.Client(key=GOOGLE_KEY)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)



LANG,WIKIPEDIA,WATSON = range(3)


#watson init
natural_language_understanding = NaturalLanguageUnderstandingV1(
version='2017-02-27',
username=WATSON_USER_NAME,
password=WATSON_PASSWORD)


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    update.message.reply_text("Hi! I am a Bot which answer your questions to help you find what you are looking \n"
                                "If you want to ask me something type /ask and your question")


def help(bot, update):
    update.message.reply_text('Help!')


def echo(bot, update):
    user = update.message.from_user
    text = update.message.text
    #print update.message
    
    if re.search('^(hi)$',text.lower()):
        update.message.reply_text('Hi '+user.first_name+'\nHow can I help you?')
    elif re.search('^(okay|ok|)$',text.lower()):
        update.message.reply_text('You got it '+user.first_name)
    elif len(text) < 10:
        update.message.reply_text('The sentence is too short to understand what you want')
    else:
        ask_watson(bot,update)

def ask_watson(bot, update):
    user = update.message.from_user
    try:
        response = natural_language_understanding.analyze(text = update.message.text,features=[Features.Categories()])
    except:
        update.message.reply_text('The sentence is too short to understand what you want')
        return
    #print response
    
    result = json.loads(json.dumps(response, indent=2))
    if len(result['categories']) > 0:
        update.message.reply_text(result['categories'])
    


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))

# def wiki_lang(bot, update):
    
#     reply_keyboard = [['en','de','fr','es','tr']]
#     update.message.reply_text('which language would you prefer?',
#         reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
#     return LANG

def set_wiki_lang(bot,update):    
    text = update.message.text
    user = update.message.from_user
    lang = user.language_code.split('-')[0]    
    ask_wikipedia(bot,update)
    
def change_wiki_lang(bot,update):
    lang = update.message.text[11:13].lower()
    print lang
    try:
        wikipedia.set_lang(lang)
    except:
        print "Language can not be set "+ lang


def ask_wikipedia(bot, update): 
    text = update.message.text[11:]  
    try:
        result = wikipedia.page(title=text,auto_suggest=False)
    except wikipedia.exceptions.DisambiguationError as wed:
        update.message.reply_text('which one did you mean?',
        #reply_markup=InlineKeyboardMarkup([[wed.options]]))
        reply_markup=ReplyKeyboardMarkup([["/wikipedia " + s for s in wed.options]], one_time_keyboard=True, resize_keyboard=True,selective=True))        
        return
    except wikipedia.exceptions.PageError as wep:
        update.message.reply_text('The Article could not be found in Wikipedia that you are looking for')
        print wep
        return
    update.message.reply_text(result.content[:300]+'...weiterlesen\n'+result.url)

def build_menu(buttons,
               n_cols,
               header_buttons,
               footer_buttons):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu

def richtung(str):
    if "<=>" in str:
        str = str.replace('<','')
    if "<=" in str:
        spl = str.split('<=')
        return {"fr":spl[1],"to":spl[0]}
    if "=>" in str:
        spl = str.split('=>')
        return {"fr":spl[0],"to":spl[1]}

def googlemap_mode(bot,update):
    global fr,to,message
    text = update.message.text
    ab = 10 #googlemap
    button_list = [
        [
            InlineKeyboardButton("driving",callback_data="driving"),
            InlineKeyboardButton("walking",callback_data="walking")
        ],
        [
            InlineKeyboardButton("bicycling",callback_data="bicycling"),
            InlineKeyboardButton("transit",callback_data="transit")
        ]
    ]

    try:
        fr = richtung(text[ab:])["fr"]
        to = richtung(text[ab:])["to"]
    except:
        print "Ziel und Startpunkte dürfen nicht leer sein"
        return
    print fr,to
    message = update.message.reply_text
    update.message.reply_text("Which transport mode would you prefer?",
                            reply_markup=InlineKeyboardMarkup(button_list)
    )




def googlemap(bot,update):     
    #text = update.message.text
    answer = update.callback_query.data
    print answer
    print update.message
    
    now = datetime.now()
    try:
        directions_result = gmaps.directions(fr,
                                        to,
                                        mode=answer,
                                        departure_time=now)
    except:
        print "something went wrong"
        return
    
    try:
        weg = json.loads(json.dumps(directions_result,indent=2))[0]
    except:
        print 'something went wrong. the data is too big'
        return
    way = ""
    for step in weg['legs'][0]['steps']:
        way += '=> '+step['html_instructions']+' '+step['distance']['text']+'\n'
        print step['html_instructions']+' '+step['distance']['text']+'\n\n'
    print update
    #update.message.reply_text(way,parse_mode='HTML')
    way = way.replace('div','b')
    message(way,parse_mode='HTML')
    print way

def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(TELEGRAM_TOKEN)

    

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            LANG: [MessageHandler(Filters.text, set_wiki_lang)],
            WIKIPEDIA: [MessageHandler(Filters.text,ask_wikipedia)],         
        },

        fallbacks=[CommandHandler('echo', echo)]
    )

    dp.add_handler(conv_handler)

    # on different commands - answer in Telegram
    # dp.add_handler(CommandHandler("start", start))
    # dp.add_handler(CommandHandler("help", help))
    # dp.add_handler(CommandHandler("ask", ask))
    dp.add_handler(CommandHandler("wikipedia", set_wiki_lang))
    dp.add_handler(CommandHandler("watson", ask_watson))
    dp.add_handler(CommandHandler("wiki_lang", change_wiki_lang))
    dp.add_handler(CommandHandler("googlemap", googlemap_mode))
    dp.add_handler(CallbackQueryHandler(googlemap))
    # dp.add_handler(CommandHandler("wiki_lang",set_wiki_lang))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
