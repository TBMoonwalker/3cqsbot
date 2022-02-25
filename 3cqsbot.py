import configparser
import argparse
import re
import logging
import asyncio

from random import randint
from telethon import TelegramClient, events
from py3cw.request import Py3CW
from helpers.singlebot import SingleBot
from helpers.multibot import MultiBot
from helpers.signals import Signals

######################################################
#                       Config                       #
######################################################
config = configparser.ConfigParser()
config.read('config/config.ini')

parser = argparse.ArgumentParser(description='3CQSBot bringing 3CQS signals to 3Commas.')
parser.add_argument('-l', '--loglevel',
                       metavar='loglevel',
                       type=str,
                       nargs="?",
                       default="info",
                       help='loglevel during runtime - use info, debug, warning, ...')

args = parser.parse_args()

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

loglevel = getattr(logging, args.loglevel.upper(), None)

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=loglevel,
    datefmt='%Y-%m-%d %H:%M:%S')

# Initialize variables
asyncState = type('', (), {})()
asyncState.btcbool = True
asyncState.botswitch = True

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
        data = []

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
        data = False
    
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


async def symrank():
    while True:
        if asyncState.botswitch:
            logging.info("Calling Symrank to get new pairs")
            await client.send_message(asyncState.chatid, '/symrank')
        await asyncio.sleep(randint(1800,3600))

async def botswitch():
    
    while True:
        if (not asyncState.btcbool and
            not asyncState.botswitch):
            logging.debug("Activate Bot")
            asyncState.botswitch = True
            if config['dcabot'].getboolean('single'):
                logging.info("Not activating old single bots (waiting for new signals.")
            else:
                # Send new top 30 for activating the multibot
                logging.debug("Calling for new symrank stats")
                await client.send_message(asyncState.chatid, '/symrank')
        elif (asyncState.btcbool and
            asyncState.botswitch):
            logging.debug("Deactivate Bot")
            asyncState.botswitch = False
            if config['dcabot'].getboolean('single'):
                bot = SingleBot([], bot_data(), {}, 0, config, p3cw, logging)
                bot.disable(bot_data(), True)
            else:
                bot = MultiBot([], bot_data(), {}, 0, config, p3cw, logging)
                bot.disable()
                  
        else:
            logging.debug("Nothing do to")

        await asyncio.sleep(60)
    
    
@client.on(events.NewMessage(chats=config['telegram']['chatroom']))
async def my_event_handler(event):
    
    if (asyncState.btcbool and
        config['trading'].getboolean('btc_pulse')):
        logging.info("Bot stopped - no new signals processed")
    else:

        logging.debug('New signals incoming...')

        tg_output = tg_data(parse_tg(event.raw_text))
        bot_output = bot_data()
        account_output = account_data()
        pair_output = pair_data()

        if tg_output and not isinstance(tg_output, list):
            if config['dcabot'].getboolean('single'):
                bot = SingleBot(tg_output, bot_output, account_output, config, p3cw, logging)
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
                    logging.info("Trading limits reached. Deal not placed.")
            else:
                logging.info("Token " + tg_output['pair'] + " is not traded on " + config['trading']['exchange'])
        elif tg_output and isinstance(tg_output, list):
            if not config['dcabot'].getboolean('single'):
                # Create or update multibot with pairs from "/symrank"
                bot = MultiBot(tg_output, bot_output, account_output, pair_output, config, p3cw, logging)
                bot.create()
            else:
                logging.debug("Ignoring /symrank call, because we're running in single mode!")


async def main():
    signals = Signals(logging)
    
    logging.debug('Refreshing cache...')
    
    async for dialog in client.iter_dialogs():
        if dialog.name == "3C Quick Stats":
            asyncState.chatid = dialog.id
        
    logging.info('*** 3CQS Bot started ***')
    
    
    if (config['trading'].getboolean('btc_pulse') and
        not config['dcabot'].getboolean('single')):
        btcbooltask =  client.loop.create_task(signals.getbtcbool(asyncState))
        switchtask = client.loop.create_task(botswitch())
        symranktask = client.loop.create_task(symrank())

        while True:
            await symranktask
            await btcbooltask
            await switchtask
    
    elif (not config['dcabot'].getboolean('single') and
          not config['trading'].getboolean('btc_pulse')):
        
        symranktask = client.loop.create_task(symrank())
        
        while True:
            await symranktask
            

with client:
    client.loop.run_until_complete(main())

client.start()

if (not config['trading'].getboolean('btc_pulse') and
    config['dcabot'].getboolean('single')):
    client.run_until_disconnected()