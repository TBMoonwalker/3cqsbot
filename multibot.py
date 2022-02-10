class MultiBot:
    def __init__(self, tg_data, bot_data, account_data, deal_data, config, p3cw):
        self.tg_data = tg_data
        self.bot_data = bot_data
        self.account_data = account_data
        self.deal_data = deal_data
        self.config = config
        self.p3cw = p3cw

    def trigger(self):
        # Triggers a multi bot deal
        print("Start trigger")
        # ToDo
        # Check if multibot exists (has to be, because trigger is called afterwards)
        # Check for STOP/START SIGNAL (Update Pairs)
        # Create new deal after bot update