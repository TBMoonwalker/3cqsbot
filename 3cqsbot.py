import argparse
import re
import logging
import asyncio
import sys
import os
import portalocker
import math

from telethon import TelegramClient, events
from py3cw.request import Py3CW
from singlebot import SingleBot
from multibot import MultiBot
from signals import Signals
from logging.handlers import RotatingFileHandler
from config import Config


######################################################
#                       Config                       #
######################################################
attributes = Config()


parser = argparse.ArgumentParser(
    description="3CQSBot bringing 3CQS signals to 3Commas."
)
parser.add_argument(
    "-l",
    "--loglevel",
    metavar="loglevel",
    type=str,
    nargs="?",
    default="info",
    help="loglevel during runtime - use info, debug, warning, ...",
)

args = parser.parse_args()

######################################################
#                        Init                        #
######################################################

# Initialize 3Commas API client
p3cw = Py3CW(
    key=attributes.get("key"),
    secret=attributes.get("secret"),
    request_options={
        "request_timeout": attributes.get("timeout", 3),
        "nr_of_retries": attributes.get("retries", 5),
        "retry_backoff_factor": attributes.get("delay_between_retries", 2.0),
    },
)

# Initialize Telegram API client
client = TelegramClient(
    attributes.get("sessionfile", "tgsesssion"),
    attributes.get("api_id"),
    attributes.get("api_hash"),
)

# Set logging facility
if attributes.get("debug", False):
    loglevel = "DEBUG"
else:
    loglevel = getattr(logging, args.loglevel.upper(), None)

# Set logging output
# Thanks to @M1cha3l for improving logging output
handler = logging.StreamHandler()

if attributes.get("log_to_file", False):
    handler = logging.handlers.RotatingFileHandler(
        attributes.get("log_file_path", "3cqsbot.log"),
        maxBytes=attributes.get("log_file_size", 200000),
        backupCount=attributes.get("log_file_count", 5),
    )

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=loglevel,
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[handler],
)

# Initialize global variables
asyncState = type("", (), {})()
asyncState.btcbool = True
asyncState.botswitch = True
asyncState.chatid = ""
asyncState.fh = 0
asyncState.accountData = {}
asyncState.pairData = []

######################################################
#                     Methods                        #
######################################################
def run_once():
    asyncState.fh = open(os.path.realpath(__file__), "r")
    try:
        portalocker.lock(asyncState.fh, portalocker.LOCK_EX | portalocker.LOCK_NB)
    except:
        sys.exit(
            "Another 3CQSBot is already running in this directory - please use another one!"
        )


# Check for single instance run
run_once()


def parse_tg(raw_text):
    return raw_text.split("\n")


def tg_data(text_lines):
    # Make sure the message is a signal
    if len(text_lines) == 7:
        data = {}
        signal = text_lines[1]
        token = text_lines[2].replace("#", "")
        action = text_lines[3].replace("BOT_", "")
        volatility_score = text_lines[4].replace("Volatility Score ", "")

        if volatility_score == "N/A":
            volatility_score = 9999999

        priceaction_score = text_lines[5].replace("Price Action Score ", "")

        if priceaction_score == "N/A":
            priceaction_score = 9999999

        symrank = text_lines[6].replace("SymRank #", "")

        if symrank == "N/A":
            symrank = 9999999

        if signal == "SymRank Top 30":
            signal = "top30"
        elif signal == "SymRank Top 100 Triple Tracker":
            signal = "triple100"
        elif signal == "Hyper Volatility":
            signal = "hvol"
        else:
            signal = "xvol"

        data = {
            "signal": signal,
            "pair": attributes.get("market") + "_" + token,
            "action": action,
            "volatility": float(volatility_score),
            "price_action": float(priceaction_score),
            "symrank": int(symrank),
        }
    # Symrank list
    elif len(text_lines) == 17:
        pairs = {}
        data = []

        if "Volatile" not in text_lines[0]:
            for row in text_lines:
                if ". " in row:
                    # Sort the pair list from Telegram
                    line = re.split(" +", row)
                    pairs.update(
                        {int(line[0][:-1]): line[1], int(line[2][:-1]): line[3]}
                    )

            allpairs = dict(sorted(pairs.items()))
            data = list(allpairs.values())

    else:
        data = False

    return data


