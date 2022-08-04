import argparse
import asyncio
import json
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from threading import Thread
from time import sleep, time

import numpy as np
import portalocker
import requests
import yfinance as yf
from babel.dates import format_timedelta
from babel.numbers import format_currency
from numpy import true_divide
from py3cw.request import Py3CW
from telethon import TelegramClient, events
from tenacity import retry, wait_fixed

from config import Config
from logger import Logger, NotificationHandler
from multibot import MultiBot
from signals import Signals
from singlebot import SingleBot

######################################################
#                       Config                       #
######################################################

# load configuration file
attributes = Config()

program = Path(__file__).stem

# Parse and interpret options
parser = argparse.ArgumentParser(description="3CQSBot bringing 3CQS signals to 3Commas")

parser.add_argument("-d", "--datadir", help="data directory to use", type=str)
args = parser.parse_args()
if args.datadir:
    datadir = args.datadir
else:
    datadir = os.getcwd()

# Handle timezone
if hasattr(time, "tzset"):
    os.environ["TZ"] = attributes.get("timezone", "Europe/Berlin")
    time.tzset()

# Init notification handler
notification = NotificationHandler(
    program,
    attributes.get("notifications", False),
    attributes.get("notify-urls", []),
)

# Initialise logging
logging = Logger(
    datadir,
    program,
    notification,
    attributes.get("logrotate", 7),
    attributes.get("debug", False),
    attributes.get("notifications", False),
)

logging.info(f"Loaded configuration from '{datadir}/config.ini'")

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

# Initialize global variables
asyncState = type("", (), {})()
asyncState.btc_downtrend = False
asyncState.bot_active = True
asyncState.first_topcoin_call = True
asyncState.fgi = -1
asyncState.fgi_downtrend = False
asyncState.fgi_allows_trading = True
asyncState.fgi_time_until_update = 1
asyncState.dca_conf = "dcabot"
asyncState.chatid = ""
asyncState.fh = 0
asyncState.account_data = {}
asyncState.pair_data = []
asyncState.symrank_success = False
asyncState.multibot = {}
asyncState.receive_signals = False

######################################################
#                     Methods                        #
######################################################


def single_instance_check():
    asyncState.fh = open(os.path.realpath(__file__), "r")
    try:
        portalocker.lock(asyncState.fh, portalocker.LOCK_EX | portalocker.LOCK_NB)
    except:
        sys.exit(
            "Another 3CQSBot is already running in this directory - please use another one!"
        )


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

        if signal == "SymRank Top 100 Triple Tracker":
            signal = "triple100"
        elif signal == "SymRank Top 100 Quadruple Tracker (BETA)":
            signal = "quadruple100"
        elif signal == "SymRank Top 250 Quadruple Tracker (BETA)":
            signal = "quadruple250"
        elif signal == "SymRank Top 30":
            signal = "top30"
        elif signal == "Super Volatility":
            signal = "svol"
        elif signal == "Super Volatility Double Tracker":
            signal = "svoldouble"
        elif signal == "Hyper Volatility":
            signal = "hvol"
        elif signal == "Hyper Volatility Double Tracker":
            signal = "hvoldouble"
        elif signal == "Ultra Volatility":
            signal = "uvol"
        elif signal == "X-Treme Volatility":
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
    # too many requests or other commands
    else:
        data = False

    return data


def bot_data():

    # Gets information about existing bots in 3Commas
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
        logging.error(error["msg"])
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


