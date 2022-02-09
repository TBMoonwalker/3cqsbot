# Summary
The 3cqsbot can be used to start and stop [3commas](https://3commas.io) dca bots with the help of the 3cqs signals. You can subscribe to the [telegram channel](https://t.me/The3CQSBot) to receive these signals. If you have any questions regarding the signals, please contact the developer [directly](https://www.3cqs.com/contact/).

# Disclaimer
**The 3cqsbot is meant to be used for educational purposes only. Use with real funds at your own risk**

# Prerequisites

## Python

- Python3
- py3cw Module (pip3 install py3cw)
- telethon Module (pip3 install telethon)

## Operating Systems
- MacOS
- Linux
    - Ubuntu
- Windows
    - untested (please let me know if it works)

# Setup
First of all, the value type doesn't matter, because Pythons configparser is taking care of the types. So you don't need '' or "" around the values.

## API configuration
Name | Type | Mandatory | Values(default) | Description
------------ | ------------ | ------------ | ------------ | ------------
api_id | string | YES |   | Telegram API ID
api_hash | string | YES |   | Telegram API Hash
sessionfile | string | YES | (tgsession) | Telegram sessionfile location
key | string | YES |    | 3Commas API Key
secret | string | YES | | 3Commas API Secret

### 3CQS Signals

Join the telegram channel [telegram channel](https://t.me/The3CQSBot) according to the official Telegram [documentation](https://core.telegram.org/api/obtaining_api_id)

Wait for the Signals. Actually the signals are in a beta phase and you have to be chosen to get them. Be patient if they not arrive after joining

### Telegram API
In the meantime create your [telegram api account](https://my.telegram.org/apps) and insert them into `api_id` and `api_hash` fields in the *'telegram'* section of the `config.ini`

### 3Commas API
Create a [3commas api account](https://3commas.io/api_access_tokens) too and insert the values in the `key` and `secret` fields in the *'commas'* section of the `config.ini`

**Permissions needed:** BotsRead, BotsWrite, AccountsRead

## DCABot configuration

Name | Type | Mandatory | Values(default) | Description
------------ | ------------ | ------------ | ------------ | ------------
suffix | string | YES | (3CQSBOT)  | The name suffix of the created bot
tp | number | YES |   | Take profit in percent (Example: 1.5)
bo | number | YES |    | Base order volume (Example: 10)
so | number | YES | | Safety order volume (Example: 10)
os | number | YES | | Safety order volume scale (Example: 1.05)
ss | number | YES | | Safety order step scale (Example: 1)
sos | number | YES | | Price deviation to open safety orders (Example: 2.4)
mad | integer | YES | | Max active deals (Example: 10)
max | integer | YES | | Max active safety trades count (Example: 1)
mstc | integer | YES | | Max safety trades count (Example: 25)
sdsp | integer | NO | | Simultaneous deals per same pair (only Multibot)
single | boolean | YES | false (true) | Type of Bot creation (Example: true for Single DCA Bots)
btc_min_vol | number | YES |  | Minimum 24h volume trading calculated in BTC (Example: 100)

Configure the 'dcabot' section in the `config.ini` according to your favourite bot configuration. If you don't have any, please take a look at [this site](https://www.buymeacoffee.com/Ribsy/posts) for published settings.

Set the `single` value in the `config.ini` to true. 3cqsbot will create multiple dca bots (according to your max deal size). 

**Support for a DCA multivalue pair bot comes later.**

## Trading mode

### Market
Name | Type | Mandatory | Values(default) | Description
------------ | ------------ | ------------ | ------------ | ------------
market | string | YES |   | Trading market (Example: BUSD, USDT, USDC)
trade_mode | string | YES | real(paper)   | Real or Paper trading mode
exchange | string | YES | (Paper trading account)  | Exchange of the chosen account (Example: Binance, Paper trading account, FTX )
symrank_limit | integer | YES | (10000) | Maximum value of bot creation according to the Symrank
volatility_limit | number | YES | (10000) | Maximum value of bot creation according to the volatility
price_action_limit | number | YES | (10000) | Maximum value of bot creation according to the price action

**Again, please use 3cqsbot only on paper trading. Usage with real funds is at your own risk**

# Run
If you get signals, you can run the script with the command: 

```
python3 3cqsbot.py
```
When running for the first time, you will be asked for your Telegram phonenumber and you will get a code you have to insert!

# Bug reports
Please submit bugs or problems through the Github [issues page](https://github.com/TBMoonwalker/3cqsbot/issues).