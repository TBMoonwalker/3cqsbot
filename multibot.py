import random
import json
from sys import prefix

from signals import Signals


class MultiBot:
    def __init__(
        self, tg_data, bot_data, account_data, pair_data, config, p3cw, logging
    ):
        self.tg_data = tg_data
        self.bot_data = bot_data
        self.account_data = account_data
        self.pair_data = pair_data
        self.config = config
        self.p3cw = p3cw
        self.logging = logging
        self.signal = Signals(logging)
        self.prefix = self.config["dcabot"]["prefix"]
        self.subprefix = self.config["dcabot"]["subprefix"]
        self.suffix = self.config["dcabot"]["suffix"]

    def strategy(self):
        if self.config["filter"]["deal_mode"] == "signal":
            strategy = [{"strategy": "manual"}]
        else:
            strategy = json.loads(self.config["filter"]["deal_mode"])

        return strategy

    def adjustmad(self, pairs, mad):
        # Lower max active deals, when pairs are under mad
        if len(pairs) * self.config["dcabot"].getint("sdsp") < mad:
            self.logging.debug(
                "Pairs are under 'mad' - Lower max active deals to actual pairs"
            )
            mad = len(pairs)
        # Raise max active deals to minimum pairs or mad if possible
        elif len(pairs) * self.config["dcabot"].getint("sdsp") >= mad:
            self.logging.debug("Pairs are over 'mad' - nothing to do")
            mad = self.config["dcabot"].getint("mad")

        return mad

    def payload(self, pairs, mad):
        payload = {
            "name": self.prefix + "_" + self.subprefix + "_" + self.suffix,
            "account_id": self.account_data["id"],
            "pairs": pairs,
            "max_active_deals": mad,
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
            "allowed_deals_on_same_pair": self.config["dcabot"].getint("sdsp"),
            "min_volume_btc_24h": self.config["dcabot"].getfloat("btc_min_vol"),
        }

        return payload

    def enable(self, bot):
        # Enables an existing bot
        if not bot["is_enabled"]:
            error, data = self.p3cw.request(
                entity="bots",
                action="enable",
                action_id=str(bot["id"]),
                additional_headers={
                    "Forced-Mode": self.config["trading"]["trade_mode"]
                },
            )

            if error:
                self.logging.error(error["msg"])
                self.logging.debug("Error enabling bot: " + bot["name"])
            else:
                self.logging.info("Enabling bot: " + bot["name"])
        else:
            self.logging.info(bot["name"] + " enabled")

    def disable(self):
        # Disables an existing bot
        for bot in self.bot_data:
            if (self.prefix + "_" + self.subprefix + "_" + self.suffix) in bot["name"]:

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
                    self.logging.error("Error disabling bot: " + error["msg"])
                else:
                    self.logging.info("Disabling bot: " + bot["name"])

    def new_deal(self, bot, triggerpair):
        # Triggers a new deal
        if triggerpair:
            pair = triggerpair
        else:
            if self.config["filter"].getboolean("random_pair"):
                pair = random.choice(bot["pairs"])
            else:
                pair = ""

        if pair:
            self.logging.info("Trigger new deal with pair " + pair)
            error, data = self.p3cw.request(
                entity="bots",
                action="start_new_deal",
                action_id=str(bot["id"]),
                additional_headers={
                    "Forced-Mode": self.config["trading"]["trade_mode"]
                },
                payload={"pair": pair},
            )

            if error:
                if bot["active_deals_count"] == bot["max_active_deals"]:
                    self.logging.info("Max deals count reached, not adding a new one.")
                else:
                    self.logging.error(error["msg"])
        else:
            self.logging.info("Pair was not part of the START signal, ignoring it.")

    def create(self):
        # Creates a multi bot with start signal
        new_bot = True
        pairs = []
        botnames = []
        mad = self.config["dcabot"].getint("mad")

        # Check for existing or new bot
        for bot in self.bot_data:

            botnames.append(bot["name"])

            if (self.prefix + "_" + self.subprefix + "_" + self.suffix) in bot["name"]:
                botid = str(bot["id"])
                new_bot = False
                break

        self.logging.debug("Existing bot names: " + str(botnames))

        # Create pair list
        # Filter topcoins (if set)
        pairlist = self.signal.topcoin(
            self.tg_data,
            self.config["filter"].getint("topcoin_limit"),
            self.config["filter"].getint("topcoin_volume"),
            self.config["filter"]["topcoin_exchange"],
        )
        for pair in pairlist:
            pair = self.config["trading"]["market"] + "_" + pair
            # Traded on our exchange?
            if pair in self.pair_data:
                self.logging.debug("Pair " + pair + " added to the list.")
                pairs.append(pair)

        self.logging.debug("Pairs after topcoin filter " + str(pairs))

        # Run filters to adapt pair list
        if self.config["filter"].getboolean("limit_initial_pairs"):
            # Limit pairs to the maximal deals (mad)
            if self.config["dcabot"].getint("mad") == 1:
                maxpairs = 2
            elif self.config["dcabot"].getint("mad") <= len(pairs):
                maxpairs = self.config["dcabot"].getint("mad")
            else:
                maxpairs = len(pairs)
            pairs = pairs[0:maxpairs]

            self.logging.debug("Pairs after limit initial pairs filter " + str(pairs))

        # Adapt mad if pairs are under value
        mad = self.adjustmad(pairs, mad)

        if new_bot:

            self.logging.info("Creating multi bot with pairs " + str(pairs))
            error, data = self.p3cw.request(
                entity="bots",
                action="create_bot",
                additional_headers={
                    "Forced-Mode": self.config["trading"]["trade_mode"]
                },
                payload=self.payload(pairs, mad),
            )

            if error:
                self.logging.error(error["msg"])
            else:
                if not self.config["filter"].getboolean("ext_botswitch"):
                    self.enable(data)
                else:
                    self.logging.info(
                        "ext_botswitch set to true, bot has to be enabled by external TV signal"
                    )
                self.new_deal(data, triggerpair="")
        else:

            error, data = self.p3cw.request(
                entity="bots",
                action="update",
                action_id=botid,
                additional_headers={
                    "Forced-Mode": self.config["trading"]["trade_mode"]
                },
                payload=self.payload(pairs, mad),
            )

            if error:
                self.logging.error(error["msg"])
            else:
                self.logging.info(bot["name"] + " updated with filtered pairs")
                self.logging.debug("Pairs: " + str(pairs))
                if not self.config["filter"].getboolean("ext_botswitch"):
                    self.enable(data)
                else:
                    self.logging.info(
                        "ext_botswitch set to true, bot enabling/disabling has to be managed by external TV signal"
                    )

    def trigger(self, triggeronly=False):
        # Updates multi bot with new pairs
        triggerpair = ""
        mad = self.config["dcabot"].getint("mad")

        for bot in self.bot_data:
            if (self.prefix + "_" + self.subprefix + "_" + self.suffix) in bot["name"]:

                if not triggeronly:
                    pair = self.tg_data["pair"]

                    self.logging.info(
                        "Got new 3cqs "
                        + self.tg_data["action"]
                        + " signal for pair "
                        + pair
                    )

                    if self.tg_data["action"] == "START":
                        triggerpair = pair

                        if pair in bot["pairs"]:
                            self.logging.info(
                                "Pair " + pair + " is already included in the pair list"
                            )
                        else:
                            pair = self.signal.topcoin(
                                pair,
                                self.config["filter"].getint("topcoin_limit"),
                                self.config["filter"].getint("topcoin_volume"),
                                self.config["filter"]["topcoin_exchange"],
                            )
                            if pair:
                                self.logging.info("Adding pair " + pair)
                                bot["pairs"].append(pair)
                            else:
                                self.logging.info(
                                    "Pair "
                                    + pair
                                    + " is not in filtered Coingecko's top coin list!"
                                )

                    else:
                        if pair in bot["pairs"]:
                            self.logging.info("Remove pair " + pair)
                            bot["pairs"].remove(pair)
                        else:
                            self.logging.info(
                                "Pair "
                                + pair
                                + " was not included in the pair list, not removed"
                            )

                    # Adapt mad if pairs are under value
                    mad = self.adjustmad(bot["pairs"], mad)

                    error, data = self.p3cw.request(
                        entity="bots",
                        action="update",
                        action_id=str(bot["id"]),
                        additional_headers={
                            "Forced-Mode": self.config["trading"]["trade_mode"]
                        },
                        payload=self.payload(bot["pairs"], mad),
                    )

                    if error:
                        self.logging.error(error["msg"])
                else:
                    data = bot

                if self.config["filter"]["deal_mode"] == "signal" and data:
                    self.new_deal(data, triggerpair)