def pair_data(account, interval_sec):

    while True:
        try:
            pairs = []
            asyncState.pair_data = []

            error, data = p3cw.request(
                entity="accounts",
                action="market_pairs",
                additional_headers={"Forced-Mode": attributes.get("trade_mode")},
                payload={"market_code": account["market_code"]},
            )

            if error:
                logging.error(error["msg"])
                sys.tracebacklimit = 0
                sys.exit("Problem fetching pair data from 3commas api - stopping!")

            error, blacklist_data = p3cw.request(
                entity="bots", action="pairs_black_list"
            )

            if error:
                logging.error(error["msg"])
                sys.tracebacklimit = 0
                sys.exit(
                    "Problem fetching pairs blacklist data from 3commas api - stopping!"
                )

            for pair in data:
                if attributes.get("market") in pair:
                    if (
                        pair not in attributes.get("token_denylist", [])
                        and pair not in blacklist_data["pairs"]
                    ):
                        pairs.append(pair)

            asyncState.pair_data = pairs
            logging.info(
                str(len(pairs))
                + " tradeable and non-blacklisted "
                + attributes.get("market")
                + " pairs for account '"
                + account["id"]
                + "' on '"
                + account["market_code"]
                + "' imported. Next update in "
                + format_timedelta(interval_sec, locale="en_US"),
                True,
            )
            notification.send_notification()
            sleep(interval_sec)
        except Exception as err:
            logging.error("Exception raised by thread pair_data: {}".format(err))
            sleep(interval_sec)


# Credits go to @M1ch43l
# Adjust DCA settings dynamically according to social sentiment: greed = aggressive DCA, neutral = moderate DCA, fear = conservative DCA
@retry(wait=wait_fixed(10))
def requests_call(method, url, timeout):
    response = []
    try:
        response = requests.request(method, url, timeout=timeout)
    except Exception as e:
        raise IOError(
            "Fear and greed index API actually down, retrying in 10s, Error is:" + e
        )
    return response


def get_fgi(ema_fast, ema_slow):

    logging.info(
        "Using crypto fear and greed index (FGI) from alternative.me for changing 3cqsbot DCA settings to defensive, moderate or aggressive",
        True,
    )

    while True:
        try:
            url = "https://api.alternative.me/fng/?limit=100"
            fgi_values = []
            fgi_ema_fast = []
            fgi_ema_slow = []
            response = requests_call("GET", url, 5)
            raw_data = json.loads(response.text)
            for i in range(len(raw_data["data"])):
                fgi_values.insert(0, int(raw_data["data"][i]["value"]))
            fgi_ema_fast = ema(fgi_values, ema_fast)
            fgi_ema_slow = ema(fgi_values, ema_slow)
            time_until_update = int(raw_data["data"][0]["time_until_update"])
            fmt = "{0.hours}h:{0.minutes}m:{0.seconds}s"
            # Web response sometimes slow, so proceed only if time_until_update for next web update > 10 sec
            if time_until_update < 0:
                time_until_update = 10
            elif time_until_update > 10:
                logging.info(
                    "Current FGI: {:d}".format(fgi_values[-1])
                    + " - time till next update: "
                    + format_timedelta(time_until_update, locale="en_US"),
                    True,
                )
                asyncState.fgi = fgi_values[-1]

                if fgi_ema_fast[-1] < fgi_ema_slow[-1]:
                    asyncState.fgi_downtrend = True
                    output_str = "FGI-EMA{0:d}: {1:.1f}".format(
                        ema_fast, fgi_ema_fast[-1]
                    ) + " less than FGI-EMA{:d}: {:.1f}".format(
                        ema_slow, fgi_ema_slow[-1]
                    )
                    if round(fgi_ema_fast[-1], 1) < round(fgi_ema_fast[-2], 1):
                        logging.info(
                            "FGI in the downtrend zone - "
                            + output_str
                            + " - Fast EMA falling compared to yesterday"
                            + " ("
                            + str(round(fgi_ema_fast[-2], 1))
                            + ")",
                            True,
                        )
                    else:
                        logging.info(
                            "FGI in the downtrend zone - "
                            + output_str
                            + " - Fast EMA equal or rising compared to yesterday"
                            " (" + str(round(fgi_ema_fast[-2], 1)) + ")",
                            True,
                        )
                else:
                    asyncState.fgi_downtrend = False
                    output_str = "FGI-EMA{0:d}: {1:.1f}".format(
                        ema_fast, fgi_ema_fast[-1]
                    ) + " greater than FGI-EMA{:d}: {:.1f}".format(
                        ema_slow, fgi_ema_slow[-1]
                    )
                    if round(fgi_ema_fast[-1], 1) < round(fgi_ema_fast[-2], 1):
                        logging.info(
                            "FGI in the uptrend zone - "
                            + output_str
                            + "  - Fast EMA falling compared to yesterday"
                            " (" + str(round(fgi_ema_fast[-2], 1)) + ")",
                            True,
                        )
                    else:
                        logging.info(
                            "FGI in the uptrend zone - "
                            + output_str
                            + "  - Fast EMA equal or rising compared to yesterday"
                            " (" + str(round(fgi_ema_fast[-2], 1)) + ")",
                            True,
                        )

                # FGI downtrend = true if FGI drops >= 10 between actual and last day
                # OR >= 15 between actual and second to last day
                if ((fgi_values[-2] - fgi_values[-1]) >= 10) or (
                    (fgi_values[-3] - fgi_values[-1]) >= 15
                ):
                    asyncState.fgi_downtrend = True
                    logging.info(
                        "FGI actual/yesterday/before yesterday: {:d}/{:d}/{:d}".format(
                            fgi_values[-1], fgi_values[-2], fgi_values[-3]
                        ),
                        True,
                    )
                    logging.info(
                        "Drop > 10 between actual vs. yesterday or drop > 15 between actual vs. before yesterday",
                        True,
                    )

                asyncState.fgi_time_until_update = time_until_update

            notification.send_notification()
            # request FGI once per day, because is is calculated only once per day
            sleep(time_until_update)
        except Exception as err:
            logging.error("Exception raised by thread get_fgi: {}".format(err))
            sleep(3600)


