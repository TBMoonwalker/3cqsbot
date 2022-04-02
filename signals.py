import yfinance as yf
import numpy as np
import asyncio
import math
import re

from pycoingecko import CoinGeckoAPI
from tenacity import retry, wait_fixed
from functools import lru_cache, wraps
from time import monotonic_ns


class Signals:
    def __init__(self, logging):
        self.logging = logging

    # Credits goes to https://gist.github.com/Morreski/c1d08a3afa4040815eafd3891e16b945
    def timed_lru_cache(
        _func=None, *, seconds: int = 600, maxsize: int = 128, typed: bool = False
    ):
        """Extension of functools lru_cache with a timeout

        Parameters:
        seconds (int): Timeout in seconds to clear the WHOLE cache, default = 10 minutes
        maxsize (int): Maximum Size of the Cache
        typed (bool): Same value of different type will be a different entry

        """

        def wrapper_cache(f):
            f = lru_cache(maxsize=maxsize, typed=typed)(f)
            f.delta = seconds * 10**9
            f.expiration = monotonic_ns() + f.delta

            @wraps(f)
            def wrapped_f(*args, **kwargs):
                if monotonic_ns() >= f.expiration:
                    f.cache_clear()
                    f.expiration = monotonic_ns() + f.delta
                return f(*args, **kwargs)

            wrapped_f.cache_info = f.cache_info
            wrapped_f.cache_clear = f.cache_clear
            return wrapped_f

        # To allow decorator to be used without arguments
        if _func is None:
            return wrapper_cache
        else:
            return wrapper_cache(_func)

    @staticmethod
    @timed_lru_cache(seconds=10800)
    def cgexchanges(exchange, id):
        cg = CoinGeckoAPI()
        exchange = cg.get_exchanges_tickers_by_id(id=exchange, coin_ids=id)

        return exchange

    @staticmethod
    @timed_lru_cache(seconds=10800)
    def cgvalues(rank):
        cg = CoinGeckoAPI()
        market = []

        if rank <= 250:
            pages = 1
        else:
            pages = math.ceil(rank / 250)

        for page in range(1, pages + 1):
            page = cg.get_coins_markets(vs_currency="usd", page=page, per_page=250)
            for entry in page:
                market.append(entry)

        return market

    def topvolume(self, id, volume, exchange):
        # Check if topcoin has enough volume
        volume_target = True

        if volume > 0:

            exchange = self.cgexchanges(exchange, id)

            self.logging.debug(self.cgvalues.cache_info())

            for target in exchange["tickers"]:
                if (
                    target["target"] == "USDT"
                    and target["converted_volume"]["btc"] >= volume
                ):
                    volume_target = True
                    break
                else:
                    volume_target = False

        return volume_target

    def topcoin(self, pairs, rank, volume, exchange):

        market = self.cgvalues(rank)

        self.logging.debug(self.cgvalues.cache_info())
        self.logging.info(
            "Applying CG's Top coin filter settings: marketcap <= "
            + str(rank)
            + " with daily BTC volume >= "
            + str(volume)
            + " on "
            + str(exchange)
        )

        if isinstance(pairs, list):
            self.logging.info(
                str(len(pairs))
                + " Symrank pair(s) BEFORE Top coin filter: "
                + str(pairs)
            )
            pairlist = []
            for pair in pairs:
                for symbol in market:
                    coin = pair
                    if (
                        coin.lower() in symbol["symbol"]
                        and int(symbol["market_cap_rank"]) <= rank
                    ):
                        # Check if topcoin has enough volume
                        if self.topvolume(symbol["id"], volume, exchange):
                            pairlist.append(pair)
                            break
        else:
            self.logging.info("Symrank pair BEFORE Top coin filter: " + str(pairs))
            pairlist = ""
            coin = re.search("(\w+)_(\w+)", pairs).group(2)

            for symbol in market:
                if (
                    coin.lower() in symbol["symbol"]
                    and int(symbol["market_cap_rank"]) <= rank
                ):
                    # Check if topcoin has enough volume
                    if self.topvolume(symbol["id"], volume, exchange):
                        pairlist = pairs
                        break

        if not pairlist:
            self.logging.info(str(pairs) + " not ranging under CG's Top coins")
        else:
            if isinstance(pairlist, str):
                self.logging.info(str(pairlist) + " matching with CG's Top coins")
            else:
                self.logging.info(
                    str(len(pairlist))
                    + " Symrank pair(s) AFTER Top coin filter: "
                    + str(pairlist)
                )

        return pairlist

    # Credits goes to @IamtheOnewhoKnocks from
    # https://discord.gg/tradealts
    def ema(self, data, period, smoothing=2):
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
    def btctechnical(self, symbol):
        btcusdt = yf.download(
            tickers=symbol, period="6h", interval="5m", progress=False
        )
        if len(btcusdt) > 0:
            btcusdt = btcusdt.iloc[:, :5]
            btcusdt.columns = ["Time", "Open", "High", "Low", "Close"]
            btcusdt = btcusdt.astype(float)
            btcusdt["EMA9"] = self.ema(btcusdt["Close"], 9)
            btcusdt["EMA50"] = self.ema(btcusdt["Close"], 50)
            btcusdt["per_5mins"] = (np.log(btcusdt["Close"].pct_change() + 1)) * 100
            btcusdt["percentchange_15mins"] = (
                np.log(btcusdt["Close"].pct_change(3) + 1)
            ) * 100
        else:
            raise IOError("Downloading YFinance chart broken, retry....")

        return btcusdt

    # Credits goes to @IamtheOnewhoKnocks from
    # https://discord.gg/tradealts
    async def getbtcbool(self, asyncState):

        self.logging.info("Starting btc pulse")

        while True:
            btcusdt = self.btctechnical("BTC-USD")
            # if EMA 50 > EMA9 or <-1% drop then the sleep mode is activated
            # else bool is false and while loop is broken
            if (
                btcusdt.percentchange_15mins[-1] < -1
                or btcusdt.EMA50[-1] > btcusdt.EMA9[-1]
            ):
                self.logging.info(
                    "BTC pulse signaling Downtrend. Waiting 5m more to confirm Downtrend."
                )

                # after 5mins getting the latest BTC data to see if it has had a sharp rise in previous 5 mins
                await asyncio.sleep(300)
                btcusdt = self.btctechnical("BTC-USD")

                # this is the golden cross check fast moving EMA
                # cuts slow moving EMA from bottom, if that is true then bool=false and break while loop
                if (
                    btcusdt.EMA9[-1] > btcusdt.EMA50[-1]
                    and btcusdt.EMA50[-2] > btcusdt.EMA9[-2]
                ):
                    self.logging.info("No Downtrend proved. BTC still in Uptrend")
                    asyncState.btcbool = False
                else:
                    self.logging.info(
                        "Downtrend proved. BTC pulse sending 3cqsbot to sleep"
                    )
                    asyncState.btcbool = True

            else:
                self.logging.info("BTC pulse signaling Uptrend")
                asyncState.btcbool = False

            self.logging.info("Next BTC pulse check in 5m")
            await asyncio.sleep(300)
