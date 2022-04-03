import re
import json
import time

from signals import Signals

deal_lock = False


class SingleBot:
    def __init__(self, tg_data, bot_data, account_data, config, p3cw, logging):
        self.tg_data = tg_data
        self.bot_data = bot_data
        self.account_data = account_data
        self.config = config
        self.p3cw = p3cw
        self.logging = logging
        self.signal = Signals(logging)
        self.prefix = self.config["dcabot"]["prefix"]
        self.subprefix = self.config["dcabot"]["subprefix"]
        self.suffix = self.config["dcabot"]["suffix"]

    def strategy(self):
        if self.config["filter"]["deal_mode"] == "signal":
            strategy = [{"strategy": "nonstop"}]
        else:
            strategy = json.loads(self.config["filter"]["deal_mode"])

        return strategy

    def deal_count(self):
        account = self.account_data
        deals = []

        error, data = self.p3cw.request(
            entity="deals",
            action="",
            action_id=account["id"],
            additional_headers={"Forced-Mode": self.config["trading"]["trade_mode"]},
            payload={"limit": 1000, "scope": "active"},
        )

        if error:
            self.logging.error(error["msg"])
            self.logging.error(
                "Setting deal count temporary to maximum - because of API errors!"
            )
            return self.config["dcabot"].getint("single_count")
        else:
            for deal in data:
                if (
                    self.prefix
                    + "_"
                    + self.subprefix
                    + "_"
                    + self.config["trading"]["market"]
                ) in deal["bot_name"]:
                    deals.append(deal["bot_name"])

        self.logging.debug(str(deals))
        self.logging.info("Deal count: " + str(len(deals)))

        return len(deals)

    def bot_count(self):

        bots = []

        for bot in self.bot_data:
            if (
                self.prefix
                + "_"
                + self.subprefix
                + "_"
                + self.config["trading"]["market"]
            ) in bot["name"] and bot["is_enabled"]:
                bots.append(bot["name"])

        self.logging.info("Enabled single bot count: " + str(len(bots)))

        return len(bots)

    def payload(self, pair):
        payload = {
            "name": self.prefix + "_" + self.subprefix + "_" + pair + "_" + self.suffix,
            "account_id": self.account_data["id"],
            "pairs": self.tg_data["pair"],
            "max_active_deals": self.config["dcabot"].getint("mad"),
            "base_order_volume": self.config["dcabot"].getfloat("bo"),
            "take_profit": self.config["dcabot"].getfloat("tp"),
            "safety_order_volume": self.config["dcabot"].getfloat("so"),
            "martingale_volume_coefficient": self.config["dcabot"].getfloat("os"),
            "martingale_step_coefficient": self.config["dcabot"].getfloat("ss"),
            "max_safety_orders": self.config["dcabot"].getint("mstc"),
            "safety_order_step_percentage": self.config["dcabot"].getfloat("sos"),
            "take_profit_type": "total",
            "active_safety_orders_count": self.config["dcabot"].getint("max"),
            "strategy_list": self.strategy(),
            "trailing_enabled": self.config["trading"].getboolean("trailing"),
            "trailing_deviation": self.config["trading"].getfloat("trailing_deviation"),
            "min_volume_btc_24h": self.config["dcabot"].getfloat("btc_min_vol"),
        }

        return payload

    def update(self, bot):

        # Update settings on an existing bot
        error, data = self.p3cw.request(
            entity="bots",
            action="update",
            action_id=str(bot["id"]),
            additional_headers={"Forced-Mode": self.config["trading"]["trade_mode"]},
            payload=self.payload(bot["pairs"][0]),
        )

        if error:
            self.logging.error(error["msg"])
        else:
            self.logging.info("Updating bot settings on " + bot["name"])

    def enable(self, bot):

        if self.config["trading"].getboolean("singlebot_update"):
            self.update(bot)

        # Enables an existing bot
        error, data = self.p3cw.request(
            entity="bots",
            action="enable",
            action_id=str(bot["id"]),
            additional_headers={"Forced-Mode": self.config["trading"]["trade_mode"]},
        )

        if error:
            self.logging.error(error["msg"])
        else:
            self.logging.info(
                "Enabling single bot " + bot["name"] + " because of a START signal"
            )

    def disable(self, bot, allbots=False):
        # Disable all bots
        error = {}

        if allbots:

            self.logging.info("Disabling all single bots, because of BTC Pulse")

            for bots in bot:
                if (
                    self.prefix
                    + "_"
                    + self.subprefix
                    + "_"
                    + self.config["trading"]["market"]
                ) in bots["name"]:
                    error, data = self.p3cw.request(
                        entity="bots",
                        action="disable",
                        action_id=str(bots["id"]),
                        additional_headers={
                            "Forced-Mode": self.config["trading"]["trade_mode"]
                        },
                    )

                    if error:
                        self.logging.error(error["msg"])
                    else:
                        self.logging.info(
                            "Disabling single bot "
                            + bots["name"]
                            + " because of a STOP signal"
                        )
        else:
            # Disables an existing bot
            error, data = self.p3cw.request(
                entity="bots",
                action="disable",
                action_id=str(bot["id"]),
                additional_headers={
                    "Forced-Mode": self.config["trading"]["trade_mode"]
                },
            )

            if error:
                self.logging.error(error["msg"])
            else:
                self.logging.info(
                    "Disabling single bot " + bot["name"] + " because of a STOP signal"
                )

    def create(self):
        # Creates a single bot with start signal
        self.logging.info("Create single bot with pair " + self.tg_data["pair"])

        error, data = self.p3cw.request(
            entity="bots",
            action="create_bot",
            additional_headers={"Forced-Mode": self.config["trading"]["trade_mode"]},
            payload=self.payload(self.tg_data["pair"]),
        )

        if error:
            self.logging.error(error["msg"])
        else:
            # Fix - 3commas needs some time for bot creation
            time.sleep(2)
            self.enable(data)

    def delete(self, bot):
        if bot["active_deals_count"] == 0 and self.config["trading"].getboolean(
            "delete_single_bots"
        ):
            # Deletes a single bot with stop signal
            self.logging.info("Delete single bot with pair " + self.tg_data["pair"])
            error, data = self.p3cw.request(
                entity="bots",
                action="delete",
                action_id=str(bot["id"]),
                additional_headers={
                    "Forced-Mode": self.config["trading"]["trade_mode"]
                },
            )

            if error:
                self.logging.error(error["msg"])
        else:
            self.logging.info(
                "Cannot delete single bot, because of active deals or configuration. Disabling it!"
            )
            self.disable(bot, False)

    def trigger(self):
        # Triggers a single bot deal

        self.logging.info("Got new 3cqs signal")

        global deal_lock
        new_bot = True
        pair = self.tg_data["pair"]
        running_deals = self.deal_count()

        if self.bot_data:
            for bot in self.bot_data:
                if (
                    self.prefix + "_" + self.subprefix + "_" + pair + "_" + self.suffix
                ) in bot["name"]:
                    new_bot = False
                    break

            if new_bot:
                if self.tg_data["action"] == "START":
                    if self.bot_count() < self.config["dcabot"].getint("single_count"):

                        pair = self.signal.topcoin(
                            pair,
                            self.config["filter"].getint("topcoin_limit"),
                            self.config["filter"].getint("topcoin_volume"),
                            self.config["filter"]["topcoin_exchange"],
                        )

                        if pair:
                            self.logging.info(
                                "No single bot for " + pair + " found - creating one"
                            )
                            # avoid deals over limit
                            if (
                                running_deals
                                < self.config["dcabot"].getint("single_count") - 1
                            ):
                                self.create()
                                deal_lock = False
                            elif (
                                running_deals
                                == self.config["dcabot"].getint("single_count") - 1
                            ) and not deal_lock:
                                self.create()
                                deal_lock = True
                            else:
                                self.logging.info(
                                    "Blocking new deals, because last enabled bot can potentialy reach max deals!"
                                )

                        else:
                            self.logging.info(
                                "Pair "
                                + pair
                                + " is not in the top coin list - not added!"
                            )

                elif self.tg_data["action"] == "STOP":
                    self.logging.info(
                        "Stop command on a non-existing single bot with pair: " + pair
                    )
                else:
                    self.logging.info(
                        "Maximum bots/deals reached. Bot with pair: "
                        + pair
                        + " not added."
                    )
            else:
                self.logging.debug("Pair: " + pair)
                self.logging.debug("Bot-Name: " + bot["name"])

                if self.tg_data["action"] == "START":
                    if self.bot_count() < self.config["dcabot"].getint("single_count"):
                        # avoid deals over limit
                        if (
                            self.deal_count()
                            < self.config["dcabot"].getint("single_count") - 1
                        ):
                            self.enable(bot)
                            deal_lock = False
                        elif (
                            self.deal_count()
                            == self.config["dcabot"].getint("single_count") - 1
                        ) and not deal_lock:
                            self.enable(bot)
                            deal_lock = True
                        else:
                            self.logging.info(
                                "Blocking new deals, because last enabled bot can potentialy reach max deals!"
                            )

                    else:
                        self.logging.info(
                            "Maximum enabled bots/deals reached. Single bot with pair: "
                            + pair
                            + " not enabled."
                        )
                else:
                    self.delete(bot)

        else:
            self.logging.info("No single bots found")
            self.create()
