import configparser
import re
import logging
import itertools

from venv import create
from collections import OrderedDict
from telethon import TelegramClient, events
from py3cw.request import Py3CW
from singlebot import SingleBot
from multibot import MultiBot

######################################################
#                       Config                       #
######################################################
config = configparser.ConfigParser()
config.read('config.ini')

######################################################
#                        Init                        #
######################################################
p3cw = Py3CW(
    key=config['commas']['key'], 
    secret=config['commas']['secret'])

client = TelegramClient(
    config['telegram']['sessionfile'], 
    config['telegram']['api_id'], 
    config['telegram']['api_hash'])

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

######################################################
#                     Methods                        #
######################################################
def parse_tg(raw_text):
    return raw_text.split('\n')


def tg_data(text_lines):
    # Make sure the message is a signal
    if len(text_lines) == 6:
        data = {}
        token = text_lines[1].replace('#', '')
        action = text_lines[2].replace('BOT_', '')
        volatility_score = text_lines[3].replace('Volatility Score ', '')
        if volatility_score == "N/A":
            volatility_score = 9999999
        priceaction_score = text_lines[4].replace('Price Action Score ', '')
        if priceaction_score == "N/A":
            priceaction_score = 9999999
        symrank = text_lines[5].replace('SymRank #', '')
        if symrank == "N/A":
            symrank = 9999999
        data = {
            "pair": config['trading']['market'] + "_" + token,
            "action": action,
            "volatility": float(volatility_score),
            "price_action": float(priceaction_score),
            "symrank": int(symrank)
        }

    elif len(text_lines) == 17:
        pairs = {}

        if "Volatile" not in text_lines[0]:
            for row in text_lines:
                if ". " in row:
                    # Sort the pair list from Telegram
                    line = re.split(" +",row)
                    pairs.update({
                        int(line[0][:-1]): line[1],
                        int(line[2][:-1]): line[3]
                    })
            
            allpairs = dict(sorted(pairs.items()))
            data = list(allpairs.values())

    else:
        data = []
    
    return data


def bot_data():
    # Gets information about existing bot in 3Commas
    error, data = p3cw.request(
        entity="bots",
        action="",
        additional_headers={'Forced-Mode': config['trading']['trade_mode']}
    )

    return data


def account_data():
    # Gets information about the used 3commas account (paper or real)
    account = {}

    error, data = p3cw.request(
        entity="accounts",
        action="",
        additional_headers={'Forced-Mode': config['trading']['trade_mode']}
    )

    for accounts in data:
        if accounts['exchange_name'] == config['trading']['exchange']:
            account.update({'id': str(accounts['id'])})
            account.update({'market_code': str(accounts['market_code'])})

    return account


def pair_data():
    pairs = []
    account = account_data()

    error, data = p3cw.request(
        entity="accounts",
        action="market_pairs",
        additional_headers={'Forced-Mode': config['trading']['trade_mode']},
        payload={
            "market_code": account['market_code']
        }
    )

    for pair in data:
        if config['trading']['market'] in pair:
            pairs.append(pair)

    return pairs


def deal_data():
    account = account_data()
    deals = []

    error, data = p3cw.request(
        entity="deals",
        action="",
        action_id=account['id'],
        additional_headers={'Forced-Mode': config['trading']['trade_mode']},
        payload={
            "limit": 1000,
            "scope": "active"
        }
    )

    if error:
        logging.error(error['msg'])
    else:
        for deal in data:
            if (config['dcabot']['prefix'] + "_" +  config['trading']['market']) in deal['bot_name']:
                deals.append(deal['bot_name'])
    
    logging.debug(deals)
    logging.debug("Deal count: " + str(len(deals)))
    
    return len(deals)
    
    
@client.on(events.NewMessage(chats=config['telegram']['chatroom']))
async def my_event_handler(event):
    tg_output = tg_data(parse_tg(event.raw_text))
    logging.debug('New signals incoming...')
    bot_output = bot_data()
    account_output = account_data()
    pair_output = pair_data()

    if tg_output and not isinstance(tg_output, list):
        if config['dcabot'].getboolean('single'):
            deal_output = deal_data()
            bot = SingleBot(tg_output, bot_output, account_output, deal_output, config, p3cw, logging)
        else:
            bot = MultiBot(tg_output, bot_output, account_output, pair_output, config, p3cw, logging)
            # Every signal triggers a new multibot deal
            bot.trigger(triggeronly=True)
     
        # Trigger bot if limits passed
        if (tg_output['volatility'] != 0 and
            tg_output['pair'] in pair_output):
            if ((tg_output['volatility'] <= config['trading'].getfloat('volatility_limit') and 
                tg_output['price_action'] <= config['trading'].getfloat('price_action_limit') and
                tg_output['symrank'] <= config['trading'].getint('symrank_limit')) or
                tg_output['action'] == 'STOP'):

                bot.trigger()

            else:
                logging.debug("Trading limits reached. Deal not placed.")
        else:
            logging.debug("Token is not traded on " + config['trading']['exchange'])
    else:
        if not config['dcabot'].getboolean('single'):
            # Create initial multibot with pairs from "/symrank"
            bot = MultiBot(tg_output, bot_output, account_output, pair_output, config, p3cw, logging)
            bot.create()
        else:
            logging.debug("Ignoring /symrank call, because we're running in single mode!")


async def main():
    logging.debug('Refreshing cache...')
    async for dialog in client.iter_dialogs():
        if dialog.name == "3C Quick Stats":
            chatid = dialog.id
        
    logging.info('\n*** 3CQS Bot started ***')
    
    if not config['dcabot'].getboolean('single'):
        await client.send_message(chatid, '/symrank')


with client:
    client.loop.run_until_complete(main())

client.start()
client.run_until_disconnected()