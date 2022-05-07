import random
import json
import babel.numbers
import sys

from signals import Signals


class MultiBot:
    def __init__(
        self,
        tg_data,
        bot_data,
        account_data,
        pair_data,
        attributes,
        p3cw,
        logging,
        dca_conf,
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
        self.botid = str(self.attributes.get("botid", "", "dcabot"))
        self.botname = (
            self.attributes.get("prefix", self.attributes.get("prefix", "3CQSBOT", "dcabot"), self.dca_conf)
            + "_"
            + self.attributes.get("subprefix", self.attributes.get("subprefix", "MULTI", "dcabot"), self.dca_conf)
            + "_"
            + self.attributes.get("suffix", self.attributes.get("suffix", "dcabot", "dcabot"), self.dca_conf)
        )

    def strategy(self):
        if self.attributes.get("deal_mode", "signal", self.dca_conf) == "signal":
            strategy = [{"strategy": "manual"}]
        else:
            try:
                strategy = json.loads(self.attributes.get("deal_mode", "", self.dca_conf))
            except ValueError:
                self.logging.error(
                    "Either missing ["
                    + self.dca_conf
                    + "] section with DCA settings or decoding JSON string of deal_mode failed. Please check https://jsonformatter.curiousconcept.com/ for correct format"
                )
                sys.exit("Aborting script!")

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

    def report_funds_needed(self, maxdeals):
        tp = self.attributes.get("tp", "", self.dca_conf)
        bo = self.attributes.get("bo", "", self.dca_conf)
        so = self.attributes.get("so", "", self.dca_conf)
        os = self.attributes.get("os", "", self.dca_conf)
        ss = self.attributes.get("ss", "", self.dca_conf)
        sos = self.attributes.get("sos", "", self.dca_conf)
        mstc = self.attributes.get("mstc", "", self.dca_conf)

        fundsneeded = bo + so
        socalc = so
        pd = sos
        for i in range(mstc - 1):
            socalc = socalc * os
            fundsneeded += socalc
            pd = (pd * ss) + sos

        self.logging.info(
            "Using DCA settings ["
            + self.dca_conf
            + "]:  TP: "
            + str(tp)
            + "%  BO: $"
            + str(bo)
            + "  SO: $"
            + str(so)
            + "  OS: "
            + str(os)
            + "  SS: "
            + str(ss)
            + "  SOS: "
            + str(sos)
            + "%  MSTC: "
            + str(mstc)
            + " - covering max. price deviation: "
            + f"{pd:2.1f}"
            + "%",
            True
        )
        self.logging.info(
            "Max active deals (mad) allowed: "
            + str(maxdeals)
            + "   Max funds per active deal (all SO filled): "
            + babel.numbers.format_currency(fundsneeded, "USD", locale="en_US")
            + "   Total funds needed: "
            + babel.numbers.format_currency(
                maxdeals * fundsneeded, "USD", locale="en_US"
            ),
            True
        )

        return

    def payload(self, pairs, mad, new_bot):

        payload = {
            "name": self.botname,
            "account_id": self.account_data["id"],
            "pairs": pairs,
            "max_active_deals": mad,
            "base_order_volume": self.attributes.get("bo", "", self.dca_conf),
            "take_profit": self.attributes.get("tp", "", self.dca_conf),
            "safety_order_volume": self.attributes.get("so", "", self.dca_conf),
            "martingale_volume_coefficient": self.attributes.get(
                "os", "", self.dca_conf
            ),
            "martingale_step_coefficient": self.attributes.get("ss", "", self.dca_conf),
            "max_safety_orders": self.attributes.get("mstc", "", self.dca_conf),
            "safety_order_step_percentage": self.attributes.get(
                "sos", "", self.dca_conf
            ),
            "take_profit_type": "total",
            "active_safety_orders_count": self.attributes.get("max", "", self.dca_conf),
            "cooldown": self.attributes.get("cooldown", 0, self.dca_conf),
            "strategy_list": self.strategy(),
            "trailing_enabled": self.attributes.get("trailing", False, self.dca_conf),
            "trailing_deviation": self.attributes.get(
                "trailing_deviation", 0.2, self.dca_conf
            ),
            "allowed_deals_on_same_pair": self.attributes.get(
                "sdsp", "", self.dca_conf
            ),
            "min_volume_btc_24h": self.attributes.get("btc_min_vol", 0, self.dca_conf),
            "disable_after_deals_count": self.attributes.get(
                "deals_count", 0, self.dca_conf
            ),
        }

        if new_bot:
            if payload["disable_after_deals_count"] == 0:
                self.logging.debug("This is a new bot and deal_count set to 0, removing from payload")
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

    def enable(self, bot):
        # Enables an existing bot
        if not bot["is_enabled"]:
            self.logging.info(
                "Enabling bot: " + bot["name"] + " (botid: " + str(bot["id"]) + ")", 
                True
            )

            error, data = self.p3cw.request(
                entity="bots",
                action="enable",
                action_id=str(bot["id"]),
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
            )

            if error:
                self.logging.error(error["msg"])

        else:
            self.logging.info("'" + bot["name"] + "' (botid: " + str(bot["id"]) + ") enabled")

    def disable(self):
        # Disables an existing bot
        for bot in self.bot_data:
            if self.botid == bot["id"] or self.botname == bot["name"]:

                # Disables an existing bot
                self.logging.info(
                    "Disabling bot: " + bot["name"] + " (" + str(bot["id"]) + ")", 
                    True
                )

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
            self.logging.info(
                "Trigger new deal with pair " + pair, 
                True
            )
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
                        + " reached, not adding a new one.",
                        True
                    )
                else:
                    self.logging.error(error["msg"])

    def create(self):
        # Creates a multi bot with start signal
        bot_by_id = False
        bot_by_name = False
        pairs = []
        mad = self.attributes.get("mad")

        # Check for existing bot id
        if self.botid != "":
            botnames = []
            self.logging.info("Searching for 3cqsbot with botid: " + self.botid)
            for bot in self.bot_data:
                botnames.append(bot["name"])

                if self.botid == str(bot["id"]):
                    bot_by_id = True
                    self.logging.info(
                        "Botid " + self.botid + " with name '" + bot["name"] + "' found"
                    )
                    break

        # Check for existing name
        if not bot_by_id:
            if self.attributes.get("fearandgreed", False) and self.botid == "":
                self.logging.error("Please add 'botid = xxxxxxx' to [dcabot] for using FGI. FGI guided DCA settings will only applied to existent 3cqsbot.")
                self.logging.error("Script will be aborted if no botid is found by botname")

            botnames = []
            if self.botid != "":
                self.logging.info("3cqsbot not found with botid: " + self.botid)
                
            self.logging.info("Searching for 3cqsbot with name '" + self.botname + "' to get botid")
            for bot in self.bot_data:
                botnames.append(bot["name"])

                if self.botname == bot["name"]:
                    self.botid = str(bot["id"])
                    bot_by_name = True
                    self.logging.info(
                        "3cqsbot '"
                        + bot["name"]
                        + "' with botid "
                        + self.botid
                        + " found"
                    )
                    break
            if not bot_by_name:
                self.logging.info("3cqsbot not found with this name")

        self.logging.debug(
            "Checked bot ids/names till config id/name found: " + str(botnames)
        )

        # If FGI is used and botid is not set in [dcabot], which is mandatory to prevent creating new bots with different botids,
        # abort program for security reasons 
        if self.attributes.get("fearandgreed", False) and self.botid == "":
            self.logging.error("No botid set in [dcabot] and no 3cqsbot '" + self.botname + "' found on 3commas")
            self.logging.error("Please get botid on 3commas for an existent 3cqsbot and add 'botid = <botid of 3cqsbot>' under [dcabot] in config.ini")
            self.logging.error("If first time run of this script with enabled FGI and no 3cqsbot has been created so far,") 
            self.logging.error("create manually one on 3commas, get botid and leave the bot disabled") 
            sys.exit("Aborting script!")

        # Initial pair list
        pairlist = self.tg_data

        # Filter topcoins (if set)
        if self.attributes.get("topcoin_filter", False):
            pairlist = self.signal.topcoin(
                self.tg_data,
                self.attributes.get("topcoin_limit", 3500),
                self.attributes.get("topcoin_volume", 0),
                self.attributes.get("topcoin_exchange", "binance"),
                self.attributes.get("market"),
            )
        else:
            self.logging.info("Topcoin filter disabled, not filtering pairs!")

        for pair in pairlist:
            pair = self.attributes.get("market") + "_" + pair
            # Traded on our exchange?
            if pair in self.pair_data:
                self.logging.debug(pair + " added to the list")
                pairs.append(pair)
            else:
                self.logging.info(
                    pair
                    + " removed because pair is blacklisted on 3commas or in token_denylist or not tradable on '" 
                    + self.attributes.get("account_name")
                    + "'"
                )

        self.logging.debug("Pairs after topcoin filter " + str(pairs))

        # Run filters to adapt mad according to pair list - multibot creation with mad=1 possible
        if self.attributes.get("limit_initial_pairs", False):
            # Limit pairs to the maximal deals (mad)
            if self.attributes.get("mad") == 1:
                maxpairs = 1
            elif self.attributes.get("mad") <= len(pairs):
                maxpairs = self.attributes.get("mad")
            else:
                maxpairs = len(pairs)
            pairs = pairs[0:maxpairs]

            self.logging.debug("Pairs after limit initial pairs filter " + str(pairs))

        # Adapt mad if pairs are under value
        mad = self.adjustmad(pairs, mad)
        maxdeals = self.attributes.get("mad")
        self.logging.info(
            str(len(pairs)) 
            + " out of 30 symrank pairs selected "
            + str(pairs) 
            + ". Maximum active deals (mad) set to " 
            + str(mad) 
            + " out of " 
            + str(maxdeals),
            True
        )

        # Creation of multibot even with mad=1 possible
        if not bot_by_id and not bot_by_name and mad > 0:
            # Create new multibot
            self.logging.info(
                "Creating multi bot '" 
                + self.botname 
                + "' with filtered symrank pairs",
                True
            )
            self.report_funds_needed(maxdeals)

            error, data = self.p3cw.request(
                entity="bots",
                action="create_bot",
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
                payload=self.payload(pairs, mad, new_bot = True),
            )

            if error:
                self.logging.error(error["msg"])
            else:
                if not self.attributes.get("ext_botswitch", False):
                    self.enable(data)
                else:
                    self.logging.info(
                        "ext_botswitch set to true, bot has to be enabled by external TV signal",
                        True
                    )
                self.new_deal(data, triggerpair="")
        elif mad > 0:
            # Update existing multibot
            if self.botname != bot["name"]:
                self.logging.info(
                    "Renaming bot name from '"
                    + bot["name"]
                    + "' to '"
                    + self.botname
                    + "' (botid: "
                    + self.botid
                    + ")",
                    True
                )
                bot["name"] = self.botname

            self.logging.info(
                "Updating multi bot '"
                + bot["name"]
                + "' (botid: "
                + self.botid
                + ") with filtered symrank pairs",
                True
            )
            self.report_funds_needed(maxdeals)

            error, data = self.p3cw.request(
                entity="bots",
                action="update",
                action_id=self.botid,
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
                payload=self.payload(pairs, mad, new_bot = False),
            )

            if error:
                self.logging.error(error["msg"])
            else:
                self.logging.debug("Pairs: " + str(pairs))
                if not self.attributes.get("ext_botswitch", False):
                    self.enable(data)
                else:
                    self.logging.info(
                        "ext_botswitch set to true, bot enabling/disabling has to be managed by external TV signal",
                        True
                    )
        else:
            self.logging.info(
                "No (filtered) pairs left for multi bot. Either weak market phase or symrank/topcoin filter too strict. Bot will be disabled to wait for better times",
                True
                )
            self.disable()

    def trigger(self, triggeronly=False):
        # Updates multi bot with new pairs
        triggerpair = ""
        mad = self.attributes.get("mad")

        for bot in self.bot_data:
            if self.botname == bot["name"] or self.botid == str(bot["id"]):

                if not triggeronly:
                    pair = self.tg_data["pair"]

                    self.logging.info(
                        "Got new 3cqs " + self.tg_data["action"] + " signal for " + pair
                    )

                    if self.tg_data["action"] == "START":
                        triggerpair = pair

                        if pair in bot["pairs"]:
                            self.logging.info(
                                pair + " is already included in the pair list"
                            )
                        else:
                            # Filter topcoins (if set)
                            if self.attributes.get("topcoin_filter", False):
                                pair = self.signal.topcoin(
                                    pair,
                                    self.attributes.get("topcoin_limit", 3500),
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
                                    "Adding pair " + pair, 
                                    True
                                )
                                bot["pairs"].append(pair)
                    else:
                        if pair in bot["pairs"]:
                            self.logging.info(
                                "Removing pair " + pair, 
                                True
                            )
                            bot["pairs"].remove(pair)
                        else:
                            self.logging.info(
                                pair + " was not included in the pair list - not removed"
                            )

                    # Adapt mad if included pairs and simul. deals for the same pair are lower than mad value
                    mad = self.adjustmad(bot["pairs"], mad)
                    self.logging.info(
                        "Included pairs: "
                        + str(bot["pairs"])
                        + ". Adjusting mad to: "
                        + str(mad),
                        True
                    )

                    error, data = self.p3cw.request(
                        entity="bots",
                        action="update",
                        action_id=str(bot["id"]),
                        additional_headers={
                            "Forced-Mode": self.attributes.get("trade_mode")
                        },
                        payload=self.payload(bot["pairs"], mad, new_bot = False),
                    )

                    if error:
                        self.logging.error(error["msg"])
                else:
                    data = bot

                if self.attributes.get("deal_mode") == "signal" and data:
                    self.new_deal(data, triggerpair)
