import yfinance as yf
import numpy as np
import asyncio
import math
import re

from pycoingecko import CoinGeckoAPI
from tenacity import retry,wait_fixed

class Signals:

    def __init__(self, logging):
        self.cg = CoinGeckoAPI()
        self.logging = logging
    

    def topcoin(self, pairs, rank):
        pages = math.ceil(rank / 250)
        market = []

        for page in range(1,pages +1):
            page = self.cg.get_coins_markets(vs_currency='usd', page=page, per_page=250)
            for entry in page:
                market.append(entry)
        
        
        if isinstance(pairs, list):
            pairlist = []
            for pair in pairs:
                for symbol in market:
                    coin = pair
                    if coin.lower() in symbol['symbol']:
                        pairlist.append(pair)
                        break
        else:
            pairlist = ""
            coin = re.search('(\w+)_(\w+)', pairs).group(2)

            for symbol in market:
                if coin.lower() in symbol['symbol']:
                    pairlist = pairs
                    break
        
        self.logging.debug("Pairs after toplist: " + str(pairlist))
        return pairlist

    # Credits going to @IamtheOnewhoKnocks from
    # https://discord.gg/tradealts
    def ema(self, data, period, smoothing=2):
        # Calculate EMA without dependency for TA-Lib
        ema = [sum(data[:period]) / period]
        
        for price in data[period:]:
            ema.append((price * (smoothing / (1 + period))) + ema[-1] * (1 - (smoothing / (1 + period))))
        
        for i in range(period-1):
            ema.insert(0, np.nan)
        
        return ema

    # Credits going to @IamtheOnewhoKnocks from
    # https://discord.gg/tradealts
    @retry(wait=wait_fixed(2))
    def btctechnical(self, symbol):
        btcusdt = yf.download(tickers=symbol, period = '6h', interval = '5m', progress= False)
        if len(btcusdt) > 0:
            btcusdt = btcusdt.iloc[:,:5]
            btcusdt.columns = ['Time','Open','High','Low','Close']
            btcusdt = btcusdt.astype(float)
            btcusdt["EMA9"] = self.ema(btcusdt["Close"], 9)
            btcusdt["EMA50"] = self.ema(btcusdt["Close"], 50)
            btcusdt['per_5mins'] = (np.log(btcusdt['Close'].pct_change() + 1))*100
            btcusdt['percentchange_15mins'] = (np.log(btcusdt['Close'].pct_change(3) + 1))*100
        else:
            raise IOError("Downloading YFinance chart broken, retry....")
            
        return btcusdt
        
    # Credits going to @IamtheOnewhoKnocks from
    # https://discord.gg/tradealts
    async def getbtcbool(self, asyncState):

        self.logging.info('Starting btc pulse')

        while True:
            btcusdt = self.btctechnical('BTC-USD')
            # if EMA 50 > EMA9 or <-1% drop then the sleep mode is activated 
            # else bool is false and while loop is broken
            if btcusdt.percentchange_15mins[-1] < -1 or btcusdt.EMA50[-1] > btcusdt.EMA9[-1]:
                self.logging.info('Bot sleep')
                
                # after 5mins getting the latest BTC data to see if it has had a sharp rise in previous 5 mins
                await asyncio.sleep(300)
                btcusdt = self.btctechnical('BTC-USD')

                # this is the golden cross check fast moving EMA
                # cuts slow moving EMA from bottom, if that is true then bool=false and break while loop
                if (btcusdt.EMA9[-1] > btcusdt.EMA50[-1] and
                    btcusdt.EMA50[-2] > btcusdt.EMA9[-2] ):
                    self.logging.info('Bot awake')
                    asyncState.btcbool =  False
                else:
                    self.logging.info('Bot sleep')
                    asyncState.btcbool = True
                
            else:
                self.logging.info('Bot awake')
                asyncState.btcbool = False
            
            await asyncio.sleep(300)
            


