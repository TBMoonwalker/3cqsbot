import argparse
import logging
import asyncio
import socketio
import sys
import os
import portalocker
import math

from py3cw.request import Py3CW
from singlebot import SingleBot
from multibot import MultiBot
from conditions import Conditions
from filters import Filters
from logging.handlers import RotatingFileHandler
from config import Config


######################################################
#                       Config                       #
######################################################

# load configuration file
attributes = Config()

# Parse and interpret options
parser = argparse.ArgumentParser(
    description="3CQSBot bringing 3CQS signals to 3Commas."
)

parser.add_argument("-d", "--datadir", help="data directory to use", type=str)
args = parser.parse_args()
if args.datadir:
    datadir = args.datadir
else:
    datadir = os.getcwd()

args = parser.parse_args()

# Set logging facility
if attributes.get("debug", False):
    loglevel = "DEBUG"
    wslogger = True
else:
    loglevel = "INFO"
    wslogger = False

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

# Logging level for socketio


logging.info(f"Loaded configuration from '{datadir}/config.ini'")

######################################################
#                        Init                        #
######################################################

# Initialize 3Commas API client
p3cw = Py3CW(
    key=attributes.get("key"),
    secret=attributes.get("secret"),
    request_options={
        "request_timeout": attributes.get("timeout", 10),
        "nr_of_retries": attributes.get("retries", 20),
        "retry_backoff_factor": attributes.get("delay_between_retries", 5.0),
    },
)

# Initialize socket.io async client
sio = socketio.AsyncClient(
    logger=logging,
    engineio_logger=logging,
    reconnection=False,
    reconnection_delay=attributes.get("websocket_reconnection_delay", 10000),
    reconnection_attempts=attributes.get("websocket_reconnection_attempts", 0),
)

# Initialize global variables
asyncState = type("", (), {})()
asyncState.btc_downtrend = False
asyncState.bot_active = True
asyncState.fh = 0
asyncState.accountData = {}
asyncState.pairData = []
asyncState.multiInit = "empty"
asyncState.tasks = []
asyncState.fgi = -1
asyncState.fgi_downtrend = False
asyncState.fgi_allows_trading = False
asyncState.fgi_time_until_update = 1

######################################################
#                     Methods                        #
######################################################
def __run_once():
    asyncState.fh = open(os.path.realpath(__file__), "r")
    try:
        portalocker.lock(asyncState.fh, portalocker.LOCK_EX | portalocker.LOCK_NB)
    except:
        sys.exit(
            "Another 3CQSBot is already running in this directory - please use another one!"
        )


# Check for single instance run
__run_once()


def __bot_data():

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


def __account_data():

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
                account.update({"exchange": str(accounts["exchange_name"])})

        if "id" not in account:
            sys.tracebacklimit = 0
            sys.exit(
                "Account with name '" + attributes.get("account_name") + "' not found"
            )

    return account


def __pair_data(data):
    if data["symbol"] not in asyncState.pairData:
        asyncState.pairData.append(data["symbol"])


def __bot_type(signal, pair_output):
    bot_output = __bot_data()

    if attributes.get("single"):
        bot = SingleBot(
            signal,
            bot_output,
            asyncState.accountData,
            attributes,
            p3cw,
            logging,
        )
    else:
        bot = MultiBot(
            signal,
            bot_output,
            asyncState.accountData,
            pair_output,
            attributes,
            p3cw,
            logging,
        )

    return bot


async def __bot_switch():

    while True:

        if not asyncState.btc_downtrend:

            if not asyncState.bot_active:
                asyncState.bot_active = True

                logging.debug(
                    "bot_active before enabling: " + str(asyncState.bot_active)
                )
                logging.info("BTC uptrending")

                if attributes.get("single"):
                    logging.info(
                        "Not activating old single bots (waiting for new signals)"
                    )
                else:
                    bot = MultiBot([], __bot_data(), {}, 0, attributes, p3cw, logging)
                    bot.enable()

        else:

            if asyncState.bot_active:
                asyncState.bot_active = False

                logging.debug("bot_active: " + str(asyncState.bot_active))

                if attributes.get("single"):
                    bot = SingleBot([], __bot_data(), {}, attributes, p3cw, logging)
                    bot.disable(__bot_data(), True)
                else:
                    bot = MultiBot([], __bot_data(), {}, 0, attributes, p3cw, logging)
                    bot.disable()

        await asyncio.sleep(60)


def __handle_task_result(task: asyncio.Task) -> None:

    try:
        task.result()
    except asyncio.CancelledError:
        pass  # Task cancellation should not be logged as an error.
    except Exception:  # pylint: disable=broad-except
        logging.exception(
            "Exception raised by task = %r",
            task,
        )


