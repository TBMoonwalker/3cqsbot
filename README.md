# Based on TBMoonWalker's 3CQSBot v2.1.4-alpha script - Improved by M1ch43l with adding following features v.2.5.0-alpha

1. Implementation of sentiment trading according to the Crypto Fear and Greed Index (FGI) with separate DCA profiles including profile specific topcoin filter settings and amount of concurrent deals. New sections `[fgi_aggressive]`, `[fgi_moderate]` and `[fgi_defensive]` added for individual single/multi bot DCA configurations
2. Implementation of fgi_pulse trading, similar to btc_pulse however using the crossing of EMA9 to EMA20 as default values to decide for trading
3. Notification on Telegram: new deals are reported on your personal Telegram channel - no need to check your logs daily, also extended notification available for reporting every 3CQS signal
4. Config und DCA setting reporting with funds needed, max. coverage and required change
5. For Multibot: if `deal_mode = signal` is used, deals are triggered ONCE (no ASAP mode compared to single bot configuration)
6. For Multibot: Symrank list sorting according to trading volume and limiting to maximum active deals, e.g. when using ASAP like mode
7. List of tradeable pairs on 3Commas is updated every 6 hours to check for new or blacklisted coins
8. White-list for pairs implemented - trade only certain coins
9. Improved error handling if 3Commas, CoinGeckos or Yahoo Finance API requests are lagging
10. Backwards compatibility to v2.1.4 - use your old config

## Summary

