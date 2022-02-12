class SingleBot:
    def __init__(self, tg_data, bot_data, account_data, deal_data, config, p3cw, logging):
        self.tg_data = tg_data
        self.bot_data = bot_data
        self.account_data = account_data
        self.deal_data = deal_data
        self.config = config
        self.p3cw = p3cw
        self.logging = logging

    def enable(self, bot):
        # Enables an existing bot
        self.logging.info("Enabling bot " + bot['name'])
        error, data = self.p3cw.request(
            entity="bots",
            action="enable",
            action_id=str(bot['id']),
            additional_headers={'Forced-Mode': self.config['trading']['trade_mode']},
        )


    def disable(self, bot):
        # Disables an existing bot
        self.logging.info("Disabling bot " + bot['name'])
        error, data = self.p3cw.request(
            entity="bots",
            action="disable",
            action_id=str(bot['id']),
            additional_headers={'Forced-Mode': self.config['trading']['trade_mode']},
        )

    def create(self):
        # Creates a single bot with start signal
        self.logging.info("Create single bot with pair " + self.tg_data['pair'])
        error, data = self.p3cw.request(
            entity="bots",
            action="create_bot",
            additional_headers={'Forced-Mode': self.config['trading']['trade_mode']},
            payload={
                "name": self.config['dcabot']['prefix'] + "_" + self.tg_data['pair'],
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
                "strategy_list": [{"strategy":"nonstop"}],
                "trailing_enabled": self.config['trading'].getboolean('trailing'),
                "trailing_deviation": self.config['trading'].getfloat('trailing_deviation'),
                "min_volume_btc_24h": self.config['dcabot'].getfloat('btc_min_vol')
            }
        )

        if not error:
            self.enable(data)
        else:
            self.logging.error(error['msg'])


    def delete(self, bot):
        if bot['active_deals_count'] == 0:
            # Deletes a single bot with stop signal
            self.logging.info("Delete single bot with pair " + self.tg_data['pair'])
            error, data = self.p3cw.request(
                entity="bots",
                action="delete",
                action_id=str(bot['id']),
                additional_headers={'Forced-Mode': self.config['trading']['trade_mode']},
            )
        else:
            self.logging.info("Cannot delete single bot, because of active deals. Disabling it!")
            self.disable(bot)


    def trigger(self):
        # Triggers a single bot deal
        self.logging.info("Start trigger")
        new_bot = True

        if self.bot_data:
            for bot in self.bot_data:
                if self.tg_data['pair'] in bot['name']:
                    new_bot = False
                    break

            if new_bot:
                if (self.tg_data['action'] == "START" and
                    self.deal_data < self.config['dcabot'].getint('mad')):
                    self.logging.info("No single dcabot for " + self.tg_data['pair'] + " found - creating one")
                    self.create()
                else:
                    self.logging.info("Maximum deals reached or stop command on a non-existing bot!")
            else:
                self.logging.debug("Pair: " + self.tg_data['pair'])
                self.logging.debug("Bot-Name: " + bot['name'])
                if self.tg_data['action'] == "START":
                    if self.deal_data < self.config['dcabot'].getint('mad'):
                        self.enable(bot)
                else:
                    self.delete(bot)
        
        else:
            self.logging.info("No dcabots found")
            self.create()