async def __websocket_connect():
    while True:
        if not sio.connected:
            logging.debug("Websocket initial connection/reconnection attempt")
            try:
                await sio.connect(
                    attributes.get("websocket_url"),
                    headers={
                        "api-key": attributes.get("websocket_key"),
                        "user-agent": "3CQS Signal Client/"
                        + attributes.get("websocket_version"),
                    },
                    transports=["websocket", "polling"],
                    socketio_path="/stream/v1/signals",
                )
            except:
                logging.debug("Websocket connection attempt failed - will retry")
        else:
            logging.debug("Websocket still connected - no reconnect necessary")
        await sio.sleep(30)


@sio.event
async def connect_error():
    logging.info("error from websocket server, trying to reconnect")


@sio.event
async def connect():
    logging.debug("connection established")


@sio.event
async def disconnect():
    logging.info("disconnected from websocket server")


@sio.on("*")
async def catch_all(event, data):
    logging.debug("Event: " + str(event))


@sio.on("signal")
async def my_message(data):

    filters = Filters(data, attributes, asyncState.accountData, logging)

    if data:

        logging.info("New 3CQS signal '" + str(data["signal_name"]) + "' incoming...")

        # Right signal?
        if filters.signal():

            bot = __bot_type(data, [data["symbol"]])

            # Check for stop signal
            if data["signal"] == "BOT_STOP":
                logging.debug("Stop signal received!")
                bot.trigger()
            else:

                # Continue only if we can trade the right signal on the configured exchange
                if (
                    filters.exchange()
                    and filters.whitelist()
                    and filters.topcoin()
                    and filters.volatility()
                    and filters.price()
                    and filters.symrank()
                    and not filters.denylist()
                ):

                    logging.debug("Websocket signal " + str(data))

                    if not attributes.get("single"):

                        # Create initial pairlist for multibot
                        pair_output = [data["symbol"]]

                        # Check if Multibot exist and if not fill initial pairs
                        if asyncState.multiInit == "empty" and not bot.bot():
                            # Minimum of two pairs is needed - stop Initialization afterwards
                            if len(asyncState.pairData) < 2:
                                logging.info(
                                    "Still filling initial pairs for multibot ...."
                                )
                                __pair_data(data)
                            else:
                                logging.info("Initial pairs for multibot filled.")
                                asyncState.multiInit = "filled"

                        # Create new Multibot
                        if asyncState.multiInit == "filled":
                            bot = __bot_type(data, asyncState.pairData)
                            logging.debug("Bot create")
                            logging.debug(str(asyncState.pairData))

                            # Enable new multibot only on btc uptrend
                            if bot.create() and not asyncState.btc_downtrend:
                                # Bot object needs to be created again, to gather newly created Multibot
                                bot = __bot_type(data, asyncState.pairData)
                                bot.enable()
                            else:
                                logging.info(
                                    "Multibot created, but not activated. BTC is in downtrend!"
                                )

                            asyncState.multiInit = "initialized"

                    # Trigger bot if limits passed and pair is traded on the configured exchange
                    if asyncState.btc_downtrend:
                        # Continue to update Multibot pairlist in downtrend
                        if not attributes.get("single"):
                            logging.debug("Add new pair to multibot")
                            bot.trigger(triggeronly=True)
                    else:
                        logging.debug("Trigger bot")
                        bot.trigger()


async def main():
    conditions = Conditions(logging)
    asyncState.accountData = __account_data()

    logging.info("*** 3CQS Bot started ***")

    # Connect to 3CQS websocket
    websocket = asyncio.create_task(__websocket_connect())
    websocket.add_done_callback(__handle_task_result)
    asyncState.tasks.append(websocket)
    # await __websocket_connect()

    # Start background tasks for conditions
    # BTC-Pulse
    if attributes.get("btc_pulse", False):
        btc_pulse = asyncio.create_task(conditions.btcpulse(asyncState))
        btc_pulse.add_done_callback(__handle_task_result)

        botswitch = asyncio.create_task(__bot_switch())
        botswitch.add_done_callback(__handle_task_result)

        asyncState.tasks.append(btc_pulse)
        asyncState.tasks.append(botswitch)

    # FGI
    if attributes.get("fearandgreed", False):
        fgi_task = asyncio.create_task(
            conditions.get_fgi(
                asyncState,
                attributes.get("fgi_ema_fast", 9),
                attributes.get("fgi_ema_slow", 50),
            )
        )
        fgi_task.add_done_callback(__handle_task_result)

        asyncState.tasks.append(fgi_task)

    if asyncState.tasks:
        await asyncio.wait(asyncState.tasks)
    else:
        await sio.wait()


if __name__ == "__main__":
    asyncio.run(main())