This python script program is addressed to users with basic linux command line experience and advanced experience for running single / multibots using the trading platform [3Commas](https://3commas.io). 3cqsbot can be used to start and stop DCA (Dollar Cost Average) bots with the help of external given 3CQS trading signals.
3CQS trading signals are developed using various market indicators and extensive technical research of the current and historical market atmosphere. They offer effective trading suggestions to purchase, trade or hold an asset. 3CQS trading signals are designed to signal the start and stop of DCA bots for optimal performance under a variety of market conditions. You can subscribe to the <https://t.me/The3CQSBot> to receive these signals. Enter `/signals` after joining and select proper signals you want to receive. It is recommended to start with 'SymRank Top 100 Quadruple tracker' as default and to switch off all other signals to avoid of being banned from receiving to much signals. If you have any questions regarding the signals, please contact the developer [directly](https://www.3cqs.com/contact/).

## Disclaimer

Note: **The 3cqsbot is meant to be used for educational purposes only. The use with real funds is FULLY at your own risk and not recommended. The signal sender as well the authors of 3cqsbot cannot be held responsible for losses when using real money**

## Prerequisites

### 3CQS Signals Bot

Join the telegram channel <https://t.me/The3CQSBot> according to the official Telegram [documentation](https://core.telegram.org/api/obtaining_api_id)

Wait for the signals. Actually the signals are in a beta phase and you have to be chosen to get them. Be patient if they not arrive after joining

### Telegram API

In the meantime create your [telegram api account](https://my.telegram.org/apps) and insert them into `api_id` and `api_hash` fields in the *'telegram'* section of the `config.ini`

### 3Commas API

Create a [3commas api account](https://3commas.io/api_access_tokens) too and insert the values in the `key` and `secret` fields in the *'commas'* section of the `config.ini`

**Permissions needed:** BotsRead, BotsWrite, AccountsRead

### Operating Systems

- MacOS
- Linux
  - Ubuntu
- Windows
  - untested (please let me know if it works)
- Docker

## Installation

### Python

Please install at least version 3.7 on your system

### Python modules

```bash
pip3 install -r requirements.txt
```

## Configuration (config.ini)

Copy the `*.example*` from the examples directory to `config.ini` in the root folder and change your settings regarding the available settings below. The value type doesn't matter, because Pythons configparser is taking care of the types. So you don't need '' or "" around the values.

### [general]

Name | Type | Mandatory | Values(default) | Description
------------ | ------------ | ------------ | ------------ | ------------
timezone | string | NO | Europe/Amsterdam | Set logging to timezone, see <https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568> for a list of possible timezones
debug | boolean | NO | (false), true   | Set logging to debug
logrotate | integer | NO | (7) | How many logfiles will be archived, before deleted

### [telegram]

Name | Type | Mandatory | Values(default) | Description
------------ | ------------ | ------------ | ------------ | ------------
api_id | string | YES |   | Telegram API ID
api_hash | string | YES |   | Telegram API Hash
sessionfile | string | NO | (tgsession) | Telegram sessionfile location
chatroom | string | NO | (3C Quick Stats) | Telegram channel to receive the 3cqs signals
notifications | boolean | NO | (false), true | set to true to enable notifications - code from Cyberjunky
extensive_notifications | boolean | NO | (false), true | every START/STOP signal is reported
notify-urls | string | NO | ["tgram://bottoken/ChatID"]  | See following instructions to obtain the TG bottoken and ChatID
  
To get your Telegram bot token (format is 1234567890:alphanumeric_characters) see <https://www.siteguarding.com/en/how-to-get-telegram-bot-api-token>. Enter in the same dialog box of @BotFather /start to enable your notification bot on Telegram.  
To get your ChatID (format is 1234567890) enter @RawDataBot in the channel search function. Under search results with the section "chats" select "Telegram Bot Raw". Press the START button or type /start. On the output you see "Made by @SeanChannel". In the output look for "chat": "id". This is your ChatID to enter. See also <https://www.alphr.com/find-chat-id-telegram/> for instructions.  
Other notifications ways are possible. Enter one or a list of apprise notify urls, each in " " seperated with commas. See [Apprise website](https://github.com/caronc/apprise) for more information.
  
**!!! ATTENTION - When creating multiple 3cqsbot instances by copying the 3cqsbot directory, REMOVE your telegram sessionfile (tgsession.session) with other 3cqsbot instances - otherwise this will lead to problems and misfunctional bots. For each instance you have to create a new TG sessionfile by starting the bot once manually!!!**

### [3commas]

Name | Type | Mandatory | Values(default) | Description
------------ | ------------ | ------------ | ------------ | ------------
chatroom | string |NO | (3C Quick Stats) | Name of the chatroom - on Windows please use the ID 5011413076
key | string | YES |    | 3Commas API Key
secret | string | YES | | 3Commas API Secret
timeout | integer | NO | (3) | Timeout waiting for a 3Commas api response
retries | integer | NO | (5) | Number of retries after a 3Commas api call was not successful
delay_between_retries | number | NO | (2.0) | Waiting time factor between unsuccessful retries
system_bot_value | integer | NO | (300) | Number of actual bots running on your account. This is important, so that the script can see all running bots and does not start duplicates!
botid | integer | NO | (1234567) | Applies only to multi bot and in combination with market sentiment trading using the fear and greed index for cryptos (FGI)  - Using botid of an already created bot ensures that the algo applies modification only to this bot and avoids creating a new one, e.g. if bot name is changed or DCA settings are changed according to FGI

### DCABot configuration [dcabot, fgi_aggressive, fgi_moderate, fgi_defensive]

Name | Type | Mandatory | Values(default) | Description
------------ | ------------ | ------------ | ------------ | ------------
fgi_min | integer | NO | (61) or (31) or (0) | for `[fgi_aggressive]` or `[fgi_moderate]` or `[fgi_defensive]`
fgi_max | integer | NO | (100) or (60) or (30) | for `[fgi_aggressive]` or `[fgi_moderate]` or `[fgi_defensive]`
prefix | string | YES | (3CQSBOT)  | The name prefix of the created bot
subprefix | string | YES | (MULTI) | Subprefix of the bot (Best would be SINGLE or MULTI)
suffix | string | YES | (TA_SAFE) | Suffix in the bot name - could be the used DCA setting of the TA community
single_count | integer | YES | (3) | Maximum single bots - only have to be configured if single bot mode is used
mad | integer | YES | (3) | Max active deals for a bot
deal_mode | string | NO | ([{"options": {"time": "3m", "points": "100", "time_period": "7", "trigger_condition": "less"}, "strategy": "rsi"}]) signal | Method how the script is starting new deals in single / multi pair mode - for more see the "Deal START signal/strategy examples" section
tp | number | YES | (1.5)  | Take profit in percent
trailing | boolean | NO | (false), true | Trailing profit enabled
trailing_deviation | number | NO | (0.2) | Deviation of trailing profit
bo | number | YES | (11)   | Base order volume
so | number | YES | (11) | Safety order volume
os | number | YES | (1.05) | Safety order volume scale
ss | number | YES | (1) | Safety order step scale
sos | number | YES | (2.4) | Price deviation to open safety orders
mstc | integer | YES | (25) | Max safety trades count
max | integer | YES | (1) | Max active safety trades count
sdsp | integer | NO | (1) | Simultaneous deals per same pair (only Multibot)
btc_min_vol | number | NO | (100) | Minimum 24h volume trading calculated in BTC by 3commas
cooldown | number | NO | (30) | Number of seconds to wait until starting another deal
deals_count | integer | NO | (0) | Bot will be disabled after completing this number of deals. If 0 bot will not be disabled (default)
topcoin_limit | integer | NO | (3500) | Token pair has to be in the marketcap ranking limit to be traded by the bot
topcoin_volume | integer | NO | (0) | additional trading volume check on Coingecko which is done first before adding the coin in the trading list of 3commas (it is unclear how actual and accurate btc_min_vol of 3commas is). Only pairs with the given volume are traded. Default is 0 and means CG volume check is disabled

Configure the `[dcabot]` and if using market sentiment trading add `[fgi_aggressive]`, `[fgi_moderate]`, `[fgi_defensive]` section in the `config.ini` according to your favourite bot configuration. Tip: You can use different bot names, so you know which dca setting is used by the bot or deal.

If you don't have any DCA settings, please take a look at [Ribsy's site](https://www.buymeacoffee.com/Ribsy/posts) for published settings and background information and for the [TA community list](https://docs.google.com/spreadsheets/d/1cQ68_Sl70SRFRMeGu0zgBhTCuQvSf6ENi_obLhr7kpw/edit#gid=885933644) with all tested DCA settings

Default configuration is based on Trade Alts Safer settings: <https://discord.gg/tradealts>

#### Single bot configuration

**single_count** = how many singlebots can run overall

**mad** = how many deals can run on a singlebot pair

**Examples:**

`single_count=1`, `mad=1` - Only one singlebot is started, and only one deal is started

`single_count=3`, `mad=1` - Three singlebots are started, and only one deal per singlebot is started

`single_count=3`, `mad=2` - Three singlebots are started, and two deals are started per singlebot

#### Multi bot configuration

**mad** = how many deals per composite bot can run

**Example:**

`mad=20` - 20 deals with different pairs can run at the same time

### Deal Mode explanation

Condition: **single=true deal_mode=signal**

A single bot for a specific pair (the signal) will be created when the pair fits your configured filters and when the 3CQS signal is a "#START" signal. The deal will be started immediately. The bot will be disabled on a #STOP signal for this specific pair. If `delete_single_bots` is set to true, the script tries do delete the bot. This only works, when no deal is running.

Condition: **single=true deal_mode="self assigned strategy"**

Everything is the same as with the other single mode, but the deals are started dependent on your configured `deal_mode` strategy.

Condition: **single=false deal_mode=signal**

A multi bot will be created with the top 30 Symrank list (initical call to /symrank). A new deal will be started when a new signal is coming in.

If it is a STOP/START signal which is not from an existing pair a random pair from the initial top 30 Symrank list is used for a new deal.

If it is a START signal from an existing pair or a freshly added pair, exactly that pair is used for a new deal.

Pairs will be deleted from the list during a STOP signal and added with a START signal, if it fits the filters.

Condition: **single=false deal_mode="self assigned strategy"**

Everything is the same as with the other multi mode, but the deals are started dependent on your configured `deal_mode` strategy.

### Deal START signal/strategy examples

`deal_mode = signal`

- for **single bot**: 3CQS #START signal creates the single bot and deal is started **ASAP** (deal start condition is set to "open new trade ASAP" by the algo). After finishing the deal, a new one is started as long as the single bot is enabled.

- for **multi bot**: 3CQS #START signal adds the pair and deal is started **manually** by the program, only **ONCE** after adding. After the deal is closed, the deal is **not** started again in contrast to ASAP for **single bot**.  
If you want the same behaviour as for **single bot** you have to use a strategy for deal_mode (see below), which can be configured almost as ASAP.
Deal start condition is set to "manual strategy" by the algo because "open new trade ASAP" is generally not implemented for multi bots because of security reasons - imagine you have a list of 100 pairs and all are opened simultaneously with ASAP

`deal_mode = [{json coded 3commas strategy}}`

- for **single bot**: deal is only started when RSI-7 15min < 70 preventing from buying in the overbought area  
`deal_mode = [{"options":{"time_period":"7","time":"15m","trigger_condition":"less","points":"70"},"strategy":"rsi"}]`

- for **multi bot**: If filtered symrank pairs should be started as soon as possible (ASAP) up to maximum active deals (mad) use the deal start condition such as  
`[{"options":{"time_period":"7","time":"3m","trigger_condition":"less","points":"100"},"strategy":"rsi"}]`  
or  
`[{"options": {"time": "1m", "type": "buy_or_strong_buy"}, "strategy": "trading_view"}]`  
  You can also use a combination of different indicators/filters:  
`[{"options": {"time": "1m", "type": "buy_or_strong_buy"}, "strategy": "trading_view"},{"options": {"time": "5m", "type": "buy_or_strong_buy"}, "strategy": "trading_view"},{"options": {"time": "15m", "type": "buy_or_strong_buy"}, "strategy": "trading_view"},{"options":{"length":14,"time":"15m","points":55},"strategy":"rsi"},{"options":{"length":14,"time":"4h","points":70},"strategy":"rsi"}]`

- **NOTE** Not all exchanges support all deal mode strategies. Example, as of April 2022 Kucoin does NOT support the RSI strategy and will result in no deals starting. Ensure that your desired strategy is supported on your exchange before setting it in the config.

A whole list of deal start signals can be found on <https://discord.com/channels/720875074806349874/835100061583015947/965743501570609172> in json coded format, alternatively get deal start with the API call `GET /ver1/bots/strategy_list`. More details can be found under: <https://github.com/3commas-io/3commas-official-api-docs/blob/master/bots_api.md>

## Trading mode

Name | Type | Mandatory | Values(default) | Description
------------ | ------------ | ------------ | ------------ | ------------
market | string | YES | (USDT)  | Trading market (Example: BUSD, USDT, USDC)
trade_mode | string | YES | (paper), real   | Real or Paper trading mode
account_name | string | YES | (Paper trading 123456)  | Account name for trading. Can be found unter "My Exchanges".
single | boolean | YES | (false), true | Type of not creation (False for multi pair DCA Bots / True for single pair DCA Bots)
delete_single_bots | boolean | NO | (false), true | If set to true, bots without an active deal will be deleted in single bot configuration
singlebot_update | boolean | NO | (true), false | If set to true, singlebots settings will be updated when enabled again (new settings only work after restart of the script)
trade_future | boolean | NO | (false), true | Enable futures trading - **actually NOT working, implementation is planned**
leverage_type | string | NO | (cross), custom, not_specified, isolated | Different leverage types for futures trading from 3commas
leverage_value | integer | NO | (2) | Leverage value for futures trading
stop_loss_percent | integer | NO | (1) | Stop loss value in percent for futures trading
stop_loss_type | string | NO | (stop_loss_and_disable_bot), stop_loss | Stop Loss type for futures trading
stop_loss_timeout_enabled | boolean | NO | (false), true | Enable stop loss timeout for futures trading
stop_loss_timeout_seconds | integer | NO | (5) | Time interval for stop loss in seconds for futures trading

## Filter

Name | Type | Mandatory | Values(default) | Description
------------ | ------------ | ------------ | ------------ | ------------
symrank_signal | string | YES | (triple100), quadruple100, quadruple250, top30, svol, svoldouble, hvol, hvoldouble, uvol, xvol, all | Decide which signal the bot should parse.
symrank_limit_min | integer | NO | (1) | Bots will be created when the symrank value is over this limit
symrank_limit_max | integer | NO | (100) | Bots will be created when the symrank value is under this limit
volatility_limit_min | number | NO | (0.1) | Bots will be created when the volatility value is over this limit
volatility_limit_max | number | NO | (100) | Bots will be created when the volatility value is under this limit
price_action_limit_min | number | NO | (0.1) | Bots will be created when the price_action value is over this limit
price_action_limit_max | number | NO | (100) | Bots will be created when the price_action value is under this limit
topcoin_filter | boolean | NO | (false), true | Disables the topcoin filter (default)
topcoin_exchange | string | NO | (binance), gdax | Name of the exchange to check the volume. Because every exchange has another id, please contact me for your exchange and I will update this list here for configuration
continuous_update | boolean | NO | (true), false | If set to true the multi bot is continuously updated with pairs independent of being activated or deactivated, e.g. by btc_pulse. The top30 symrank list is called once when bot is started.
limit_initial_pairs | boolean | NO | (false), true | Limit symrank pairs to the max number of deals (MAD) and sort them by trading volume for multi bot - top pairs are chosen
random_pair | boolean | NO | (false), true | If true then random pairs from the symrank list will be used for new deals in multibot
btc_pulse | boolean | NO | (false), true | Enable or disable the bots according to Bitcoins behaviour. If Bitcoin is going down, the bot will be disabled
fgi_pulse | boolean | NO | (false), true | Enable or disable the bots according to markets sentiment using EMA crossing
fgi_ema_fast | integer | NO | (9) | determine down-/uptrending of FGI using EMA fast crossing up/down EMA slow
fgi_ema_slow | integer | NO | (20) | determine down-/uptrending of FGI using EMA fast crossing up/down EMA slow
fgi_trading | boolean | NO | (false), true | If true, three different dca settings can be used according to market's sentiment (use [fgi_aggressive] for bull market, [fgi_moderate] for sideways market, [fgi_defensive] for bear market, each with corresponding dca settings)
fgi_trade_min | integer | NO | (0) | if fgi_trading set to true define minimum FGI value for trading
fgi_trade_max | integer | NO | (100) | if fgi_trading set to true define maximum FGI value for trading
ext_botswitch | boolean | NO | (false), true | If true the automatic multibot enablement will be disabled and only triggered by external events - you must disable BTC Pulse if you enable this switch !!!
token_denylist | list | NO | ([BUSD_USDT, USDC_USDT, USDT_USDT, USDT_USDP]) | Additional denylist of assets in combination to 3commas blacklist to prevent the bot from including and buying unwanted assets
token_whitelist | list | NO | ([BTC_BUSD, ETH_BUSD]) | Trade only whitelisted pairs

## 3CQS Trading Signals

There are different 3CQS trading signals. To decide which signal fits your needs, please take a look at the signals beneath. The description can be found on Discord too: <https://discord.com/channels/720875074806349874/835100061583015947/958724423513419876> or officially on <https://www.3cqs.com/home/faq/>

### What is SymRank?

SymRank is a proprietary symbol ranking system exclusive to 3CQS users that ranks symbols (coins) in near realtime based on multiple criteria including current trading volume, volatility and price action.

### What are Volatiltiy Scores?

Pricing is monitored in near realtime and calculated which results in 15m, 30m, 1h, etc. volatility interval percentages. Each interval is then weighted and averaged based on the timeframe (more recent time frames are weighted higher), from which a score is calculated. Higher scores are greater volatility.

### What are Price Action Scores?

Realtime pricing is monitored and calculated using a combination of moving average formulas. Similar to volatility, more weight is given to recent pricing, from which a score is calculated.

### Price Action & Volatility Score Insight

3CQS price action and volatility take into account pricing over the last 24 hours. Scores that are marked with the red color are considered currently on a downtrend and green if on an uptrend.

Price action scores that are significantly negative are when price is moving much lower over the last 24 hours. Volatility scores can be negative as well, but are not calculated the same and won’t generally be seen with as large negative scores.

Negative scores represent the lowest of all price / volatility trend movements over 24 hours whereas the color is the current projected up / downtrend. Basically significant sells that drop price drastically will likely result in larger negative price action scores, but it could increase volatility as buys increase price. So you can have a very low negative price action score with a high volatility score in many cases. The scores are constantly recalculated, so it’s helpful to see the trends when you hover over the scores.

### Possible strategies for symrank_signal

#### ```triple100```

**Signal Name**: SymRank Top 100 Triple Tracker  
Criteria for BOT_START: SymRank <= 100, Volatility Score >= 3, Price Action Score >= 2  
These three indicators are tracked and if any fall out the starting thresholds for a period of time a BOT_STOP signal is sent

#### ```quadruple100```

**Signal Name**: SymRank Top 100 Quadruple Tracker  
Criteria for BOT_START: SymRank <= 100, Volatility Score >= 3, Price Action Score >= 2, RSI-14 15m <= 65  
These four indicators are tracked and if any fall out the starting thresholds for a period of time a BOT_STOP signal is sent

#### ```quadruple250```

**Signal Name**: SymRank Top 250 Quadruple Tracker  
Criteria for BOT_START: SymRank <= 250, Volatility Score >= 3, Price Action Score >= 2, RSI-14 15m <= 65  
These four indicators are tracked and if any fall out the starting thresholds for a period of time a BOT_STOP signal is sent

#### ```top30```

**Signal Name**: SymRank Top 30  
Criteria for BOT_START: SymRank <= 30  
SymRank is tracked and if the symbol falls out of the Top 30 for a period of time a BOT_STOP signal is sent

#### ```svol```

**Signal Name**: Super Volatility  
Criteria for BOT_START: Volatility Score >= 4  
Volatility scores are tracked and if the symbol falls out of the starting threshold for a period of time a BOT_STOP signal is sent

#### ```svoldouble```

**Signal Name**: Super Volatility Double Tracker  
Criteria for BOT_START: Volatility Score >= 4, Price Action Score >= 2  
Volatility and price action scores are tracked and if the symbol falls out of the starting threshold for a period of time a BOT_STOP signal is sent

#### ```hvol```

**Signal Name**: Hyper Volatility  
Criteria for BOT_START: Volatility Score >= 6  
Volatility scores are tracked and if the symbol falls out of the starting threshold for a period of time a BOT_STOP signal is sent

#### ```hvoldouble```

**Signal Name**: Hyper Volatility Double Tracker  
Criteria for BOT_START: Volatility Score >= 6, Price Action Score >= 2  
Volatility and price action scores are tracked and if the symbol falls out of the starting threshold for a period of time a BOT_STOP signal is sent

#### ```uvol```

**Signal Name**: Ultra Volatility  
Criteria for BOT_START: Volatility Score >= 8  
Volatility score are tracked and if the symbol falls out of the starting threshold for a period of time a BOT_STOP signal is sent

#### ```xvol```

**Signal Name**: X-treme Volatility  
Criteria for BOT_START: Volatility Score >= 10  
Volatility scores are tracked and if the symbol falls out of the starting threshold for a period of time a BOT_STOP signal is sent

#### ```all```

Process all signals

### BTC pulse

BTC pulse is a simple strategy which monitors BTC price action to start new deals or just put the bot to sleep ( no new deals but active deals keep running) based on:  

- If BTC is uptrending new deals are started  
- If BTC is downtrending no new deals are started

BTC pulse hence is determined using the 2 factors:  

- % price change of BTC in the last 15 minutes or Fast (9) and Slow (50) moving EMAs crossses

Please test this strategy on paper before putting real money on it.
TBMoonWalker or IamtheOnewhoKnocks take no responsibility for losses occurred due to the script/strategy

Note: **Please use 3cqsbot only on paper trading. Usage with real funds is at your own risk**

### Fear and Greed Index

The use of the Crypto Fear and Greed index (FGI) helps you to identify the sentiment of the corresponding market phase and to use adapted DCA profiles. The FGI is determined once a day on <https://alternative.me/crypto/fear-and-greed-index/>
![Screenshot](FGI%20borders%20screenshot.png)
  
The option fgi_trading activates FGI dependent DCA profile setting and trading.  

When FGI is signaling "greed (FGI values 60-80)/very greed (80-100)" you may use aggressive DCA settings `[fgi_aggressive]`, e.g. Mars/Banshee/69er DCA settings covering a price drop of 20-40%. You can use less maximum active deals then usual because a drop is very likely and you do not want to sit on red bags for the next 6-9 months.

In phases of fear (FGI values 0-30) over a longer time that may correspond to a beginning or consolidating bear market, the bot can switch to very defensive/conservative DCA settings `[fgi_defensive]`, eg. TA safer, ZachTech BitMan DCA settings covering a price drop of up to 60%.

Get the excel lists from @Snurg at <https://discord.com/channels/720875074806349874/829512509798219788/965771867413696532> to get the optimal DCA settings in corresdonding market phases according to your trade funds.

For sideways market (FGI values 31-60) you can define DCA settings under `[fgi_moderate]`.

In each fgi section define the variables ```fgi_min``` and ```fgi_max``` so that the correct DCA settings are applied. If ```fgi_min/fgi_max``` are not set, then values between ```fgi_min = 0``` and ```fgi_max = 30``` are assumed for defensive, FGI values between 31-60 are assumed for moderate and FGI values between 61-100 are assumed for aggressive settings.

If corresponding fgi section is not found, the standard [dcabot] section is used and the FGI values are ignored.

**To know**: No new 3cqsbot is created when using FGI guided DCA settings, instead the new settings are applied to the existent one, so that new deals are started with the new DCA settings.

Optionally, the multi pair bot can be renamed according to the prefix, subprefix and suffix given in the corresponding fgi section, e.g. renaming from 3CQSBOT_MULTI_aggressive to 3CQSBOT_MULTI_defensive. To make sure it is always the same bot, you can additionally use the option 'botid' with the same botid number of an already created multi bot in all fgi sections.

For single bots the standard name (prefix, subprefix, suffix) defined in `[dcabot]` is used ensuring that the algo finds all single bots under standard name to switch them off when receiving the #STOP signal from 3CQS.

### Fear and Greed Index trading range

With the options ```fgi_trade_min = 10``` and ```fgi_trade_max = 90``` you can generally define the allowed trading range.

### Fear and Greed Index pulse

With the option fgi_pulse you can determine the trend direction of the market sentiment, in contrast to btc_pulse on a daily basis. When the sentiment is downtrending very fast (drop of >10% on one day or >15% on two days) trading is stopped, also if the fast (9) EMA is below the slow (20) EMA. Contrary, when fast EMA is crossing up the slow EMA line the market is uptrending and automated trading activities are started, dependent of your generally defined FGI trading range ```fgi_trade_min``` and ```fgi_trade_max```. You can customize the EMA values with the options ```fgi_ema_fast``` and ```fgi_ema_slow```.

### External bot switch

If external botswitch is enabled, the 3cqsbot can be switched on/off by external TradingView signals sent to 3commas.
See documentation on 3commas <https://3commas.io/trading-view> how to set up TradingView custom signals to manage your bot.
However, external botswitch can not be run simultanously with BTC pulse, because it will interfere the behaviour of the bot with signals.

## Run

If you get signals, you can run the script with the command:

```bash
python3 3cqsbot.py
```

When running for the first time, you will be asked for your Telegram phonenumber and you will get a code you have to insert!

### You don't get the code

Some users had to put spaces in the phone number. It seems the number has to be the same format as in Telegram. For example type in your telephone number as `+XXX XXX XXX XXX` to receive the code.

## Docker

### Create the docker image

```bash
docker build -t "your repo name"/3cqsbot:"version number"
```

### Create a persistent volume for your Telegram session file

```bash
docker volume create session
```

### Create your .env file

Copy one of the `.env.*.example` files from the example directory to `.env` in the root directory and change the settings. The same settings as in the config.ini can be used

### Run your container

```bash
docker run --name 3cqsbot --volume session:/App/session --env-file .env -d "your repo name"/3cqsbot:"version number"
```

### Logfile monitoring

```bash
docker logs --follow 3cqsbot
```

## PythonAnywhere

If you want to run 3cqsbot 24h/7d without running your home computer all the time and you do not have a Rasperry Pi,
then PythonAnywhere might be a cheap option for you to run the script.

### Create account

If you live in the EU go to <https://eu.pythonanywhere.com> otherwise <https://www.pythonanywhere.com>.
The 'Hacker account' plan for 5€/5$ is sufficient enough to run 3cqsbot

### Preparing PythonAnywhere to run 3CQSBot

Click on `Dashboard`. Under menue "New console" Click on `$ Bash` to open a Bash console in your home directory.
Clone the actual version of 3cqsbot from Github and install the requirements for the bot by following commands

```bash
git clone https://github.com/TBMoonwalker/3cqsbot.git 3cqsbot
cd 3cqsbot
pip3 install -r requirements.txt
cp config.ini.example config.ini
```

When you want to use multiple 3cqsbots simultanously you have to clone 3cqsbot to different directories

```bash
git clone https://github.com/TBMoonwalker/3cqsbot.git 3cqsbot_TAsafe
git clone https://github.com/TBMoonwalker/3cqsbot.git 3cqsbot_Urmav6
git clone https://github.com/TBMoonwalker/3cqsbot.git 3cqsbot_Mars
```

### Edit config.ini settings

Edit the config.ini with the integrated editor of PythonAnywhere in the `Files` menue. Paste the necessary keys of 3commas and Telegram and
configure your DCA settings. Once done you can copy your config.ini to other directories of 3cqsbot and adapt the DCA settings.

### Scheduled tasks

Because the consoles of PythonAnywhere are frequently restarted due to maintenance you have to use scheduled task to ensure continuous work of your 3cqsbot.
Before running 3cqsbot as scheduled task, make sure that you run the script once on the console to establish the Telegram security session.
Enter your phone number (international format, e.g. +49xxx or 0049xxx) of your Telegram account and enter the code you receive from Telegram.
Check if 3cqsbot is running without any problems under the console.
Do not copy the tgsession file to other directories of 3cqsbots, because it is an individual security file and you will invalidate the established Telegram session
when used with another version of 3cqsbot.

Click on `Tasks` menue. If you have only one python script running you can use the Always-on task (only one Always-on task allowed on the "Hacker account" plan).
In case of using more scripts, e.g. for testing DCA settings, you have to use scheduled tasks on an hourly basis. Select "Hourly" and paste

```bash
cd ~/3cqsbot && python 3cqsbot.py 
```

If you encounter problems with this command then try this where YOUR_USERNAME has to be replaced by your chosen username on PythonAnywhere.

```bash
cd /home/YOUR_USERNAME/3cqsbot && python 3cqsbot.py
```

When using multiple 3cqsbots with different settings you have to add each 3cqsbot directory as seperate hourly task.
Rename 3cqsbot.py according to your DCA setting configuration in the `Files` menue to identify the task running in the process list.

1. Hourly Task: 10min ```cd ~/3cqsbot_TAsafe && python 3cqsbot_TAsafe.py```
2. Hourly Task: 11min ```cd ~/3cqsbot_Urmav6 && python 3cqsbot_Urmav6.py```
3. Hourly Task: 12min ```cd ~/3cqsbot_Urmav6 && python 3cqsbot_Mars.py```

In case you have to kill a process you can know easily identify your task to kill after fetching the process list under `Running tasks`
Check the log files in the scheduled task under `Actions` for errors.

### Updating 3cqsbot

If you want to update 3cqsbot to the newest version open the Bash console. Change to your desired 3cqsbot directory with following commands

```bash
cd 3cqsbot
git pull
pip3 install -r requirements.txt
```

Check the config.ini.example for new config options. Make sure to update your existent config.ini for the new options with the integrated
PythonAnywhere editor (Files menue).

## Debugging

The script can be started with

```bash
python3 3cqsbot.py -l debug
```

do show debug logging

## Bug reports

Please submit bugs or problems through the Github [issues page](https://github.com/TBMoonwalker/3cqsbot/issues).

## Donation

If you like to support this project, you can donate to the following wallet:

- USDT or BUSD (BEP20 - Binance Smart Chain): 0xB3C6DD82a203E3b6f399187DB265AdC664E2beF9
