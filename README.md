# Summary
The 3cqsbot can be used to start and stop [3commas](https://3commas.io) dca bots with the help of the 3cqs signals. You can subscribe to the [telegram channel](https://t.me/The3CQSBot) to receive these signals. If you have any questions regarding the signals, please contact the developer [directly](https://www.3cqs.com/contact/).

# Disclaimer
**The 3cqsbot is meant to be used for educational purposes only. Use with real funds at your own risk**

# Prerequisites/Installation

## 3CQS Signals Bot

Join the telegram channel [telegram channel](https://t.me/The3CQSBot) according to the official Telegram [documentation](https://core.telegram.org/api/obtaining_api_id)

Wait for the signals. Actually the signals are in a beta phase and you have to be chosen to get them. Be patient if they not arrive after joining

## Telegram API
In the meantime create your [telegram api account](https://my.telegram.org/apps) and insert them into `api_id` and `api_hash` fields in the *'telegram'* section of the `config.ini`

## 3Commas API
Create a [3commas api account](https://3commas.io/api_access_tokens) too and insert the values in the `key` and `secret` fields in the *'commas'* section of the `config.ini`

**Permissions needed:** BotsRead, BotsWrite, AccountsRead

## Operating Systems
- MacOS
- Linux
    - Ubuntu
- Windows
    - untested (please let me know if it works)
- Docker

## Installation
### Python modules
pip3 install requirements.txt

# Configuration (config.ini)
Copy the `config.ini.example` to `config.ini` and change your settings regarding the available settings below. The value type doesn't matter, because Pythons configparser is taking care of the types. So you don't need '' or "" around the values.

## Telegram
Name | Type | Mandatory | Values(default) | Description
------------ | ------------ | ------------ | ------------ | ------------
api_id | string | YES |   | Telegram API ID
api_hash | string | YES |   | Telegram API Hash
sessionfile | string | YES | (tgsession) | Telegram sessionfile location

## 3Commas
Name | Type | Mandatory | Values(default) | Description
------------ | ------------ | ------------ | ------------ | ------------
chatroom | string | YES | (3C Quick Stats) | Name of the chatroom - on Windows please use the ID 5011413076
key | string | YES |    | 3Commas API Key
secret | string | YES | | 3Commas API Secret
timeout | integer | YES | (3) | Timeout waiting for a 3Commas api response
retries | integer | YES | (5) | Number of retries after a 3Commas api call was not successful
delay_between_retries | number | YES | (2.0) | Waiting time factor between unsuccessful retries 

## DCABot configuration

Name | Type | Mandatory | Values(default) | Description
------------ | ------------ | ------------ | ------------ | ------------
prefix | string | YES | (3CQSBOT)  | The name prefix of the created bot
subprefix | string | YES | (MULTI) | Subprefix of the bot (Best would be SINGLE or MULTI)
suffix | string | YES | (TA_SAFE) | Suffix in the bot name - could be the used bot configuration
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

Name | Type | Mandatory | Values(default) | Description
------------ | ------------ | ------------ | ------------ | ------------
market | string | YES | (USDT)  | Trading market (Example: BUSD, USDT, USDC)
trade_mode | string | YES | (paper) real   | Real or Paper trading mode
account_name | string | YES | (Paper trading 123456)  | Account name for trading. Can be found unter "My Exchanges". 
symrank_limit | integer | YES | (10000) | Maximum value of bot creation according to the Symrank
volatility_limit | number | YES | (10000) | Maximum value of bot creation according to the volatility
price_action_limit | number | YES | (10000) | Maximum value of bot creation according to the price action
topcoin_limit | integer | YES | (10000) | Maximum number of coins according to the CoinGecko toplist
deal_mode | string | YES | ( [{"options": {"time": "3m", "points": "100"}, "strategy": "rsi"}]) signal | Method how the script is creating new deals in multipair bot
limit_initial_pairs | boolean | YES | (false) | Limit initial pairs to the max number of deals (MAD) - bot chooses the top pairs
btc_pulse | boolean | YES | (false) | Activates or deactivates the bots according to Bitcoins behaviour. If Bitcoin is going down, the bot will be disabled
delete_single_bots | boolean | YES | (false) | If set to yes, bots without an active deal will be deleted in single bot configuration
trailing | boolean | YES | (false) true | Trailing profit enabled
trailing_deviation | number | YES | (0.2) | Deviation of trailing profit

### Deal Mode explanation

**single=true deal_mode=signal**

A single bot for a specific pair (the signal) will be created when the signal fits your configured filters and when the signal is a "START" signal. The deal will be start immediately. The bot will be disabled on a stop signal for this specific pair. If `delete_single_bots`is set to true, the script tries do delete the bot. This only works, when no deal is running.

**single=true deal_mode="self asigned strategy"**

Everything is the same as with the other single mode, but the deals are started dependent on your configured `deal_mode` strategy.

**single=false deal_mode=signal**

A multi bot will be created with the top 30 Symrank list (initical call to /symrank). A new deal will be started when a new signal is coming in. 

If it is a STOP/START signal which is not from an existing pair a random pair from the initial top 30 Symrank list is used for a new deal. 

If it is a START signal from an existing pair or a freshly added pair, exactly that pair is used for a new deal.

Pairs will be deleted from the list during a STOP signal and added with a START signal, if it fits the filters.

**single=false deal_mode="self asigned strategy"**

Everything is the same as with the other multi mode, but the deals are started dependent on your configured `deal_mode` strategy.

## Filter

Name | Type | Mandatory | Values(default) | Description
------------ | ------------ | ------------ | ------------ | ------------
symrank_limit | integer | YES | (10000) | Bots will be created when the symrank value is under this limit
volatility_limit | number | YES | (10000) | Bots will be created when the volatility value is under this limit
price_action_limit | number | YES | (10000) | Bots will be created when the price_action value is under this limit
topcoin_limit | integer | YES | (10000) | Token pair has to be in the configured topcoin limit to be traded by the bot
deal_mode | string | YES | ([{"options": {"time": "3m", "points": "100"}, "strategy": "rsi"}]) signal | Deal strategy how the script is creating new deals in multipair bot - for more see the "Deal Modes" section
limit_initial_pairs | boolean | YES | (false) | Limit initial pairs to the max number of deals (MAD) - bot chooses the top pairs
btc_pulse | boolean | YES | (false) | Activates or deactivates the bots according to Bitcoins behaviour. If Bitcoin is going down, the bot will be disabled
token_denylist | array | NO | ([BTC_USDT, ETH_USDT, BUSD_USDT, USDC_USDT, USDT_USDT]) | Denylist of pairs which not be used by the bot for new deals

### BTC Pulse
BTCPulse is a simple strategy which monitors BTC Price Action to start new deals or just put the bot to sleep ( no new deals but active deals keep running) based on:-
If BTC is in upswing new deals are started 
If BTC is dumping no new deals are started

BTCPulse hence is determined using the 2 factors :-
% price change of BTC in the last 15 minutes or
Fast and Slow moving EMAs crossses

Please test this strategy on paper before putting real money on it.
TBMoonWalker or IamtheOnewhoKnocks take no responsibility for losses occurred due to the script/strategy

**Again, please use 3cqsbot only on paper trading. Usage with real funds is at your own risk**


### Deal Modes
This section is all about the deal start signals. Tested are the following modes:

- `signal` --> starting the bot after a 3CQS signal
- `[{"options": {"time": "3m", "points": "100"}, "strategy": "rsi"}]` --> start the bot when the RSI-7 value is under 100 in the 3 minute view

More modes are possible, but not tested. You can minimize the value of the RSI-7 entry point for example. A whole list of deal signals can be found with the api call `GET /ver1/bots/strategy_list`. Details can be found under: https://github.com/3commas-io/3commas-official-api-docs/blob/master/bots_api.md

# Run
If you get signals, you can run the script with the command: 

```
python3 3cqsbot.py
```
When running for the first time, you will be asked for your Telegram phonenumber and you will get a code you have to insert!

# Docker
## Create the docker image
```
docker build -t "your repo name"/3cqsbot:"version number"
```
## Create a persistent volume for your Telegram session file
```
docker volume create session
```

## Create your .env file
Copy the `.env.example` file to `.env`and change the settings. The same settings as in the config.ini can be used

## Run your container
```
docker run --name 3cqsbot --volume session:/App/session --env-file .env -d "your repo name"/3cqsbot:"version number"
```

## Logfile monitoring
```
docker logs --follow 3cqsbot
```

# Debugging
The script can be started with

```
python3 3cqsbot.py -l debug
```

do show debug logging

# Bug reports
Please submit bugs or problems through the Github [issues page](https://github.com/TBMoonwalker/3cqsbot/issues).

# Donation
If you like to support this project, you can donate to the following wallet:

- USDT or BUSD (BEP20 - Binance Smart Chain): 0xB3C6DD82a203E3b6f399187DB265AdC664E2beF9