def bot_data():
    # Gets information about existing bot in 3Commas
    botlimit = attributes.get("system_bot_value", 300)
    pages = math.ceil(botlimit / 100)
    bots = []

    for page in range(1, pages + 1):
        if page == 1:
            offset = 0
        else:
            offset = (page - 1) * 100

        error, data = p3cw.request(
            entity="bots",
            action="",
            additional_headers={"Forced-Mode": attributes.get("trade_mode")},
            payload={"limit": 100, "offset": offset},
        )

        if error:
            sys.exit(error["msg"])
        else:
            if data:
                bots += data
            else:
                break

    return bots


def account_data():
    # Gets information about the used 3commas account (paper or real)
    account = {}

    error, data = p3cw.request(
        entity="accounts",
        action="",
        additional_headers={"Forced-Mode": attributes.get("trade_mode")},
    )

    if error:
        logging.debug(error["msg"])
        sys.tracebacklimit = 0
        sys.exit("Problem fetching account data from 3commas api - stopping!")
    else:
        for accounts in data:
            if accounts["name"] == attributes.get("account_name"):
                account.update({"id": str(accounts["id"])})
                account.update({"market_code": str(accounts["market_code"])})

        if "id" not in account:
            sys.tracebacklimit = 0
            sys.exit(
                "Account with name '" + attributes.get("account_name") + "' not found"
            )

    return account


def pair_data(account):
    pairs = []

    error, data = p3cw.request(
        entity="accounts",
        action="market_pairs",
        additional_headers={"Forced-Mode": attributes.get("trade_mode")},
        payload={"market_code": account["market_code"]},
    )

    if error:
        logging.debug(error["msg"])
        sys.tracebacklimit = 0
        sys.exit("Problem fetching pair data from 3commas api - stopping!")

    error, blacklist_data = p3cw.request(
        entity="bots",
        action="pairs_black_list"
    )

    if error:
        logging.debug(error["msg"])
        sys.tracebacklimit = 0
        sys.exit("Problem fetching pairs blacklist data from 3commas api - stopping!")
    
    for pair in data:
        if attributes.get("market") in pair:
            if pair not in attributes.get("token_denylist") and pair not in blacklist_data["pairs"]:
                pairs.append(pair)

    return pairs


async def symrank():
    logging.info(
        "Sending /symrank command to 3C Quick Stats on Telegram to get new pairs"
    )
    await client.send_message(asyncState.chatid, "/symrank")


async def botswitch():
    while True:
        if not asyncState.btcbool and not asyncState.botswitch:
            asyncState.botswitch = True
            logging.debug("Botswitch: " + str(asyncState.botswitch))
            if attributes.get("single"):
                logging.info("Not activating old single bots (waiting for new signals)")
            else:
                # Send new top 30 for activating the multibot
                await symrank()

        elif asyncState.btcbool and asyncState.botswitch:
            asyncState.botswitch = False
            logging.debug("Botswitch: " + str(asyncState.botswitch))
            if attributes.get("single"):
                bot = SingleBot([], bot_data(), {}, attributes, p3cw, logging)
                bot.disable(bot_data(), True)
            else:
                bot = MultiBot([], bot_data(), {}, 0, attributes, p3cw, logging)
                bot.disable()

        else:
            logging.debug("Nothing do to")
            logging.debug("Botswitch: " + str(asyncState.botswitch))

        await asyncio.sleep(60)


def _handle_task_result(task: asyncio.Task) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        pass  # Task cancellation should not be logged as an error.
    except Exception:  # pylint: disable=broad-except
        logging.exception(
            "Exception raised by task = %r",
            task,
        )


