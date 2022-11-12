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

        for bots in self.bot_data:
            if (self.prefix + "_" + self.subprefix + "_" + self.suffix) == bots["name"]:
                bot.update({"id": str(bots["id"])})
                bot.update({"name": bots["name"]})
                bot.update({"enabled": bots["is_enabled"]})
                bot.update({"pairs": bots["pairs"]})
                bot.update({"active_deals_count": bots["active_deals_count"]})
                bot.update({"max_active_deals": bots["max_active_deals"]})

        return bot

    def __adjustmad(self, pairs, mad):
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

    def __payload(self, pairs, mad, new_bot):

        payload = {
            "name": self.prefix + "_" + self.subprefix + "_" + self.suffix,
            "account_id": self.account_data["id"],
            "pairs": pairs,
            "base_order_volume": self.attributes.get("bo"),
            "take_profit": self.attributes.get("tp"),
            "safety_order_volume": self.attributes.get("so"),
            "martingale_volume_coefficient": self.attributes.get("os"),
            "martingale_step_coefficient": self.attributes.get("ss"),
            "max_safety_orders": self.attributes.get("mstc"),
            "safety_order_step_percentage": self.attributes.get("sos"),
            "take_profit_type": "total",
            "active_safety_orders_count": self.attributes.get("max"),
            "strategy_list": self.strategy(),
            "trailing_enabled": self.attributes.get("trailing", False),
            "allowed_deals_on_same_pair": self.attributes.get("sdsp"),
        }

        if not new_bot:
            payload.update(
                {"disable_after_deals_count": self.attributes.get("deals_count", 0)}
            )

        # Handle non mandatory attributes
        if self.attributes.get("mad", 1) > 1:
            payload.update(
                {
                    "max_active_deals": self.attributes.get("mad"),
                }
            )

        if self.attributes.get("btc_min_vol", 0) > 0:
            payload.update(
                {
                    "min_volume_btc_24h": self.attributes.get("btc_min_vol", 0),
                }
            )

        if self.attributes.get("cooldown", 0) > 0:
            payload.update(
                {
                    "cooldown": self.attributes.get("cooldown", 0),
                }
            )

        if self.attributes.get("trailing_deviation", 0.0) > 0:
            payload.update(
                {
                    "trailing_deviation": self.attributes.get(
                        "trailing_deviation", 0.2
                    ),
                }
            )

        if self.attributes.get("deals_count", 0) > 0:
            payload.update(
                {
                    "disable_after_deals_count": self.attributes.get("deals_count", 0),
                }
            )

        return payload

    def enable(self):
        bot = self.bot()

        # Enables an existing bot
        self.logging.debug(str(bot))
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

    def __new_deal(self, bot, pair):
        # Triggers a new deal
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
        mad = self.__adjustmad(pairs, mad)

        if not bot:
            self.logging.info(
                "Creating multi bot "
                + self.prefix
                + "_"
                + self.subprefix
                + "_"
                + self.suffix
                + " with initial pairs"
            )
            error, data = self.p3cw.request(
                entity="bots",
                action="create_bot",
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
                payload=self.__payload(pairs, mad, new_bot=True),
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

            pair = self.attributes.get("market") + "_" + self.ws_data["symbol"]
            pair_update = True

            self.logging.info(
                "Got new 3cqs " + self.ws_data["signal"] + " signal for " + pair
            )

            if self.ws_data["signal"] == "BOT_START":
                triggerpair = pair

                if pair in bot["pairs"]:
                    self.logging.info(pair + " is already included in the pair list")
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
                    pair_update = False

            if pair_update:
                # Adapt mad if pairs are under value
                mad = self.__adjustmad(bot["pairs"], mad)
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
                    payload=self.__payload(bot["pairs"], mad, new_bot=False),
                )

                if error:
                    self.logging.error(error["msg"])
                else:
                    if self.attributes.get("deal_mode") == "signal":
                        data = bot

                    if not triggeronly:
                        if self.attributes.get("deal_mode") == "signal" and data:
                            self.__new_deal(data, triggerpair)