# Credits goes to @IamtheOnewhoKnocks from
# https://discord.gg/tradealts
def ema(data, period, smoothing=2):
    # Calculate EMA without dependency for TA-Lib
    ema = [sum(data[:period]) / period]

    for price in data[period:]:
        ema.append(
            (price * (smoothing / (1 + period)))
            + ema[-1] * (1 - (smoothing / (1 + period)))
        )

    for i in range(period - 1):
        ema.insert(0, np.nan)

    return ema


# Credits goes to @IamtheOnewhoKnocks from
# https://discord.gg/tradealts
@retry(wait=wait_fixed(2))
def btctechnical(symbol):
    btcusdt = yf.download(tickers=symbol, period="6h", interval="5m", progress=False)
    if len(btcusdt) > 0:
        btcusdt = btcusdt.iloc[:, :5]
        btcusdt.columns = ["Time", "Open", "High", "Low", "Close"]
        btcusdt = btcusdt.astype(float)
        btcusdt["EMA9"] = ema(btcusdt["Close"], 9)
        btcusdt["EMA50"] = ema(btcusdt["Close"], 50)
        btcusdt["per_5mins"] = (np.log(btcusdt["Close"].pct_change() + 1)) * 100
        btcusdt["percentchange_15mins"] = (
            np.log(btcusdt["Close"].pct_change(3) + 1)
        ) * 100
    else:
        raise IOError("Downloading YFinance chart broken, retry....")

    return btcusdt


