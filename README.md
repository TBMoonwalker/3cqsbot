# Summary
The 3cqsbot can be used to start and stop [3commas](https://3commas.io) dca bots with the help of the 3cqs signals. You can subscribe to the [telegram channel](https://t.me/The3CQSBot) to receive these signals. If you have any questions regarding the signals, please contact the developer [directly](https://www.3cqs.com/contact/).

# Disclaimer
**The 3cqsbot is meant to be used for educational purposes only. Use with real funds at your own risk**

# Prerequisites/Installation

## Python

- Python3
- py3cw module (pip3 install py3cw)
- telethon module (pip3 install telethon)
- yfinance module
- numpy module

## Operating Systems
- MacOS
- Linux
    - Ubuntu
- Windows
    - untested (please let me know if it works)

## Installation
### TA-Lib
Before the ta-lib python module can be installed, you need the library of ta-lib for your system. This link show you how do to that (under Dependencies):

https://mrjbq7.github.io/ta-lib/install.html

### Python modules
pip3 install requirements.txt

# Setup
First of all, the value type doesn't matter, because Pythons configparser is taking care of the types. So you don't need '' or "" around the values.

## API configuration
Name | Type | Mandatory | Values(default) | Description
------------ | ------------ | ------------ | ------------ | ------------
api_id | string | YES |   | Telegram API ID
api_hash | string | YES |   | Telegram API Hash
sessionfile | string | YES | (tgsession) | Telegram sessionfile location
chatroom | string | YES | (3C Quick Stats) | Name of the chatroom - on Windows please use the ID 5011413076
key | string | YES |    | 3Commas API Key
secret | string | YES | | 3Commas API Secret

### 3CQS Signals

Join the telegram channel [telegram channel](https://t.me/The3CQSBot) according to the official Telegram [documentation](https://core.telegram.org/api/obtaining_api_id)

Wait for the signals. Actually the signals are in a beta phase and you have to be chosen to get them. Be patient if they not arrive after joining

### Telegram API
In the meantime create your [telegram api account](https://my.telegram.org/apps) and insert them into `api_id` and `api_hash` fields in the *'telegram'* section of the `config.ini`

### 3Commas API
Create a [3commas api account](https://3commas.io/api_access_tokens) too and insert the values in the `key` and `secret` fields in the *'commas'* section of the `config.ini`

**Permissions needed:** BotsRead, BotsWrite, AccountsRead

## DCABot configuration

Name | Type | Mandatory | Values(default) | Description
------------ | ------------ | ------------ | ------------ | ------------
prefix | string | YES | (3CQSBOT)  | The name prefix of the created bot
subprefix | string | YES | (MULTI) | Subprefix of the bot (Best would be SINGLE or MULTI)
suffix | string | YES | (TA_SAFE) | Suffix in the bot name - could be the used bot configuration
tp | number | YES | (1.5)  | Take profit in percent
bo | number | YES | (11)   | Base order volume
so | number | YES | (11) | Safety order volume
os | number | YES | (1.05) | Safety order volume scale
ss | number | YES | (1) | Safety order step scale
sos | number | YES | (2.4) | Price deviation to open safety orders
mad | integer | YES | (3) | Max active deals
max | integer | YES | (1) | Max active safety trades count
mstc | integer | YES | (25) | Max safety trades count
sdsp | integer | NO | (1) | Simultaneous deals per same pair (only Multibot)
single | boolean | YES | (false) true | Type of Bot creation (True for Single DCA Bots)
btc_min_vol | number | YES | (100) | Minimum 24h volume trading calculated in BTC

Configure the 'dcabot' section in the `config.ini` according to your favourite bot configuration. 

If you don't have any, please take a look at [this site](https://www.buymeacoffee.com/Ribsy/posts) for published settings.

Default configuration is based on Trade Alts Safer settings: https://discord.gg/tradealts


## Trading mode

### Market
Name | Type | Mandatory | Values(default) | Description
------------ | ------------ | ------------ | ------------ | ------------
market | string | YES | (USDT)  | Trading market (Example: BUSD, USDT, USDC)
trade_mode | string | YES | (paper) real   | Real or Paper trading mode
exchange | string | YES | (Paper trading account)  | Exchange of the chosen account (Example: Binance, Paper trading account, FTX )
symrank_limit | integer | YES | (10000) | Maximum value of bot creation according to the Symrank
volatility_limit | number | YES | (10000) | Maximum value of bot creation according to the volatility
price_action_limit | number | YES | (10000) | Maximum value of bot creation according to the price action
topcoin_limit | integer | YES | (10000) | Maximum number of coins according to the CoinGecko toplist
deal_mode | string | YES | (rsi) signal | Method how the script is creating new deals in multipair bot.
limit_initial_pairs | boolean | YES | (false) | Limit initial pairs to the max number of deals (MAD) - bot chooses the top pairs
btc_pulse | boolean | YES | (false) | Activates or deactivates the bots according to Bitcoins behaviour. If Bitcoin is going down, the bot will be disabled.
trailing | boolean | YES | (false) true | Trailing profit enabled
trailing_deviation | number | YES | (0.2) | Deviation of trailing profit


**Again, please use 3cqsbot only on paper trading. Usage with real funds is at your own risk**

# Run
If you get signals, you can run the script with the command: 

```
python3 3cqsbot.py
```
When running for the first time, you will be asked for your Telegram phonenumber and you will get a code you have to insert!

# Bug reports
Please submit bugs or problems through the Github [issues page](https://github.com/TBMoonwalker/3cqsbot/issues).