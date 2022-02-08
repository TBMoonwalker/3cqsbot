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

## API configuration
- Join the telegram channel [telegram channel](https://t.me/The3CQSBot) 
- Wait for the Signals. Actually the signals are in a beta phase and you have to be chosen to get them. Be patient if they not arrive after joining
- In the meantime create your [telegram api account](https://my.telegram.org/apps) and insert them into `api_id` and `api_hash` fields in the *'telegram'* section of the `config.ini`
- Create a [3commas api account](https://3commas.io/api_access_tokens) too and insert the values in the `key` and `secret` fields in the *'commas'* section of the `config.ini`

## DCABot configuration
Configure the 'dcabot' section in the `config.ini` according to your favourite bot configuration. If you don't have any, please take a look at [this site](https://www.buymeacoffee.com/Ribsy/posts) for published settings.

## Single / Multi DCA Bot configuration
Set the `single` value in the `config.ini` to true. 3cqsbot will create multiple dca bots (according to your max deal size). 

**Support for a DCA multivalue pair bot comes later.**

## Trading mode

### Market
Set the *'trading'* values according to your situation. For paper trading in 3commas I take USDT as `market` value.
Examples:
- BUSD
- USDT
- USDC
- ....

### Trade mode
Can be `real` or `paper`

**Again, please use 3cqsbot only on paper trading. Usage with real funds is at your own risk**

### Exchange
The `exchange` value has to be set to the Exchange name in 3Commas. Examples are:
- Binance
- FTX
- ...

or 

- Paper Trading Account (for the paper trade mode)

# Run
If you get signals, you can run the script with the command: 

```
python3 3cqsbot.py
```
When running for the first time, you will be asked for your Telegram phonenumber and you will get a code you have to insert!

# Bug reports
Please submit bugs or problems through the Github [issues page](https://github.com/TBMoonwalker/3cqsbot/issues).