import configparser

from venv import create
from telethon import TelegramClient, events
from py3cw.request import Py3CW
from singlebot import SingleBot
from multibot import MultiBot

# Read configuration
config = configparser.ConfigParser()
config.read('config.ini')

# Main code
p3cw = Py3CW(key=config['commas']['key'], secret=config['commas']['secret'])
client = TelegramClient('session/anon', config['telegram']['api_id'], config['telegram']['api_hash'])

def parse_tg(raw_text):
    return raw_text.split('\n')

def tg_data(text_lines):
    data = {}

    # Make sure the message is a signal
    if len(text_lines) == 6:
        token = text_lines[1].replace('#', '')
        action = text_lines[2].replace('BOT_', '')
        volatility_score = text_lines[3].replace('Volatility Score ', '')
        priceaction_score = text_lines[4].replace('Price Action Score ', '')
        symrank = text_lines[5].replace('SymRank #', '')
        data = {
            "pair": config['trading']['market'] + "_" + token,
            "action": action,
            "volatility": volatility_score,
            "price_action": priceaction_score,
            "symrank": symrank
        }
        
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
    error, data = p3cw.request(
        entity="accounts",
        action="",
        additional_headers={'Forced-Mode': config['trading']['trade_mode']}
    )

    for accounts in data:
        if accounts['exchange_name'] == config['trading']['exchange']:
            account = accounts['id']

    return account

def deal_data():
    error, data = p3cw.request(
        entity="deals",
        action="",
        action_id=account_data(),
        additional_headers={'Forced-Mode': config['trading']['trade_mode']},
        payload={
            "scope": "active"
        }
    )

    return len(data)
    
    
@client.on(events.NewMessage(chats="3C Quick Stats"))
async def my_event_handler(event):
    print('New signals incoming...')
    tg_output = tg_data(parse_tg(event.raw_text))
    bot_output = bot_data()
    account_output = account_data()
    deal_output = deal_data()
    bot = MultiBot(tg_output, bot_output, account_output, deal_output, config, p3cw)

    if config['dcabot'].getboolean('single'):
        bot = SingleBot(tg_output, bot_output, account_output, deal_output, config, p3cw)

    bot.trigger()


async def main():
    print('Refreshing cache...')
    async for dialog in client.iter_dialogs():
        print(dialog.name, 'has ID', dialog.id)
    print('\n*** 3CQS Bot started ***')


with client:
    client.loop.run_until_complete(main())

client.start()
client.run_until_disconnected()