@client.on(events.NewMessage(chats=attributes.get("chatroom", "3C Quick Stats")))
async def my_event_handler(event):

    if (
        asyncState.btcbool
        and attributes.get("btc_pulse", False)
        and not attributes.get("ext_botswitch", False)
    ):
        logging.info(
            "New 3CQS signal not processed - 3cqsbot stopped because of BTC downtrend"
        )
    else:

        tg_output = tg_data(parse_tg(event.raw_text))
        logging.debug("TG msg: " + str(tg_output))
        bot_output = bot_data()
        account_output = asyncState.accountData
        pair_output = asyncState.pairData

        if tg_output and not isinstance(tg_output, list):

            logging.info("New 3CQS signal '" + str(tg_output["signal"]) + "' incoming...")

            # Check if it is the right signal
            if (
                tg_output["signal"] == attributes.get("symrank_signal")
                or attributes.get("symrank_signal") == "all"
            ):

                # Choose multibot or singlebot
                if attributes.get("single"):
                    bot = SingleBot(
                        tg_output, bot_output, account_output, attributes, p3cw, logging
                    )
                else:
                    bot = MultiBot(
                        tg_output,
                        bot_output,
                        account_output,
                        pair_output,
                        attributes,
                        p3cw,
                        logging,
                    )
                    # Every signal triggers a new multibot deal
                    bot.trigger(triggeronly=True)

                # Trigger bot if limits passed
                if tg_output["volatility"] != 0 and tg_output["pair"] in pair_output:
                    if (
                        tg_output["volatility"]
                        >= attributes.get("volatility_limit_min", 0.1)
                        and tg_output["volatility"]
                        <= attributes.get("volatility_limit_max", 100)
                        and tg_output["price_action"]
                        >= attributes.get("price_action_limit_min", 0.1)
                        and tg_output["price_action"]
                        <= attributes.get("price_action_limit_max", 100)
                        and tg_output["symrank"]
                        >= attributes.get("symrank_limit_min", 1)
                        and tg_output["symrank"]
                        <= attributes.get("symrank_limit_max", 100)
                    ) or tg_output["action"] == "STOP":

                        bot.trigger()

                    else:
                        logging.info(
                            "Start signal for "
                            + str(tg_output["pair"])
                            + " with symrank: "
                            + str(tg_output["symrank"])
                            + ", volatility: "
                            + str(tg_output["volatility"]) 
                            + " and price action: "
                            + str(tg_output["price_action"])
                            + " not meeting config filter limits - signal ignored"
                        )
                else:
                    logging.info(
                        str(tg_output["pair"])
                        + " is not traded on '"
                        + attributes.get("account_name")
                        + "'"
                    )
            else:
                logging.info(
                    "Signal ignored because '"
                    + attributes.get("symrank_signal")
                    + "' is configured"
                )

        elif tg_output and isinstance(tg_output, list):
            if not attributes.get("single"):
                # Create or update multibot with pairs from "/symrank"
                bot = MultiBot(
                    tg_output,
                    bot_output,
                    account_output,
                    pair_output,
                    attributes,
                    p3cw,
                    logging,
                )
                bot.create()
            else:
                logging.debug(
                    "Ignoring /symrank call, because we're running in single mode!"
                )


async def main():
    signals = Signals(logging)
    asyncState.accountData = account_data()
    asyncState.pairData = pair_data(asyncState.accountData)

    logging.debug("Refreshing cache...")

    user = await client.get_participants("The3CQSBot")
    asyncState.chatid = user[0].id

    logging.info("*** 3CQS Bot started ***")

    if not attributes.get("single"):
        await symrank()

    if attributes.get("btc_pulse", False) and not attributes.get(
        "ext_botswitch", False
    ):
        btcbooltask = client.loop.create_task(signals.getbtcbool(asyncState))
        btcbooltask.add_done_callback(_handle_task_result)
        switchtask = client.loop.create_task(botswitch())
        switchtask.add_done_callback(_handle_task_result)

        while True:
            await btcbooltask
            await switchtask
    elif attributes.get("btc_pulse", False) and attributes.get("ext_botswitch", False):
        sys.tracebacklimit = 0
        sys.exit("Check config.ini, btc_pulse and ext_botswitch both set to true - not allowed")


with client:
    client.loop.run_until_complete(main())

client.start()

if not attributes.get("btc_pulse", False):
    client.run_until_disconnected()
