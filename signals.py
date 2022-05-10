import yfinance as yf
import numpy as np
import asyncio
import math
import re
import babel.numbers
import requests
import traceback
import json
from logging import exception
from dateutil.relativedelta import relativedelta as rd

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

    def topvolume(self, id, volume, exchange, market):
        # Check if topcoin has enough volume
        volume_target = True

        if volume > 0:

            exchange = self.cgexchanges(exchange, id)

            self.logging.debug(self.cgvalues.cache_info())

            for target in exchange["tickers"]:
                converted_btc = babel.numbers.format_currency(
                    target["converted_volume"]["btc"], "", locale="en_US"
                )
                converted_usd = babel.numbers.format_currency(
                    target["converted_volume"]["usd"], "USD", locale="en_US"
                )
                btc_price = (
                    target["converted_volume"]["usd"]
                    / target["converted_volume"]["btc"]
                )
                configured_usd = babel.numbers.format_currency(
                    (volume * btc_price),
                    "USD",
                    locale="en_US",
                )
                if (
                    target["target"] == market
                    and target["converted_volume"]["btc"] >= volume
                ):
                    volume_target = True
                    self.logging.info(
                        str(target["base"])
                        + " daily volume is "
                        + converted_btc
                        + " BTC ("
                        + converted_usd
                        + ") and over the configured value of "
                        + str(volume)
                        + " BTC ("
                        + configured_usd
                        + ")"
                    )
                    break
                elif (
                    target["target"] == market
                    and target["converted_volume"]["btc"] < volume
                ):
                    volume_target = False
                    self.logging.info(
                        str(target["base"])
                        + " daily volume is "
                        + converted_btc
                        + " BTC ("
                        + converted_usd
                        + ") NOT passing the minimum daily BTC volume of "
                        + str(volume)
                        + " BTC ("
                        + configured_usd
                        + ")"
                    )
                    break
                else:
                    volume_target = False
        else:
            volume_target = True

        return volume_target

    def topcoin(self, pairs, rank, volume, exchange, trademarket):

        market = self.cgvalues(rank)

        self.logging.debug(self.cgvalues.cache_info())
        self.logging.info(
            "Applying CG's top coin filter settings: marketcap <= "
            + str(rank)
            + " with daily BTC volume >= "
            + str(volume)
            + " on "
            + str(exchange)
        )

        if isinstance(pairs, list):
            self.logging.info(
                str(len(pairs))
                + " symrank pair(s) BEFORE top coin filter: "
                + str(pairs)
            )
            pairlist = []
            for pair in pairs:
                for symbol in market:
                    coin = pair
                    if (
                        coin.lower() == symbol["symbol"]
                        and int(symbol["market_cap_rank"]) <= rank
                    ):
                        self.logging.info(
                            str(pair)
                            + " is ranked #"
                            + str(symbol["market_cap_rank"])
                            + " and has passed marketcap filter limit of #"
                            + str(rank)
                        )
                        # Check if topcoin has enough volume
                        if self.topvolume(symbol["id"], volume, exchange, trademarket):
                            pairlist.append(pair)
                            break
        else:
            pairlist = ""
            coin = re.search("(\w+)_(\w+)", pairs).group(2)

            for symbol in market:
                if (
                    coin.lower() == symbol["symbol"]
                    and int(symbol["market_cap_rank"]) <= rank
                ):
                    self.logging.info(
                        str(pairs)
                        + " is ranked #"
                        + str(symbol["market_cap_rank"])
                        + " and has passed marketcap filter limit of #"
                        + str(rank)
                    )
                    # Check if topcoin has enough volume
                    if self.topvolume(symbol["id"], volume, exchange, trademarket):
                        pairlist = pairs
                        break

        if not pairlist:
            self.logging.info(str(pairs) + " did not match the topcoin filter criteria")
        else:
            if isinstance(pairlist, str):
                self.logging.info(str(pairlist) + " matching top coin filter criteria")
            else:
                self.logging.info(
                    str(len(pairlist))
                    + " symrank pair(s) AFTER top coin filter: "
                    + str(pairlist)
                )

        return pairlist

    # Credits go to @M1ch43l
    # Adjust DCA settings dynamically according to social sentiment: greed = aggressive DCA, neutral = moderate DCA, fear = conservative DCA
    @retry(wait=wait_fixed(60))
    def requests_call(self, method, url, timeout):
        response = []
        try:
            response = requests.request(method, url, timeout=timeout)
        except Exception as e:
            raise IOError("Fear and greed index API actually down, retrying in 60s, Error is:" + e)
        return response

    async def get_fgi(self, asyncState):
        
        url = "https://api.alternative.me/fng/"
        self.logging.info("Using crypto fear and greed index (FGI) from alternative.me for changing 3cqsbot DCA settings to defensive, moderate or aggressive")

        while True:
            
            response = self.requests_call("GET", url, 5)        
            raw_data = json.loads(response.text)
            fgi = int(raw_data["data"][0]["value"])
            time_until_update = int(raw_data["data"][0]["time_until_update"])
            fmt = '{0.hours}h:{0.minutes}m:{0.seconds}s'
            self.logging.info("Current FGI: " + str(fgi) + " - time till next update: " 
            + fmt.format(rd(seconds=time_until_update)))
            asyncState.fgi = fgi

            # request FGI once per day, because is is calculated only once per day 
            await asyncio.sleep(time_until_update)

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
    async def getbtcpulse(self, asyncState):

        self.logging.info("Starting btc-pulse")

        while True:
            btcusdt = self.btctechnical("BTC-USD")
            # if EMA 50 > EMA9 or <-1% drop then the sleep mode is activated
            # else bool is false and while loop is broken
            if (
                btcusdt.percentchange_15mins[-1] < -1
                or btcusdt.EMA50[-1] > btcusdt.EMA9[-1]
            ):
                self.logging.info("btc-pulse signaling downtrend")

                # after 5mins getting the latest BTC data to see if it has had a sharp rise in previous 5 mins
                await asyncio.sleep(300)
                btcusdt = self.btctechnical("BTC-USD")

                # this is the golden cross check fast moving EMA
                # cuts slow moving EMA from bottom, if that is true then bool=false and break while loop
                if (
                    btcusdt.EMA9[-1] > btcusdt.EMA50[-1]
                    and btcusdt.EMA50[-2] > btcusdt.EMA9[-2]
                ):
                    self.logging.info("btc-pulse singaling uptrend (golden cross check)")
                    asyncState.btc_downtrend = False
                else:
                    self.logging.info("btc-pulse signaling downtrend (golden cross check)")
                    asyncState.btc_downtrend = True

            else:
                self.logging.info("btc-pulse signaling uptrend")
                asyncState.btc_downtrend = False

            self.logging.info("Next btc-pulse check in 5m")
            await asyncio.sleep(300)
