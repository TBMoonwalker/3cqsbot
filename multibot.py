import random
import json
from sys import prefix


class MultiBot:
    def __init__(
        self, ws_data, bot_data, account_data, pair_data, attributes, p3cw, logging
    ):
        self.ws_data = ws_data
        self.bot_data = bot_data
        self.account_data = account_data
        self.pair_data = pair_data
        self.attributes = attributes
        self.p3cw = p3cw
        self.logging = logging
        self.prefix = self.attributes.get("prefix")
        self.subprefix = self.attributes.get("subprefix")
        self.suffix = self.attributes.get("suffix")

    def strategy(self):
        if self.attributes.get("deal_mode", "signal") == "signal":
            strategy = [{"strategy": "manual"}]
        else:
            try:
                strategy = json.loads(self.attributes.get("deal_mode"))
            except ValueError:
                self.logging.error(
                    "Decoding JSON string of deal_mode failed. Please check https://jsonformatter.curiousconcept.com/ for correct format"
                )

        return strategy

    def bot(self):

        bot = {}

        for bot in self.bot_data:
            if (self.prefix + "_" + self.subprefix + "_" + self.suffix) == bot["name"]:
                bot.update({"id": str(bot["id"])})
                bot.update({"name": bot["name"]})
                bot.update({"enabled": bot["is_enabled"]})
                bot.update({"pairs": bot["pairs"]})

        return bot

    def adjustmad(self, pairs, mad):
        # Lower max active deals, when pairs are under mad
        if len(pairs) * self.attributes.get("sdsp") < mad:
            self.logging.debug(
                "Pairs are under 'mad' - Lower max active deals to actual pairs"
            )
            mad = len(pairs)
        # Raise max active deals to minimum pairs or mad if possible
        elif len(pairs) * self.attributes.get("sdsp") >= mad:
            self.logging.debug("Pairs are over 'mad' - nothing to do")
            mad = self.attributes.get("mad")

        return mad

    def payload(self, pairs, mad, new_bot):

        payload = {
            "name": self.prefix + "_" + self.subprefix + "_" + self.suffix,
            "account_id": self.account_data["id"],
            "pairs": pairs,
            "max_active_deals": mad,
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
            "allowed_deals_on_same_pair": self.attributes.get("sdsp"),
            "min_volume_btc_24h": self.attributes.get("btc_min_vol", 0),
            "disable_after_deals_count": self.attributes.get("deals_count", 0),
        }

        if new_bot:
            if payload["disable_after_deals_count"] == 0:
                self.logging.info(
                    "This is a new bot and deal_count set to 0, removing from payload"
                )
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

    def enable(self):
        bot = self.bot()

        # Enables an existing bot
        if not bot["enabled"]:
            self.logging.info("Enabling bot: " + bot["name"])

            error, data = self.p3cw.request(
                entity="bots",
                action="enable",
                action_id=str(bot["id"]),
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
            )

            if error:
                self.logging.error(error["msg"])

        else:
            self.logging.info(bot["name"] + " enabled")

    def disable(self):
        # Disables an existing bot
        for bot in self.bot_data:
            if (self.prefix + "_" + self.subprefix + "_" + self.suffix) == bot["name"]:

                # Disables an existing bot
                self.logging.info("Disabling bot: " + bot["name"])

                error, data = self.p3cw.request(
                    entity="bots",
                    action="disable",
                    action_id=str(bot["id"]),
                    additional_headers={
                        "Forced-Mode": self.attributes.get("trade_mode")
                    },
                )

                if error:
                    self.logging.error(error["msg"])

    def new_deal(self, bot, triggerpair):
        # Triggers a new deal
        if triggerpair:
            pair = triggerpair
        else:
            if self.attributes.get("random_pair", "true"):
                pair = random.choice(bot["pairs"])
            else:
                pair = ""

        if pair:
            self.logging.info("Trigger new deal with pair " + pair)
            error, data = self.p3cw.request(
                entity="bots",
                action="start_new_deal",
                action_id=str(bot["id"]),
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
                payload={"pair": pair},
            )

            if error:
                if bot["active_deals_count"] == bot["max_active_deals"]:
                    self.logging.info(
                        "Max active deals of "
                        + str(bot["max_active_deals"])
                        + " reached, not adding a new one."
                    )
                else:
                    self.logging.error(error["msg"])

    def create(self):
        # Creates a multi bot with start signal
        pairs = []
        mad = self.attributes.get("mad")
        bot = self.bot()
        status = False

        # Initial pairlist
        for pair in self.pair_data:
            pair = self.attributes.get("market") + "_" + self.ws_data["symbol"]
            pairs.append(pair)

        # Adapt mad if pairs are under value
        mad = self.adjustmad(pairs, mad)

        if not bot:
            self.logging.info(
                "Creating multi bot "
                + self.prefix
                + "_"
                + self.subprefix
                + "_"
                + self.suffix
                + " with filtered symrank pairs"
            )
            error, data = self.p3cw.request(
                entity="bots",
                action="create_bot",
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
                payload=self.payload(pairs, mad, bot),
            )

            if error:
                self.logging.error(error["msg"])
            else:
                status = True

        return status

    def trigger(self, triggeronly=False):
        # Updates multi bot with new pairs
        triggerpair = ""
        mad = self.attributes.get("mad")
        bot = self.bot()

        # Existing Bot
        if bot:

            if not triggeronly:
                pair = self.attributes.get("market") + "_" + self.ws_data["symbol"]

                self.logging.info(
                    "Got new 3cqs " + self.ws_data["signal"] + " signal for " + pair
                )

                if self.ws_data["signal"] == "BOT_START":
                    triggerpair = pair

                    if pair in bot["pairs"]:
                        self.logging.info(
                            pair + " is already included in the pair list"
                        )
                    else:
                        if pair:
                            self.logging.info("Adding pair " + pair)
                            bot["pairs"].append(pair)
                else:
                    if pair in bot["pairs"]:
                        self.logging.info("Remove pair " + pair)
                        bot["pairs"].remove(pair)
                    else:
                        self.logging.info(
                            pair + " was not included in the pair list, not removed"
                        )

                # Adapt mad if pairs are under value
                mad = self.adjustmad(bot["pairs"], mad)
                self.logging.info(
                    "Adjusting mad to amount of included symrank pairs: " + str(mad)
                )

                error, data = self.p3cw.request(
                    entity="bots",
                    action="update",
                    action_id=str(bot["id"]),
                    additional_headers={
                        "Forced-Mode": self.attributes.get("trade_mode")
                    },
                    payload=self.payload(bot["pairs"], mad, new_bot=False),
                )

                if error:
                    self.logging.error(error["msg"])
            else:
                data = bot

            if self.attributes.get("deal_mode") == "signal" and data:
                self.new_deal(data, triggerpair)
