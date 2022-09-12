import yfinance as yf
import numpy as np
import asyncio
import json
import requests

from tenacity import retry, wait_fixed
from functools import lru_cache, wraps
from time import monotonic_ns
from dateutil.relativedelta import relativedelta as rd


class Conditions:
    def __init__(self, logging):
        self.logging = logging

    # Credits goes to @IamtheOnewhoKnocks from
    # https://discord.gg/tradealts
    def __ema(self, data, period, smoothing=2):
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
    def __ticker(self, symbol):
        btcusdt = yf.download(
            tickers=symbol, period="6h", interval="5m", progress=False
        )
        if len(btcusdt) > 0:
            btcusdt = btcusdt.iloc[:, :5]
            btcusdt.columns = ["Time", "Open", "High", "Low", "Close"]
            btcusdt = btcusdt.astype(float)
            btcusdt["EMA9"] = self.__ema(btcusdt["Close"], 9)
            btcusdt["EMA50"] = self.__ema(btcusdt["Close"], 50)
            btcusdt["per_5mins"] = (np.log(btcusdt["Close"].pct_change() + 1)) * 100
            btcusdt["percentchange_15mins"] = (
                np.log(btcusdt["Close"].pct_change(3) + 1)
            ) * 100
        else:
            raise IOError("Downloading YFinance chart broken, retry....")

        return btcusdt

    # Credits goes to @IamtheOnewhoKnocks from
    # https://discord.gg/tradealts
    async def btcpulse(self, asyncState):

        self.logging.info("Condition: Starting BTC-Pulse")

        while True:
            btcusdt = self.__ticker("BTC-USD")
            # if EMA 50 > EMA9 or <-1% drop then the sleep mode is activated
            # else bool is false and while loop is broken
            if (
                btcusdt.percentchange_15mins[-1] < -1
                or btcusdt.EMA50[-1] > btcusdt.EMA9[-1]
            ):
                self.logging.info("BTC-Pulse signaling downtrend")

                # after 5mins getting the latest BTC data to see if it has had a sharp rise in previous 5 mins
                await asyncio.sleep(300)
                btcusdt = self.__ticker("BTC-USD")

                # this is the golden cross check fast moving EMA
                # cuts slow moving EMA from bottom, if that is true then bool=false and break while loop
                if (
                    btcusdt.EMA9[-1] > btcusdt.EMA50[-1]
                    and btcusdt.EMA50[-2] > btcusdt.EMA9[-2]
                ):
                    self.logging.info("BTC-Pulse signaling uptrend")
                    asyncState.btc_downtrend = False
                else:
                    self.logging.info("BTC-Pulse signaling downtrend")
                    asyncState.btc_downtrend = True

            else:
                self.logging.info("BTC-Pulse signaling uptrend")
                asyncState.btc_downtrend = False

            self.logging.info("Next BTC-Pulse check in 5m")

            await asyncio.sleep(300)

    # Credits goes to @M1ch43l from
    # https://discord.gg/tradealts
    # Credits go to @M1ch43l
    # Adjust DCA settings dynamically according to social sentiment: greed = aggressive DCA, neutral = moderate DCA, fear = conservative DCA
    @retry(wait=wait_fixed(10))
    def requests_call(self, method, url, timeout):
        response = []
        try:
            response = requests.request(method, url, timeout=timeout)
        except Exception as e:
            raise IOError(
                "Fear and greed index API actually down, retrying in 60s, Error is:" + e
            )
        return response

    async def get_fgi(self, asyncState, ema_fast, ema_slow):

        url = "https://api.alternative.me/fng/?limit=100"
        self.logging.info(
            "Condition: Starting crypto fear and greed index (FGI) from alternative.me"
        )

        while True:
            fgi_values = []
            fgi_ema_fast = []
            fgi_ema_slow = []
            asyncState.fgi_notification = True
            response = self.requests_call("GET", url, 5)
            raw_data = json.loads(response.text)
            for i in range(len(raw_data["data"])):
                fgi_values.insert(0, int(raw_data["data"][i]["value"]))
            fgi_ema_fast = self.ema(fgi_values, ema_fast)
            fgi_ema_slow = self.ema(fgi_values, ema_slow)
            time_until_update = int(raw_data["data"][0]["time_until_update"])
            fmt = "{0.hours}h:{0.minutes}m:{0.seconds}s"
            # Web response sometimes slow, so proceed only if time_until_update for next web update > 10 sec
            if time_until_update > 10:
                self.logging.info(
                    "Current FGI: {:d}".format(fgi_values[-1])
                    + " - time till next update: "
                    + fmt.format(rd(seconds=time_until_update))
                )
                asyncState.fgi = fgi_values[-1]

                if fgi_ema_fast[-1] < fgi_ema_slow[-1]:
                    asyncState.fgi_downtrend = True
                    self.logging.info(
                        "FGI-EMA{0:d}: {1:.1f}".format(ema_fast, fgi_ema_fast[-1])
                        + " less than FGI-EMA{:d}: {:.1f}".format(
                            ema_slow, fgi_ema_slow[-1]
                        )
                        + "  -- downtrending"
                    )
                else:
                    asyncState.fgi_downtrend = False
                    self.logging.info(
                        "FGI-EMA{0:d}: {1:.1f}".format(ema_fast, fgi_ema_fast[-1])
                        + " greater than FGI-EMA{:d}: {:.1f}".format(
                            ema_slow, fgi_ema_slow[-1]
                        )
                        + "  -- uptrending"
                    )

                # FGI downtrend = true if FGI drops >= 10 between actual and last day
                # OR >= 15 between actual and second to last day
                if ((fgi_values[-2] - fgi_values[-1]) >= 10) or (
                    (fgi_values[-3] - fgi_values[-1]) >= 15
                ):
                    asyncState.fgi_downtrend = True
                    self.logging.info(
                        "FGI actual/yesterday/before yesterday: {:d}/{:d}/{:d}".format(
                            fgi_values[-1], fgi_values[-2], fgi_values[-3]
                        )
                    )
                    self.logging.info(
                        "Drop > 10 between actual vs. yesterday or drop > 15 between actual vs. before yesterday"
                    )

                asyncState.fgi_time_until_update = time_until_update

            # request FGI once per day, because is is calculated only once per day
            await asyncio.sleep(time_until_update)
