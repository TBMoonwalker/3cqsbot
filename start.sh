#!/bin/sh


# General
echo "[general]" > config.ini
[ $DEBUG ] && echo "debug = $DEBUG" >> config.ini
[ $LOGFILE ] && echo "log_to_file = $LOGFILE" >> config.ini
[ $LOGFILEPATH ] && echo "log_file_path = $LOGFILEPATH" >> config.ini
[ $LOGFILESIZE ] && echo "log_file_size = $LOGFILESIZE" >> config.ini
[ $LOGFILECOUNT ] && echo "log_file_count = $LOGFILECOUNT" >> config.ini

# Telegram settings
echo "[telegram]" >> config.ini
[ $TG_ID ] && echo "api_id = $TG_ID" >> config.ini
[ $TG_HASH ] && echo "api_hash = $TG_HASH" >> config.ini
[ $TG_SESSIONFILE ] && echo "sessionfile = $TG_SESSIONFILE" >> config.ini
[ $CHATROOM ] && echo "chatroom = $CHATROOM" >> config.ini

# 3Commas settings
echo "[commas]" >> config.ini
[ $API_KEY ] && echo "key = $API_KEY" >> config.ini
[ $API_SECRET ] && echo "secret = $API_SECRET" >> config.ini
[ $API_TIMEOUT ] && echo "timeout = $API_TIMEOUT" >> config.ini
[ $API_RETRIES ] && echo "retries = $API_RETRIES" >> config.ini
[ $API_RETRY_DELAY ] && echo "delay_between_retries = $API_RETRY_DELAY" >> config.ini
[ $SYS_BOT_VALUE ] && echo "system_bot_value = $SYS_BOT_VALUE" >> config.ini

# DCABOT settings
echo "[dcabot]" >> config.ini
[ $DCABOT_PREFIX ] && echo "prefix = $DCABOT_PREFIX" >> config.ini
[ $DCABOT_SUBPREFIX ] && echo "subprefix = $DCABOT_SUBPREFIX" >> config.ini
[ $DCABOT_SUFFIX ] && echo "suffix = $DCABOT_SUFFIX" >> config.ini
[ $DCABOT_TP ] && echo "tp = $DCABOT_TP" >> config.ini
[ $DCABOT_BO ] && echo "bo = $DCABOT_BO" >> config.ini
[ $DCABOT_SO ] && echo "so = $DCABOT_SO" >> config.ini
[ $DCABOT_OS ] && echo "os = $DCABOT_OS" >> config.ini
[ $DCABOT_SS ] && echo "ss = $DCABOT_SS" >> config.ini
[ $DCABOT_SOS ] && echo "sos = $DCABOT_SOS" >> config.ini
[ $DCABOT_MAD ] && echo "mad = $DCABOT_MAD" >> config.ini
[ $DCABOT_MAX ] && echo "max = $DCABOT_MAX" >> config.ini
[ $DCABOT_MSTC ] && echo "mstc = $DCABOT_MSTC" >> config.ini
[ $DCABOT_SDSP ] && echo "sdsp = $DCABOT_SDSP" >> config.ini
[ $DCABOT_SINGLE ] && echo "single = $DCABOT_SINGLE" >> config.ini
[ $DCABOT_SINGLE_COUNT ] && echo "single_count = $DCABOT_SINGLE_COUNT" >> config.ini
[ $DCABOT_BTC_MIN_VOL ] && echo "btc_min_vol = $DCABOT_BTC_MIN_VOL" >> config.ini

# Trading settings
echo "[trading]" >> config.ini
[ $MARKET ] && echo "market = $MARKET" >> config.ini
[ $TRADE_MODE ] && echo "trade_mode = $TRADE_MODE" >> config.ini
[ "$ACCOUNT" ] && echo "account_name = $ACCOUNT" >> config.ini
[ $DELETE_SINGLE ] && echo "delete_single_bots = $DELETE_SINGLE" >> config.ini
[ $UPDATE_SINGLE ] && echo "singlebot_update = $UPDATE_SINGLE" >> config.ini
[ $TRAILING ] && echo "trailing = $TRAILING" >> config.ini
[ $TRAILING_DEVIATION ] && echo "trailing_deviation = $TRAILING_DEVIATION" >> config.ini

# Filter settings
echo "[filter]" >> config.ini
[ $SYMRANK_SIGNAL ] && echo "symrank_signal = $SYMRANK_SIGNAL" >> config.ini
[ $SYMRANK_LIMIT_MIN ] && echo "symrank_limit_min = $SYMRANK_LIMIT_MIN" >> config.ini
[ $SYMRANK_LIMIT_MAX ] && echo "symrank_limit_max = $SYMRANK_LIMIT_MAX" >> config.ini
[ $VOLATILITY_LIMIT_MIN ] && echo "volatility_limit_min = $VOLATILITY_LIMIT_MIN" >> config.ini
[ $VOLATILITY_LIMIT_MAX ] && echo "volatility_limit_max = $VOLATILITY_LIMIT_MAX" >> config.ini
[ $PRICE_ACTION_LIMIT_MIN ] && echo "price_action_limit_min = $PRICE_ACTION_LIMIT_MIN" >> config.ini
[ $PRICE_ACTION_LIMIT_MAX ] && echo "price_action_limit_max =$PRICE_ACTION_LIMIT_MAX" >> config.ini
[ $TOPCOIN_LIMIT ] && echo "topcoin_limit = $TOPCOIN_LIMIT" >> config.ini
[ $TOPCOIN_VOLUME ] && echo "topcoin_volume = $TOPCOIN_VOLUME" >> config.ini
[ $TOPCOIN_EXCHANGE ] && echo "topcoin_exchange = $TOPCOIN_EXCHANGE" >> config.ini
[ "$DEAL_MODE" ] && echo "deal_mode = ${DEAL_MODE}"  >> config.ini
[ $LIMIT_INIT_PAIRS ] && echo "limit_init_pairs = $LIMIT_INIT_PAIRS" >> config.ini
[ $RANDOM_PAIR ] && echo "random_pair = $RANDOM_PAIR" >> config.ini
[ $BTC_PULSE ] && echo "btc_pulse = $BTC_PULSE" >> config.ini
[ $EXT_BOTSWITCH ] && echo "ext_botswitch = $EXT_BOTSWITCH" >> config.ini
[ "$DENYLIST" ] && echo "token_denylist = $DENYLIST" >> config.ini

python3 -u 3cqsbot.py