# Credits goes to @IamtheOnewhoKnocks from
# https://discord.gg/tradealts
def get_btcpulse(interval_sec):

    logging.info("Starting btc-pulse", True)
    i = round(3600 / interval_sec, 0)
    while True:
        try:
            ## inform every hour on TG and after first start
            if i >= round(3600 / interval_sec, 0):
                TG_inform = True
                i = 0
            else:
                TG_inform = False
            logging.debug(
                "btc-pulse: counter i (3600/ sleep interval_sec): "
                + str(i)
                + "   TG_inform: "
                + str(TG_inform)
                + "   interval_sec: "
                + str(interval_sec)
            )

            btcusdt = btctechnical("BTC-USD")
            # if EMA 50 > EMA9 or <-1% drop then the sleep mode is activated
            # else bool is false and while loop is broken
            if (
                btcusdt.percentchange_15mins[-1] < -1
                or btcusdt.EMA9[-1] < btcusdt.EMA50[-1]
            ):
                # after 5mins getting the latest BTC data to see if it has had a sharp rise in previous 5 mins
                logging.info(
                    "BTC drop more than -1% within 15 min  or  5min EMA9  less than  EMA50. Waiting for confirmation in "
                    + format_timedelta(interval_sec, locale="en_US")
                )
                sleep(interval_sec)
                i += 1
                btcusdt = btctechnical("BTC-USD")

                # this is the golden cross check fast moving EMA
                # cuts slow moving EMA from bottom, if that is true then bool=false and break while loop
                if (
                    btcusdt.EMA9[-1] > btcusdt.EMA50[-1]
                    and btcusdt.EMA9[-2] < btcusdt.EMA50[-2]
                ):
                    # Inform about BTC trend changes
                    if asyncState.btc_downtrend:
                        TG_inform = True
                    logging.info(
                        "btc-pulse signaling UPtrend (golden cross check) - actual BTC price: "
                        + format_currency(btcusdt["Close"][-1], "USD", locale="en_US")
                        + "   EMA9-5m: "
                        + format_currency(btcusdt.EMA9[-1], "USD", locale="en_US")
                        + "  greater than  EMA50-5m: "
                        + format_currency(btcusdt.EMA50[-1], "USD", locale="en_US")
                        + " and BTC price 5 minutes before: "
                        + format_currency(btcusdt[-2])
                        + "   EMA9-5m: "
                        + format_currency(btcusdt.EMA9[-2], "USD", locale="en_US")
                        + "  less than  EMA50-5m: "
                        + format_currency(btcusdt.EMA50[-2], "USD", locale="en_US"),
                        TG_inform,
                    )
                    asyncState.btc_downtrend = False
                    TG_inform = False
                else:
                    # Inform about BTC trend changes
                    if not asyncState.btc_downtrend:
                        TG_inform = True
                    logging.info(
                        "btc-pulse signaling DOWNtrend - actual BTC price: "
                        + format_currency(btcusdt["Close"][-1], "USD", locale="en_US")
                        + "   EMA9-5m: "
                        + format_currency(btcusdt.EMA9[-1], "USD", locale="en_US")
                        + "  less than  EMA50-5m: "
                        + format_currency(btcusdt.EMA50[-1], "USD", locale="en_US"),
                        TG_inform,
                    )
                    asyncState.btc_downtrend = True
                    TG_inform = False
            else:
                # Inform about BTC trend changes
                if asyncState.btc_downtrend:
                    TG_inform = True
                logging.info(
                    "btc-pulse signaling UPtrend - actual BTC price: "
                    + format_currency(btcusdt["Close"][-1], "USD", locale="en_US")
                    + "   EMA9-5m: "
                    + format_currency(btcusdt.EMA9[-1], "USD", locale="en_US")
                    + "  greater than  EMA50-5m: "
                    + format_currency(btcusdt.EMA50[-1], "USD", locale="en_US"),
                    TG_inform,
                )
                asyncState.btc_downtrend = False
                TG_inform = False

            logging.info(
                "Next btc-pulse check in "
                + format_timedelta(interval_sec, locale="en_US")
            )
            notification.send_notification()
            sleep(interval_sec)
            i += 1
        except Exception as err:
            logging.error("Exception raised by thread get_btcpulse: {}".format(err))
            sleep(interval_sec)
            i += 1


def fgi_dca_conf_change(interval_sec):

    while True:
        try:
            if asyncState.fgi >= attributes.get(
                "fgi_min", 0, "fgi_defensive"
            ) and asyncState.fgi <= attributes.get("fgi_max", 30, "fgi_defensive"):
                asyncState.dca_conf = "fgi_defensive"

            if asyncState.fgi >= attributes.get(
                "fgi_min", 31, "fgi_moderate"
            ) and asyncState.fgi <= attributes.get("fgi_max", 60, "fgi_moderate"):
                asyncState.dca_conf = "fgi_moderate"

            if asyncState.fgi >= attributes.get(
                "fgi_min", 61, "fgi_aggressive"
            ) and asyncState.fgi <= attributes.get("fgi_max", 100, "fgi_aggressive"):
                asyncState.dca_conf = "fgi_aggressive"

            # Check if section fgi_defensive, fgi_moderate and fgi_aggressive are defined in config.ini, if not use standard settings of [dcabot]
            if (
                attributes.get("fgi_min", -1, "fgi_defensive") == -1
                or attributes.get("fgi_min", -1, "fgi_moderate") == -1
                or attributes.get("fgi_min", -1, "fgi_aggressive") == -1
            ):
                logging.info(
                    "DCA settings for [fgi_defensive], [fgi_moderate] or [fgi_aggressive] are not configured. Using standard settings of [dcabot] for all FGI values 0-100",
                    True,
                )
                asyncState.dca_conf = "dcabot"
            notification.send_notification()
            sleep(interval_sec)
        except Exception as err:
            logging.error(
                "Exception raised by thread fgi_dca_conf_change: {}".format(err)
            )
            sleep(interval_sec)


