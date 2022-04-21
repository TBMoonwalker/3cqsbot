import re
import json
import time

from signals import Signals

deal_lock = False


class SingleBot:
    def __init__(self, tg_data, bot_data, account_data, attributes, p3cw, logging):
        self.tg_data = tg_data
        self.bot_data = bot_data
        self.account_data = account_data
        self.attributes = attributes
        self.p3cw = p3cw
        self.logging = logging
        self.signal = Signals(logging)
        self.prefix = self.attributes.get("prefix")
        self.subprefix = self.attributes.get("subprefix")
        self.suffix = self.attributes.get("suffix")
        self.bot_name = (
            self.prefix
            + "_"
            + self.subprefix
            + "_"
            + self.attributes.get("market")
            + "(.*)"
            + "_"
            + self.suffix
        )

    def strategy(self):
        if self.attributes.get("deal_mode", "signal") == "signal":
            strategy = [{"strategy": "nonstop"}]
        else:
            try:
                strategy = json.loads(self.attributes.get("deal_mode"))
            except ValueError:
                self.logging.error(
                    "Decoding JSON string of deal_mode failed. Please check https://jsonformatter.curiousconcept.com/ for correct format"
                )

        return strategy

    def deal_count(self):
        account = self.account_data
        deals = []

        error, data = self.p3cw.request(
            entity="deals",
            action="",
            action_id=account["id"],
            additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
            payload={"limit": 1000, "scope": "active", "account_id": account["id"]},
        )

        if error:
            self.logging.error(
                "Setting deal count temporary to maximum - because of API errors!"
            )
            self.logging.error(error["msg"])
            return self.attributes.get("single_count")
        else:
            for deal in data:
                if re.search(self.bot_name, deal["bot_name"]):
                    deals.append(deal["bot_name"])

        self.logging.debug(str(deals))
        self.logging.info("Deal count: " + str(len(deals)))

        return len(deals)

    def bot_count(self):

        bots = []

        for bot in self.bot_data:
            if re.search(self.bot_name, bot["name"]) and bot["is_enabled"]:
                bots.append(bot["name"])

        self.logging.info("Enabled single bot count: " + str(len(bots)))

        return len(bots)

    def payload(self, pair, new_bot):
        payload = {
            "name": self.prefix + "_" + self.subprefix + "_" + pair + "_" + self.suffix,
            "account_id": self.account_data["id"],
            "pairs": self.tg_data["pair"],
            "max_active_deals": self.attributes.get("mad"),
            "base_order_volume": self.attributes.get("bo"),
            "take_profit": self.attributes.get("tp"),
            "safety_order_volume": self.attributes.get("so"),
            "martingale_volume_coefficient": self.attributes.get("os"),
            "martingale_step_coefficient": self.attributes.get("ss"),
            "max_safety_orders": self.attributes.get("mstc"),
            "safety_order_step_percentage": self.attributes.get("sos"),
            "take_profit_type": "total",
            "active_safety_orders_count": self.attributes.get("max"),
            "cooldown": self.attributes.get("cooldown", 0),
            "strategy_list": self.strategy(),
            "trailing_enabled": self.attributes.get("trailing", False),
            "trailing_deviation": self.attributes.get("trailing_deviation", 0.2),
            "min_volume_btc_24h": self.attributes.get("btc_min_vol"),
            "disable_after_deals_count": self.attributes.get("deals_count", 0),
        }
        
        if new_bot:
            if payload["disable_after_deals_count"] == 0:
                self.logging.info("This is a new bot and deal_count set to 0, removing from payload")
                payload.pop("disable_after_deals_count")

        if self.attributes.get("trade_future", False):
            payload.update(
                {
                    "leverage_type": self.attributes.get("leverage_type"),
                    "leverage_custom_value": self.attributes.get("leverage_value"),
                    "stop_loss_percentage": self.attributes.get("stop_loss_percent"),
                    "stop_loss_type": self.attributes.get("stop_loss_type"),
                    "stop_loss_timeout_enabled": self.attributes.get(
                        "stop_loss_timeout_enabled"
                    ),
                    "stop_loss_timeout_in_seconds": self.attributes.get(
                        "stop_loss_timeout_seconds"
                    ),
                }
            )

        return payload

    def update(self, bot):
        # Update settings on an existing bot
        self.logging.info("Updating bot settings on " + bot["name"])

        error, data = self.p3cw.request(
            entity="bots",
            action="update",
            action_id=str(bot["id"]),
            additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
            payload=self.payload(bot["pairs"][0], new_bot=False),
        )

        if error:
            self.logging.error(error["msg"])

    def enable(self, bot):

        self.logging.info(
            "Enabling single bot " + bot["name"] + " because of a START signal"
        )

        if self.attributes.get("singlebot_update", "true"):
            self.update(bot)

        # Enables an existing bot
        error, data = self.p3cw.request(
            entity="bots",
            action="enable",
            action_id=str(bot["id"]),
            additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
        )

        if error:
            self.logging.error(error["msg"])

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
                    + self.attributes.get("market")
                ) in bots["name"]:

                    self.logging.info(
                        "Disabling single bot "
                        + bots["name"]
                        + " because of a STOP signal"
                    )

                    error, data = self.p3cw.request(
                        entity="bots",
                        action="disable",
                        action_id=str(bots["id"]),
                        additional_headers={
                            "Forced-Mode": self.attributes.get("trade_mode")
                        },
                    )

                    if error:
                        self.logging.error(error["msg"])
        else:
            # Disables an existing bot
            self.logging.info(
                "Disabling single bot " + bot["name"] + " because of a STOP signal"
            )

            error, data = self.p3cw.request(
                entity="bots",
                action="disable",
                action_id=str(bot["id"]),
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
            )

            if error:
                self.logging.error(error["msg"])

    def create(self):
        # Creates a single bot with start signal
        self.logging.info("Create single bot with pair " + self.tg_data["pair"])

        error, data = self.p3cw.request(
            entity="bots",
            action="create_bot",
            additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
            payload=self.payload(self.tg_data["pair"], new_bot=True),
        )

        if error:
            self.logging.error(error["msg"])
        else:
            # Fix - 3commas needs some time for bot creation
            time.sleep(2)
            self.enable(data)

    def delete(self, bot):
        if bot["active_deals_count"] == 0 and self.attributes.get(
            "delete_single_bots", False
        ):
            # Deletes a single bot with stop signal
            self.logging.info("Delete single bot with pair " + self.tg_data["pair"])
            error, data = self.p3cw.request(
                entity="bots",
                action="delete",
                action_id=str(bot["id"]),
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
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
                ) == bot["name"]:
                    new_bot = False
                    break

            if new_bot:
                if self.tg_data["action"] == "START":
                    if self.bot_count() < self.attributes.get("single_count"):

                        if self.attributes.get("topcoin_filter", False):
                            pair = self.signal.topcoin(
                                pair,
                                self.attributes.get("topcoin_limit", 0),
                                self.attributes.get("topcoin_volume", 0),
                                self.attributes.get("topcoin_exchange", "binance"),
                                self.attributes.get("market"),
                            )
                        else:
                            self.logging.info(
                                "Topcoin filter disabled, not filtering pairs!"
                            )

                        if pair:
                            self.logging.info(
                                "No single bot for " + pair + " found - creating one"
                            )
                            # avoid deals over limit
                            if running_deals < self.attributes.get("single_count") - 1:
                                self.create()
                                deal_lock = False
                            elif (
                                running_deals == self.attributes.get("single_count") - 1
                            ) and not deal_lock:
                                self.create()
                                deal_lock = True
                            else:
                                self.logging.info(
                                    "Blocking new deals, because last enabled bot can potentially reach max deals!"
                                )

                        else:
                            self.logging.info(
                                "Pair "
                                + str(self.tg_data["pair"])
                                + " is not in the top coin list - not added!"
                            )
                    else:
                        self.logging.info(
                            "Maximum bots/deals reached. Bot with pair: "
                            + pair
                            + " not added."
                        )

                elif self.tg_data["action"] == "STOP":
                    self.logging.info(
                        "Stop command on a non-existing single bot with pair: " + pair
                    )
            else:
                self.logging.debug("Pair: " + pair)
                self.logging.debug("Bot-Name: " + bot["name"])

                if self.tg_data["action"] == "START":
                    if self.bot_count() < self.attributes.get("single_count"):
                        # avoid deals over limit
                        if self.deal_count() < self.attributes.get("single_count") - 1:
                            self.enable(bot)
                            deal_lock = False
                        elif (
                            self.deal_count() == self.attributes.get("single_count") - 1
                        ) and not deal_lock:
                            self.enable(bot)
                            deal_lock = True
                        else:
                            self.logging.info(
                                "Blocking new deals, because last enabled bot can potentially reach max deals!"
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
