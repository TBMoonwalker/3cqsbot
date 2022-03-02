#!/bin/sh

# prepare 3cqsbot configuration
cp config.ini.example config.ini

# General
sed -i "s/debug = false$/debug = $DEBUG/" config.ini

# Telegram settings
sed -i "s/api_id =$/api_id = $TG_ID/" config.ini
sed -i "s/api_hash =$/api_hash = $TG_HASH/" config.ini
sed -i "s|sessionfile = tgsession$|sessionfile = $TG_SESSIONFILE|" config.ini

# 3Commas settings
sed -i "s/key =$/key = $API_KEY/" config.ini
sed -i "s/secret =$/secret = $API_SECRET/" config.ini

# DCABOT settings
sed -i "s/prefix = 3CQSBOT$/prefix = $DCABOT_PREFIX/" config.ini
sed -i "s/subprefix = MULTI$/subprefix = $DCABOT_SUBPREFIX/" config.ini
sed -i "s/suffix = TA_SAFE$/suffix = $DCABOT_SUFFIX/" config.ini
sed -i "s/tp = 1.5$/tp = $DCABOT_TP/" config.ini
sed -i "s/bo = 11$/bo = $DCABOT_BO/" config.ini
sed -i "s/so = 11$/so = $DCABOT_SO/" config.ini
sed -i "s/^os = 1.05$/os = $DCABOT_OS/" config.ini
sed -i "s/ss = 1$/ss = $DCABOT_SS/" config.ini
sed -i "s/sos = 2.4$/sos = $DCABOT_SOS/" config.ini
sed -i "s/mad = 3$/mad = $DCABOT_MAD/" config.ini
sed -i "s/max = 1$/max = $MAX/" config.ini
sed -i "s/mstc = 25$/mstc = $DCABOT_MSTC/" config.ini
sed -i "s/sdsp = 1$/sdsp = $DCABOT_SDSP/" config.ini
sed -i "s/single = false$/single = $DCABOT_SINGLE/" config.ini
sed -i "s/btc_min_vol = 100$/btc_min_vol = $DCABOT_BTC_MIN_VOL/" config.ini

# General settings
sed -i "s/market = USDT$/market = $MARKET/" config.ini
sed -i "s/trade_mode = paper$/trade_mode = $TRADE_MODE/" config.ini
sed -i "s/account_name = Paper trading 123456$/account_name = $ACCOUNT/" config.ini
sed -i "s/symrank_limit = 10000$/symrank_limit = $SYMRANK_LIMIT/" config.ini
sed -i "s/volatility_limit = 10000$/volatility_limit = $VOLATILITY_LIMIT/" config.ini
sed -i "s/price_action_limit = 10000$/price_action_limit = $PRICE_ACTION_LIMIT/" config.ini
sed -i "s/topcoin_limit = 10000$/topcoin_limit = $TOPCOIN_LIMIT/" config.ini
sed -i "s/deal_mode = .*/deal_mode = $DEAL_MODE/" config.ini
sed -i "s/trailing = false$/trailing = $TRAILING/" config.ini
sed -i "s/trailing_deviation = 0.2$/trailing_deviation = $TRAILING_DEVIATION/" config.ini
sed -i "s/limit_initial_pairs = false$/limit_initial_pairs = $LIMIT_INIT_PAIRS/" config.ini
sed -i "s/btc_pulse = false$/btc_pulse = $BTC_PULSE/" config.ini
sed -i "s/token_denylist = .*/token_denylist = $DENYLIST/" config.ini

python3 -u 3cqsbot.py