def bot_switch(interval_sec):

    # Enable FGI dependent trading
    if attributes.get("fearandgreed", False):

        fgi_thread = Thread(
            target=get_fgi,
            args=(
                attributes.get("fgi_ema_fast", 9),
                attributes.get("fgi_ema_slow", 50),
            ),
            daemon=True,
            name="Background get_fgi",
        )
        logging.debug("bot_switch: Creating get_fgi thread")
        fgi_thread.start()
        while asyncState.fgi == -1:
            sleep(1)

        fgi_dca_conf_change_thread = Thread(
            target=fgi_dca_conf_change,
            args=(3600,),  # check once per hour
            daemon=True,
            name="Background fgi_dca_conf_change",
        )
        logging.debug("bot_switch: Creating fgi_dca_conf_change thread")
        fgi_dca_conf_change_thread.start()
        while not asyncState.dca_conf in [
            "fgi_defensive",
            "fgi_moderate",
            "fgi_aggressive",
        ]:
            sleep(1)

    logging.info("DCA setting: '[" + asyncState.dca_conf + "]'", True)
    logging.info(
        "Deal mode of actual DCA setting: '" + attributes.get("deal_mode") + "'", True
    )

    # Enable btc_pulse dependent trading
    if attributes.get("btc_pulse", False):
        btcpulse_thread = Thread(
            target=get_btcpulse,
            args=(300,),  # check every 5 min
            daemon=True,
            name="Background get_btcpulse",
        )
        logging.debug("bot_switch: Creating get_btcpulse thread")
        btcpulse_thread.start()

    while True:
        try:
            logging.debug("bot_switch: begin of while loop")
            if attributes.get("fearandgreed", False):
                logging.debug("Is alive get_fgi thread: " + str(fgi_thread.is_alive()))
                logging.debug(
                    "Is alive fgi_dca_conf_change thread: "
                    + str(fgi_dca_conf_change_thread.is_alive())
                )
            if attributes.get("btc_pulse", False):
                logging.debug(
                    "Is alive get_btcpulse thread: " + str(btcpulse_thread.is_alive())
                )
            if (
                not asyncState.bot_active
                and not asyncState.btc_downtrend
                and not asyncState.fgi_downtrend
            ):

                if not asyncState.fgi_downtrend and attributes.get(
                    "fearandgreed", False
                ):
                    if asyncState.fgi >= attributes.get(
                        "fgi_trade_min", 0
                    ) and asyncState.fgi <= attributes.get("fgi_trade_max", 100):
                        logging.info(
                            "FGI inside allowed trading range ["
                            + str(attributes.get("fgi_trade_min", 0))
                            + ".."
                            + str(attributes.get("fgi_trade_max", 100))
                            + "]",
                            True,
                        )
                        asyncState.fgi_allows_trading = True

                if not asyncState.btc_downtrend or asyncState.fgi_allows_trading:
                    if attributes.get("single"):
                        asyncState.bot_active = True
                        logging.info(
                            "Single bot mode activated - waiting for pair #start signals",
                            True,
                        )
                    elif attributes.get(
                        "deal_mode", "", asyncState.dca_conf
                    ) == "signal" or attributes.get("continuous_update", False):
                        # listen continuously to 3cqs msgs on TG, avoid symrank calls
                        if asyncState.multibot == {}:
                            bot = MultiBot(
                                [],
                                bot_data(),
                                {},
                                0,
                                attributes,
                                p3cw,
                                logging,
                                asyncState,
                            )
                        else:
                            bot = MultiBot(
                                [],
                                asyncState.multibot,
                                {},
                                0,
                                attributes,
                                p3cw,
                                logging,
                                asyncState,
                            )
                        bot.enable()
                        asyncState.multibot = bot.asyncState.multibot
                        asyncState.bot_active = bot.asyncState.multibot["is_enabled"]
                        logging.info(
                            "Multi bot activated - waiting for pair #start signals",
                            True,
                        )
                    # enabling bot only after sending symrank call to avoid messing up with old pairs
                    else:
                        logging.info(
                            "Multi bot activated - using pairs from actual top30 symrank list",
                            True,
                        )
                        asyncState.symrank_success = False

            elif asyncState.bot_active and (
                asyncState.btc_downtrend or asyncState.fgi_downtrend
            ):

                if asyncState.fgi_downtrend and attributes.get("fearandgreed", False):
                    if asyncState.fgi < attributes.get(
                        "fgi_trade_min", 0
                    ) or asyncState.fgi > attributes.get("fgi_trade_max", 100):
                        logging.info(
                            "FGI downtrending or outside the allowed trading range ["
                            + str(attributes.get("fgi_trade_min", 0))
                            + ".."
                            + str(attributes.get("fgi_trade_max", 100))
                            + "]",
                            True,
                        )
                        asyncState.fgi_allows_trading = False

                if asyncState.btc_downtrend or not asyncState.fgi_allows_trading:
                    if attributes.get("single"):
                        bot = SingleBot(
                            [], bot_data(), {}, attributes, p3cw, logging, asyncState
                        )
                        # True = disable all single bots
                        bot.disable(bot_data(), True)
                        asyncState.bot_active = bot.asyncState.bot_active
                    else:
                        if asyncState.multibot == {}:
                            bot = MultiBot(
                                [],
                                bot_data(),
                                {},
                                0,
                                attributes,
                                p3cw,
                                logging,
                                asyncState,
                            )
                        else:
                            bot = MultiBot(
                                [],
                                asyncState.multibot,
                                {},
                                0,
                                attributes,
                                p3cw,
                                logging,
                                asyncState,
                            )
                        bot.disable()
                        asyncState.multibot = bot.asyncState.multibot
                        asyncState.bot_active = bot.asyncState.multibot["is_enabled"]

            else:
                logging.debug("bot_switch: Nothing do to")

            notification.send_notification()
            sleep(interval_sec)
        except Exception as err:
            logging.error("Exception raised by thread bot_switch: {}".format(err))
            logging.error("bot_switch: Sleeping for " + str(interval_sec))
            sleep(interval_sec)


