class SingleBot:
    def __init__(self, tg_data, bot_data, account_data, deal_data, config, p3cw):
        self.tg_data = tg_data
        self.bot_data = bot_data
        self.account_data = account_data
        self.deal_data = deal_data
        self.config = config
        self.p3cw = p3cw

    def enable(self, bot):
        # Enables an existing bot
        print ("Enabling bot")
        error, data = self.p3cw.request(
            entity="bots",
            action="enable",
            action_id=str(bot['id']),
            additional_headers={'Forced-Mode': self.config['trading']['trade_mode']},
        )


    def disable(self, bot):
        # Disables an existing bot
        print ("Disabling bot")
        error, data = self.p3cw.request(
            entity="bots",
            action="disable",
            action_id=str(bot['id']),
            additional_headers={'Forced-Mode': self.config['trading']['trade_mode']},
        )

    def create(self):
        # Creates a single bot with start signal
        print ("Create single bot with pair " + self.tg_data['pair'])
        bot = self.config['dcabot']['suffix'] + "_" + self.tg_data['pair']
        error, data = self.p3cw.request(
            entity="bots",
            action="create_bot",
            additional_headers={'Forced-Mode': self.config['trading']['trade_mode']},
            payload={
                "name": self.config['dcabot']['suffix'] + "_" + self.tg_data['pair'],
                "account_id": self.account_data,
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
                "strategy_list": [{"strategy":"nonstop"}]
            }
        )

        if not error:
            self.enable(bot)


    def delete(self, bot):
        if bot['active_deals_count'] == 0:
            # Deletes a single bot with stop signal
            print ("Delete single bot with pair " + self.tg_data['pair'])
            error, data = self.p3cw.request(
                entity="bots",
                action="delete",
                action_id=str(bot['id']),
                additional_headers={'Forced-Mode': self.config['trading']['trade_mode']},
            )
        else:
            print("Cannot delete single bot, because of active deals. Disabling it!")
            self.disable(bot)


    def trigger(self):
        # Triggers a single bot deal
        print("Start trigger")
        new_bot = True

        if self.bot_data:
            for bot in self.bot_data:
                if self.tg_data['pair'] in bot['name']:
                    new_bot = False
                    break

            if new_bot:
                if (self.tg_data['action'] == "START" and
                    self.deal_data < self.config['dcabot'].getint('mad')):
                    print ("No single dcabot for this pair found")
                    self.create()
                else:
                    print("Maximum deals reached or stop command on a non-existing bot!")
            else:
                print ("Pair: " + self.tg_data['pair'])
                print ("Bot-Name: " + bot['name'])
                if self.tg_data['action'] == "START":
                    if self.deal_data < self.config['dcabot'].getint('mad'):
                        self.enable(bot)
                else:
                    self.delete(bot)
        
        else:
            print ("No dcabots found")
            self.create()
