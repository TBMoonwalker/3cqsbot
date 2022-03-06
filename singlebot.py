import re
import json

from signals import Signals

class SingleBot:
    def __init__(self, tg_data, bot_data, account_data, config, p3cw, logging):
        self.tg_data = tg_data
        self.bot_data = bot_data
        self.account_data = account_data
        self.config = config
        self.p3cw = p3cw
        self.logging = logging
        self.signal = Signals(logging)
        self.prefix = self.config['dcabot']['prefix']
        self.subprefix = self.config['dcabot']['subprefix']
        self.suffix = self.config['dcabot']['suffix']

    def strategy(self):
        if self.config['filter']['deal_mode'] == "signal":
            strategy = [{"strategy":"nonstop"}]
        else:
            strategy = json.loads(self.config['filter']['deal_mode'])

        return strategy

    def deal_data(self):
        account = self.account_data
        deals = []

        error, data = self.p3cw.request(
            entity="deals",
            action="",
            action_id=account['id'],
            additional_headers={'Forced-Mode': self.config['trading']['trade_mode']},
            payload={
                "limit": 1000,
                "scope": "active"
            }
        )

        if error:
            self.logging.error(error['msg'])
        else:
            for deal in data:
                if (self.prefix + "_" +  self.subprefix + "_" + self.config['trading']['market']) in deal['bot_name']:
                    deals.append(deal['bot_name'])
        self.logging.debug(str(data))
        self.logging.debug(deals)
        self.logging.debug("Deal count: " + str(len(deals)))
        
        return len(deals)

    def enable(self, bot):
       
        # Enables an existing bot
        error, data = self.p3cw.request(
            entity="bots",
            action="enable",
            action_id=str(bot['id']),
            additional_headers={'Forced-Mode': self.config['trading']['trade_mode']},
        )

        if error:
            self.logging.error(error['msg'])
        else:
            self.logging.info("Enabling bot " + bot['name'])


    def disable(self, bot, allbots=False):
        # Disable all bots
        error = {}

        if allbots:
            
            self.logging.debug("Disabling all bots")

            for bots in bot:
                if (self.prefix + "_" +  self.subprefix + "_" + self.config['trading']['market']) in bots['name']:
                    error, data = self.p3cw.request(
                        entity="bots",
                        action="disable",
                        action_id=str(bots['id']),
                        additional_headers={'Forced-Mode': self.config['trading']['trade_mode']},
                    )

                    if error:
                        self.logging.error(error['msg'])
                    else:
                        self.logging.info("Disabling bot " + bots['name'])
        else:
            # Disables an existing bot
            error, data = self.p3cw.request(
                entity="bots",
                action="disable",
                action_id=str(bot['id']),
                additional_headers={'Forced-Mode': self.config['trading']['trade_mode']},
            )

            if error:
                self.logging.error(error['msg'])
            else:
                self.logging.info("Disabling bot " + bot['name'])

    def create(self):
        # Creates a single bot with start signal
        self.logging.info("Create single bot with pair " + self.tg_data['pair'])

        error, data = self.p3cw.request(
            entity="bots",
            action="create_bot",
            additional_headers={'Forced-Mode': self.config['trading']['trade_mode']},
            payload={
                "name": self.prefix + "_" + self.subprefix + "_" + self.tg_data['pair'] + "_" + self.suffix,
                "account_id": self.account_data['id'],
                "pairs": self.tg_data['pair'],
                "base_order_volume": self.config['dcabot'].getfloat('bo'),
                "take_profit": self.config['dcabot'].getfloat('tp'),
                "safety_order_volume": self.config['dcabot'].getfloat('so'),
                "martingale_volume_coefficient": self.config['dcabot'].getfloat('os'),
                "martingale_step_coefficient": self.config['dcabot'].getfloat('ss'),
                "max_safety_orders": self.config['dcabot'].getint('mstc'),
                "safety_order_step_percentage": self.config['dcabot'].getfloat('sos'),
                "take_profit_type": "total",
                "active_safety_orders_count": self.config['dcabot'].getint('max'),
                "strategy_list": self.strategy(),
                "trailing_enabled": self.config['trading'].getboolean('trailing'),
                "trailing_deviation": self.config['trading'].getfloat('trailing_deviation'),
                "min_volume_btc_24h": self.config['dcabot'].getfloat('btc_min_vol')
            }
        )

        if error:
            self.logging.error(error['msg'])
        else:
            self.enable(data)
            

    def delete(self, bot):
        if (bot['active_deals_count'] == 0 and
            self.config['trading'].getboolean('delete_single_bots')):
            # Deletes a single bot with stop signal
            self.logging.info("Delete single bot with pair " + self.tg_data['pair'])
            error, data = self.p3cw.request(
                entity="bots",
                action="delete",
                action_id=str(bot['id']),
                additional_headers={'Forced-Mode': self.config['trading']['trade_mode']},
            )
            
            if error:
                self.logging.error(error['msg'])
        else:
            self.logging.info("Cannot delete single bot, because of active deals or configuration. Disabling it!")
            self.disable(bot, False)


    def trigger(self):
        # Triggers a single bot deal
        self.logging.info("Start trigger")
        new_bot = True
        pair = self.tg_data['pair']

        if self.bot_data:
            for bot in self.bot_data:
                if (self.prefix + "_" +  self.subprefix + "_" + pair + "_" + self.suffix) in bot['name']:
                    new_bot = False
                    break

            if new_bot:
                if (self.tg_data['action'] == "START" and
                    self.deal_data() < self.config['dcabot'].getint('mad')):
                    
                    pair = self.signal.topcoin(pair, self.config['filter'].getint('topcoin_limit'))
                    if pair:
                        self.logging.info("No single dcabot for " + pair + " found - creating one")
                        self.create()
                    else:
                        self.logging.info("Pair " + pair + " is not in the top coin list!")
                else:
                    self.logging.info("Maximum deals reached or stop command on a non-existing bot!")
            else:
                self.logging.debug("Pair: " + pair)
                self.logging.debug("Bot-Name: " + bot['name'])
                
                if self.tg_data['action'] == "START":
                    if self.deal_data() < self.config['dcabot'].getint('mad'):
                        self.enable(bot)
                else:
                    self.delete(bot)
        
        else:
            self.logging.info("No dcabots found")
            self.create()