def _handle_task_result(task: asyncio.Task) -> None:

    try:
        task.result()
    except asyncio.CancelledError:
        pass  # Task cancellation should not be logged as an error.
    except Exception:  # pylint: disable=broad-except
        logging.error(
            "Exception raised by task = %r",
            task,
        )


async def symrank():

    logging.info(
        "Sending /symrank command to 3C Quick Stats on Telegram to get new pairs"
    )
    while not asyncState.symrank_success:
        await client.send_message(asyncState.chatid, "/symrank")
        await asyncio.sleep(5)
        # prevent from calling the symrank command too much otherwise a timeout is caused
        if not asyncState.symrank_success:
            await asyncio.sleep(60)


@client.on(events.NewMessage(chats=attributes.get("chatroom", "3C Quick Stats")))
async def my_event_handler(event):

    tg_output = tg_data(parse_tg(event.raw_text))
    logging.debug("TG msg: " + str(tg_output))
    dealmode_signal = attributes.get("deal_mode", "", asyncState.dca_conf) == "signal"

    if tg_output and asyncState.fgi_allows_trading and asyncState.receive_signals:
        account_output = asyncState.account_data
        pair_output = asyncState.pair_data

        ##### if TG message with #START or #STOP
        if tg_output and not isinstance(tg_output, list):

            logging.info(
                "'"
                + tg_output["signal"]
                + "': "
                + tg_output["action"]
                + " signal for "
                + tg_output["pair"]
                + " incoming..."
            )

            # track time from START signal to deal creation
            if tg_output["action"] == "START":
                asyncState.latest_signal_time = datetime.utcnow()

            # Check if pair is in whitelist
            if attributes.get("token_whitelist", []):
                token_whitelisted = tg_output["pair"] in attributes.get(
                    "token_whitelist", []
                )
                logging.info(tg_output["pair"] + " in whitelist, processing signal")
            else:
                token_whitelisted = True
            if not token_whitelisted:
                logging.info("Signal ignored because pair is not whitelisted")
                return

            # Check if it is the correct symrank_signal
            if not (
                tg_output["signal"] == attributes.get("symrank_signal")
                or attributes.get("symrank_signal") == "all"
            ):
                logging.info(
                    "Signal ignored because '"
                    + attributes.get("symrank_signal")
                    + "' is configured"
                )
                return

            # Check if bot is active
            if not asyncState.bot_active and not attributes.get(
                "continuous_update", False
            ):
                logging.info("Signal not processed because 3cqsbot is disabled")
                return

            # Check if pair is tradeable
            if not tg_output["pair"] in pair_output:
                logging.info(
                    str(tg_output["pair"])
                    + " is not traded on '"
                    + attributes.get("account_name")
                    + "'"
                )
                return

            # Check if 3cqs START signal passes optional symrank criteria
            if tg_output["volatility"] != 0 and tg_output["action"] == "START":
                if not (
                    tg_output["volatility"]
                    >= attributes.get("volatility_limit_min", 0.1)
                    and tg_output["volatility"]
                    <= attributes.get("volatility_limit_max", 100)
                    and tg_output["price_action"]
                    >= attributes.get("price_action_limit_min", 0.1)
                    and tg_output["price_action"]
                    <= attributes.get("price_action_limit_max", 100)
                    and tg_output["symrank"] >= attributes.get("symrank_limit_min", 1)
                    and tg_output["symrank"] <= attributes.get("symrank_limit_max", 100)
                ):
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
                    return

            # for single and multibot: if dealmode == signal and STOP signal is sent than ignore
            if tg_output["action"] == "STOP" and dealmode_signal:
                logging.info(
                    "STOP signal ignored - not necessary when deal_mode = signal"
                )
                return

            # Attribute variables either to single or multi bot
            if attributes.get("single") or asyncState.multibot == {}:
                bot_output = bot_data()
            else:
                bot_output = asyncState.multibot
            if attributes.get("single"):
                bot = SingleBot(
                    tg_output,
                    bot_output,
                    account_output,
                    attributes,
                    p3cw,
                    logging,
                    asyncState,
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
                    asyncState,
                )

            # for multibot: if dealmode == signal and multibot is empty create/update and enable multibot before processing deals
            if (
                dealmode_signal
                and asyncState.multibot == {}
                and not attributes.get("single")
                and not tg_output["action"] == "STOP"
            ):
                bot.create()
                asyncState.multibot = bot.asyncState.multibot
                asyncState.bot_active = bot.asyncState.multibot["is_enabled"]
                asyncState.first_topcoin_call = bot.asyncState.first_topcoin_call

            # for single and multibot: function bot.trigger() handles START and STOP signals
            if asyncState.multibot != {} or attributes.get("single"):

                bot.trigger()
                if not attributes.get("single"):
                    asyncState.multibot = bot.asyncState.multibot
                    asyncState.bot_active = bot.asyncState.multibot["is_enabled"]
                else:
                    asyncState.bot_active = bot.asyncState.bot_active

        ##### if TG message is symrank list
        elif tg_output and isinstance(tg_output, list):
            if (
                not attributes.get("single")
                and not dealmode_signal
                and not asyncState.symrank_success
            ):
                asyncState.symrank_success = True
                logging.info("New symrank list incoming - updating bot", True)
                if asyncState.multibot == {}:
                    bot_output = bot_data()
                else:
                    bot_output = asyncState.multibot

                # create/update and enable multibot with pairs from "/symrank"
                bot = MultiBot(
                    tg_output,
                    bot_output,
                    account_output,
                    pair_output,
                    attributes,
                    p3cw,
                    logging,
                    asyncState,
                )
                bot.create()
                asyncState.multibot = bot.asyncState.multibot
                asyncState.bot_active = bot.asyncState.multibot["is_enabled"]
                asyncState.first_topcoin_call = bot.asyncState.first_topcoin_call
            else:
                logging.debug(
                    "Ignoring /symrank call, because we're running in single mode!"
                )

    notification.send_notification()


