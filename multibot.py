import random
import json
from sys import prefix

from signals import Signals


class MultiBot:
    def __init__(
        self, tg_data, bot_data, account_data, pair_data, attributes, p3cw, logging, dca_conf
    ):
        self.tg_data = tg_data
        self.bot_data = bot_data
        self.account_data = account_data
        self.pair_data = pair_data
        self.attributes = attributes
        self.p3cw = p3cw
        self.logging = logging
        self.signal = Signals(logging)
        self.dca_conf = dca_conf

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

    def payload(self, pairs, mad):

        payload = {
            "name": self.attributes.get("prefix", "3CQSBOT", self.dca_conf) \
                    + "_" + self.attributes.get("subprefix", "MULTI", self.dca_conf) \
                    + "_" + self.attributes.get("suffix", "standard", self.dca_conf),
            "account_id": self.account_data["id"],
            "pairs": pairs,
            "max_active_deals": mad,
            "base_order_volume": self.attributes.get("bo", "", self.dca_conf),
            "take_profit": self.attributes.get("tp", "", self.dca_conf),
            "safety_order_volume": self.attributes.get("so", "", self.dca_conf),
            "martingale_volume_coefficient": self.attributes.get("os", "", self.dca_conf),
            "martingale_step_coefficient": self.attributes.get("ss", "", self.dca_conf),
            "max_safety_orders": self.attributes.get("mstc", "", self.dca_conf),
            "safety_order_step_percentage": self.attributes.get("sos", "", self.dca_conf),
            "take_profit_type": "total",
            "active_safety_orders_count": self.attributes.get("max", "", self.dca_conf),
            "cooldown": self.attributes.get("cooldown", 0, self.dca_conf),
            "strategy_list": self.strategy(),
            "trailing_enabled": self.attributes.get("trailing", False, self.dca_conf),
            "trailing_deviation": self.attributes.get("trailing_deviation", 0.2, self.dca_conf),
            "allowed_deals_on_same_pair": self.attributes.get("sdsp", "", self.dca_conf),
            "min_volume_btc_24h": self.attributes.get("btc_min_vol", 0, self.dca_conf)
        }

        if self.attributes.get("trade_future", False):
            payload.update(
                {
                    "leverage_type": self.attributes.get("leverage_type", "", self.dca_conf),
                    "leverage_custom_value": self.attributes.get("leverage_value", "", self.dca_conf),
                    "stop_loss_percentage": self.attributes.get("stop_loss_percent", "", self.dca_conf),
                    "stop_loss_type": self.attributes.get("stop_loss_type", "", self.dca_conf),
                    "stop_loss_timeout_enabled": self.attributes.get(
                        "stop_loss_timeout_enabled", "", self.dca_conf
                    ),
                    "stop_loss_timeout_in_seconds": self.attributes.get(
                        "stop_loss_timeout_seconds", "", self.dca_conf
                    ),
                }
            )

        return payload

    def enable(self, bot):
        # Enables an existing bot
        if not bot["is_enabled"]:
            self.logging.info("Enabling bot: " + bot["name"] + " (" + str(bot["id"]) + ")")

            error, data = self.p3cw.request(
                entity="bots",
                action="enable",
                action_id=str(bot["id"]),
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
            )

            if error:
                self.logging.error(error["msg"])

        else:
            self.logging.info("'" + bot["name"] + "' (" + str(bot["id"]) + ") enabled")

    def disable(self):
        botid = str(self.attributes.get("botid", ""))
        botname = self.attributes.get("prefix", "3CQSBOT", self.dca_conf) \
        + "_" + self.attributes.get("subprefix", "MULTI", self.dca_conf) \
        + "_" + self.attributes.get("suffix", "standard", self.dca_conf)

        # Disables an existing bot
        for bot in self.bot_data:
            if botid == bot["id"] or botname == bot["name"]:

                # Disables an existing bot
                self.logging.info("Disabling bot: " + bot["name"] + " (" + str(bot["id"]) + ")")

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
                    self.logging.info("Max active deals of " 
                    + str(bot["max_active_deals"]) 
                    + " reached, not adding a new one.")
                else:
                    self.logging.error(error["msg"])


    def create(self):
        # Creates a multi bot with start signal
        new_bot = True
        pairs = []
        mad = self.attributes.get("mad")
        botname = self.attributes.get("prefix", "3CQSBOT", self.dca_conf) \
        + "_" + self.attributes.get("subprefix", "MULTI", self.dca_conf) \
        + "_" + self.attributes.get("suffix", "standard", self.dca_conf)
        botid = str(self.attributes.get("botid", "", self.dca_conf))

        # Check for existing bot id
        if botid != "":
            botnames = []
            self.logging.info("Searching for 3cqsbot with botid " + botid)
            for bot in self.bot_data:
                botnames.append(bot["name"])

                if botid == str(bot["id"]):
                    new_bot = False
                    self.logging.info("Botid " + botid + " with name '" + bot["name"] + "' found")
                    break
            if new_bot:
                self.logging.info("3cqsbot not found with botid: " + botid)

        # Check for existing name
        if new_bot:
            botnames = []
            self.logging.info("Searching for 3cqsbot with name '" + botname + "'")
            for bot in self.bot_data:
                botnames.append(bot["name"])

                if botname == bot["name"]:
                    botid = str(bot["id"])
                    new_bot = False
                    self.logging.info("3cqsbot '" + bot["name"] + "' with botid " + botid + " found")
                    break
            if new_bot:
                self.logging.info("3cqsbot not found with name '" + botname + "' - creating new one")

        self.logging.debug("Checked bot ids/names till config id/name found: " + str(botnames))

        # Create pair list
        # Filter topcoins (if set)
        pairlist = self.signal.topcoin(
            self.tg_data,
            self.attributes.get("topcoin_limit", 3500),
            self.attributes.get("topcoin_volume", 0),
            self.attributes.get("topcoin_exchange", "binance"),
            self.attributes.get("market"),
        )
        for pair in pairlist:
            pair = self.attributes.get("market") + "_" + pair
            # Traded on our exchange?
            if pair in self.pair_data:
                self.logging.debug(pair + " added to the list")
                pairs.append(pair)
            else:
                self.logging.info(
                pair 
                + " removed because pair is blacklisted on 3commas or in config.ini or not tradable on '" 
                + self.attributes.get("account_name")
                + "'"
                )

        self.logging.debug("Pairs after topcoin filter " + str(pairs))

        # Run filters to adapt pair list
        if self.attributes.get("limit_initial_pairs", False):
            # Limit pairs to the maximal deals (mad)
            if self.attributes.get("mad") == 1:
                maxpairs = 2
            elif self.attributes.get("mad") <= len(pairs):
                maxpairs = self.attributes.get("mad")
            else:
                maxpairs = len(pairs)
            pairs = pairs[0:maxpairs]

            self.logging.debug("Pairs after limit initial pairs filter " + str(pairs))

        # Adapt mad if pairs are under value
        mad = self.adjustmad(pairs, mad)

        if new_bot:

            self.logging.info("Creating multi bot '" + botname + "' with filtered symrank pairs")
            error, data = self.p3cw.request(
                entity="bots",
                action="create_bot",
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
                payload=self.payload(pairs, mad),
            )

            if error:
                self.logging.error(error["msg"])
            else:
                if not self.attributes.get("ext_botswitch", False):
                    self.enable(data)
                else:
                    self.logging.info(
                        "ext_botswitch set to true, bot has to be enabled by external TV signal"
                    )
                self.new_deal(data, triggerpair="")
        else:
            if botname != bot["name"]:
                self.logging.info("Changing bot name from '" + bot["name"] + "' (" + botid + ") to '" + botname + "' (" + botid + ")")
                bot["name"] = botname

            self.logging.info("Updating multi bot '" + bot["name"] + "' (" + botid + ") with filtered symrank pairs and DCA setting: " + self.dca_conf)
            error, data = self.p3cw.request(
                entity="bots",
                action="update",
                action_id=botid,
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
                payload=self.payload(pairs, mad),
            )

            if error:
                self.logging.error(error["msg"])
            else:
                self.logging.debug("Pairs: " + str(pairs))
                if not self.attributes.get("ext_botswitch", False):
                    self.enable(data)
                else:
                    self.logging.info(
                        "ext_botswitch set to true, bot enabling/disabling has to be managed by external TV signal"
                    )

    def trigger(self, triggeronly=False):
        # Updates multi bot with new pairs
        triggerpair = ""
        mad = self.attributes.get("mad")
        # Get botname and botid according to DCA setting
        botname = self.attributes.get("prefix", "3CQSBOT", self.dca_conf) \
        + "_" + self.attributes.get("subprefix", "MULTI", self.dca_conf) \
        + "_" + self.attributes.get("suffix", "standard", self.dca_conf)
        botid = str(self.attributes.get("botid", "", self.dca_conf))

        for bot in self.bot_data:
            if botname == bot["name"] or botid == str(bot["id"]):

                if not triggeronly:
                    pair = self.tg_data["pair"]

                    self.logging.info(
                        "Got new 3cqs "
                        + self.tg_data["action"]
                        + " signal for "
                        + pair
                    )

                    if self.tg_data["action"] == "START":
                        triggerpair = pair

                        if pair in bot["pairs"]:
                            self.logging.info(
                                pair + " is already included in the pair list"
                            )
                        else:
                            pair = self.signal.topcoin(
                                pair,
                                self.attributes.get("topcoin_limit", 3500),
                                self.attributes.get("topcoin_volume", 0),
                                self.attributes.get("topcoin_exchange", "binance"),
                                self.attributes.get("market"),
                            )
                            if pair:
                                self.logging.info("Adding pair " + pair)
                                bot["pairs"].append(pair)
                    else:
                        if pair in bot["pairs"]:
                            self.logging.info("Remove pair " + pair)
                            bot["pairs"].remove(pair)
                        else:
                            self.logging.info(
                                pair
                                + " was not included in the pair list - not removed"
                            )

                    # Adapt mad if pairs are under value
                    mad = self.adjustmad(bot["pairs"], mad)
                    self.logging.info("Adjusting mad to amount of included symrank pairs: " + str(mad) + " and DCA setting: " + self.dca_conf)

                    error, data = self.p3cw.request(
                        entity="bots",
                        action="update",
                        action_id=str(bot["id"]),
                        additional_headers={
                            "Forced-Mode": self.attributes.get("trade_mode")
                        },
                        payload=self.payload(bot["pairs"], mad),
                    )

                    if error:
                        self.logging.error(error["msg"])
                else:
                    data = bot

                if self.attributes.get("deal_mode") == "signal" and data:
                    self.new_deal(data, triggerpair)
