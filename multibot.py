import random

class MultiBot:
    def __init__(self, tg_data, bot_data, account_data, pair_data, config, p3cw, logging):
        self.tg_data = tg_data
        self.bot_data = bot_data
        self.account_data = account_data
        self.pair_data = pair_data
        self.config = config
        self.p3cw = p3cw
        self.logging = logging

    
    def strategy(self):
        if self.config['trading']['deal_mode'] == "signal":
            strategy = [{"strategy":"manual"}]
        else:
            strategy = [{"options": {"time": "3m", "points": "100"}, "strategy": "rsi"}]

        return strategy


    def enable(self, bot):
        # Enables an existing bot
        self.logging.info("Enabling bot")
        error, data = self.p3cw.request(
            entity="bots",
            action="enable",
            action_id=str(bot['id']),
            additional_headers={'Forced-Mode': self.config['trading']['trade_mode']},
        )


    def new_deal(self, bot, triggerpair):
        # Enables an existing bot
        if triggerpair:
            pair = triggerpair
        else:
            pair = random.choice(bot['pairs'])

        self.logging.info("Trigger new deal with pair " + pair)
        error, data = self.p3cw.request(
            entity="bots",
            action="start_new_deal",
            action_id=str(bot['id']),
            additional_headers={'Forced-Mode': self.config['trading']['trade_mode']},
            payload={
                "pair": pair
            }
        )

        if error:
            if bot['active_deals_count'] ==  bot['max_active_deals']:
                self.logging.info('Max deals count reached, not adding a new one.')
            else:
                self.logging.error(error['msg'])


    def create(self):
        # Creates a multi bot with start signal
        new_bot = True
        pairs = []

        deal_strategy = self.strategy()
           
        for bot in self.bot_data:
            if (self.config['dcabot']['prefix'] + "_" + "MULTIBOT") in bot['name']:
                new_bot = False
                break
                
        if new_bot:
            for pair in self.tg_data:
                pair = self.config['trading']['market'] + "_" + pair
                if pair in self.pair_data:
                    pairs.append(pair)

            if self.config['trading'].getboolean('limit_initial_pairs'):
                # Limit pairs to the maximal deals (mad)
                if self.config['dcabot'].getint('mad') == 1:
                    maxpairs = 2
                elif self.config['dcabot'].getint('mad') <= len(pairs):
                    maxpairs = self.config['dcabot'].getint('mad')
                else:
                    maxpairs = len(pairs)

                pairs = pairs[0 : maxpairs]

            self.logging.info("Create multi bot with pairs " + str(pairs))
            error, data = self.p3cw.request(
                entity="bots",
                action="create_bot",
                additional_headers={'Forced-Mode': self.config['trading']['trade_mode']},
                payload={
                    "name": self.config['dcabot']['prefix'] + "_" + "MULTIBOT",
                    "account_id": self.account_data['id'],
                    "pairs": pairs,
                    "max_active_deals": self.config['dcabot'].getint('mad'),
                    "base_order_volume": self.config['dcabot'].getfloat('bo'),
                    "take_profit": self.config['dcabot'].getfloat('tp'),
                    "safety_order_volume": self.config['dcabot'].getfloat('so'),
                    "martingale_volume_coefficient": self.config['dcabot'].getfloat('os'),
                    "martingale_step_coefficient": self.config['dcabot'].getfloat('ss'),
                    "max_safety_orders": self.config['dcabot'].getint('mstc'),
                    "safety_order_step_percentage": self.config['dcabot'].getfloat('sos'),
                    "take_profit_type": "total",
                    "active_safety_orders_count": self.config['dcabot'].getint('max'),
                    "strategy_list": deal_strategy,
                    "trailing_enabled": self.config['trading'].getboolean('trailing'),
                    "trailing_deviation": self.config['trading'].getfloat('trailing_deviation'),
                    "allowed_deals_on_same_pair": 1,
                    "min_volume_btc_24h": self.config['dcabot'].getfloat('btc_min_vol')
                    # Create a function who automatically reduces the max active deals, if there are less pairs then max active deals or set allow allowed deals
                    # on same pair higher then 1
                }
            )

            if not error:
                self.enable(data)
                self.new_deal(data, triggerpair="")
            else:
                self.logging.error(error['msg'])


    def trigger(self, triggeronly=False):
        # Updates multi bot with new pairs
        triggerpair = ""
        deal_strategy = self.strategy()
        mad = self.config['dcabot'].getint('mad')

        self.logging.info("Got new 3cqs signal")

        for bot in self.bot_data:
            if (self.config['dcabot']['prefix'] + "_" + "MULTIBOT") in bot['name']:

                if not triggeronly:

                    pair = self.tg_data['pair']

                    if self.tg_data['action'] == "START":
                        triggerpair = pair
                        if pair in bot['pairs']:
                            self.logging.info("Pair is already included in the list")
                        else:
                            self.logging.info("Add pair " + pair)
                            bot['pairs'].append(pair)
                            lastpair = True

                            # Raise max active deals to minimum pairs or mad if possible
                            if len(bot['pairs']) >= mad:
                                self.logging.info("Pairs are over 'mad' - nothing to do")
                            else:
                                # Pairs are not back to mad - update it to the latest pair count
                                self.logging.info("Pairs still under 'mad' - Set max active deals to actual pairs")
                                mad = len(bot['pairs'])
                    else:
                        if pair in bot['pairs']:
                            self.logging.info("Remove pair " + pair)
                            bot['pairs'].remove(pair)

                            # Lower max active deals, when pairs are under mad
                            if len(bot['pairs']) < mad:
                                self.logging.info("Pairs are under 'mad' - Lower max active deals to actual pairs")
                                mad = len(bot['pairs'])

                        else:
                            self.logging.info("Pair is not included in the list, not removed")

                    error, data = self.p3cw.request(
                        entity="bots",
                        action="update",
                        action_id=str(bot['id']),
                        additional_headers={'Forced-Mode': self.config['trading']['trade_mode']},
                        payload={
                            "name": self.config['dcabot']['prefix'] + "_" + "MULTIBOT",
                            "account_id": self.account_data['id'],
                            "pairs": bot['pairs'],
                            "max_active_deals": mad,
                            "base_order_volume": self.config['dcabot'].getfloat('bo'),
                            "take_profit": self.config['dcabot'].getfloat('tp'),
                            "safety_order_volume": self.config['dcabot'].getfloat('so'),
                            "martingale_volume_coefficient": self.config['dcabot'].getfloat('os'),
                            "martingale_step_coefficient": self.config['dcabot'].getfloat('ss'),
                            "max_safety_orders": self.config['dcabot'].getint('mstc'),
                            "safety_order_step_percentage": self.config['dcabot'].getfloat('sos'),
                            "take_profit_type": "total",
                            "active_safety_orders_count": self.config['dcabot'].getint('max'),
                            "strategy_list": deal_strategy,
                            "trailing_enabled": self.config['trading'].getboolean('trailing'),
                            "trailing_deviation": self.config['trading'].getfloat('trailing_deviation'),
                            "allowed_deals_on_same_pair": 1,
                            "min_volume_btc_24h": self.config['dcabot'].getfloat('btc_min_vol')
                        }
                    )
                    
                    if error:
                        self.logging.error(error['msg'])
                else:
                    data = bot

                if (self.config['trading']['deal_mode'] == "signal" and data):
                    self.new_deal(data, triggerpair)