async def main():

    # Check for single instance run
    single_instance_check()

    signals = Signals(logging)

    ##### Initial reporting #####
    logging.info("*** 3CQS Bot started ***", True)

    user = await client.get_participants("The3CQSBot")
    asyncState.chatid = user[0].id

    logging.info("** Configuration **", True)

    asyncState.account_data = account_data()
    # Update available pair_data every 360 minutes for e.g. new blacklisted pairs or new tradable pairs
    pair_data_thread = Thread(
        target=pair_data,
        args=(
            asyncState.account_data,
            3600 * 6,
        ),
        daemon=True,
        name="Background update pair_data",
    )
    logging.debug("Creating pair_data thread")
    pair_data_thread.start()
    while not asyncState.pair_data:
        sleep(1)

    if attributes.get("single"):
        logging.info("Bot mode: 'Single Pair'", True)
    else:
        logging.info("Bot Mode: 'Multi Pair'", True)

    logging.info(
        "Listening to 3cqs signals: '" + str(attributes.get("symrank_signal")) + "'",
        True,
    )
    logging.info(
        "Topcoin filter: '" + str(attributes.get("topcoin_filter", False)) + "'", True
    )
    logging.info("BTC Pulse: '" + str(attributes.get("btc_pulse", False)) + "'", True)
    logging.info(
        "FGI Trading: '" + str(attributes.get("fearandgreed", False)) + "'", True
    )
    logging.info(
        "Continuous pair update for multibot with other deal_mode than 'signal': '"
        + str(attributes.get("continuous_update", False))
        + "'",
        True,
    )
    logging.info(
        "External/TV bot switching: '"
        + str(attributes.get("ext_botswitch", False))
        + "'",
        True,
    )
    logging.info("Quote currency: '" + str(attributes.get("market")) + "'")
    logging.info(
        "Token whitelist: '" + str(attributes.get("token_whitelist", "No")) + "'", True
    )

    # Check for inconsistencies of bot switching before starting 3cqsbot
    if attributes.get("btc_pulse", False) and attributes.get("ext_botswitch", False):
        sys.tracebacklimit = 0
        sys.exit(
            "Check config.ini: btc_pulse AND ext_botswitch both set to true - not allowed"
        )

    # Central Bot Switching module for btc_pulse and FGI
    if attributes.get("btc_pulse", False) or attributes.get("fearandgreed", False):
        bot_switch_thread = Thread(
            target=bot_switch,
            args=(60,),  # check every 60 secs
            daemon=True,
            name="Background bot_switch",
        )
        logging.debug("Creating bot_switch thread")
        bot_switch_thread.start()
        sleep(3)

    # Search and rename 3cqsbot if multipair is configured
    if asyncState.multibot == {} and not attributes.get("single"):
        bot = MultiBot(
            [],
            bot_data(),
            asyncState.account_data,
            0,
            attributes,
            p3cw,
            logging,
            asyncState,
        )
        bot.search_rename_3cqsbot()
        asyncState.multibot = bot.asyncState.multibot
        if asyncState.multibot:
            asyncState.bot_active = bot.asyncState.multibot["is_enabled"]
        else:
            asyncState.bot_active = False

    ##### Wait for TG signals of 3C Quick Stats channel #####
    sleep(3)
    logging.info("** Waiting for action **", True)
    asyncState.receive_signals = True
    notification.send_notification()

    while attributes.get("deal_mode", "", asyncState.dca_conf) != "signal":
        while (
            asyncState.fgi_allows_trading
            and not asyncState.symrank_success
            and not attributes.get("single")
        ):
            await symrank()


while True:
    try:
        client.start()
        client.loop.run_until_complete(main())
        client.run_until_disconnected()
    except Exception as err:
        logging.error("Exception raised by main programm: {}".format(err))
