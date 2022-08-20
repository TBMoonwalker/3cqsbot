import json
import random
import sys
from datetime import datetime

from babel.dates import format_timedelta
from babel.numbers import format_currency

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
        asyncState,
    ):
        self.tg_data = tg_data
        self.bot_data = bot_data
        self.account_data = account_data
        self.pair_data = pair_data
        self.attributes = attributes
        self.p3cw = p3cw
        self.logging = logging
        self.asyncState = asyncState
        self.signal = Signals(logging)
        self.config_botid = str(self.attributes.get("botid", "", "dcabot"))
        self.botname = (
            self.attributes.get(
                "prefix",
                self.attributes.get("prefix", "3CQSBOT", "dcabot"),
                self.asyncState.dca_conf,
            )
            + "_"
            + self.attributes.get(
                "subprefix",
                self.attributes.get("subprefix", "MULTI", "dcabot"),
                self.asyncState.dca_conf,
            )
            + "_"
            + self.attributes.get(
                "suffix",
                self.attributes.get("suffix", "dcabot", "dcabot"),
                self.asyncState.dca_conf,
            )
        )

    def report_deals(self, report_latency=False):
        self.logging.info(
            "Deals active: "
            + str(self.asyncState.multibot["active_deals_count"])
            + "/"
            + str(self.asyncState.multibot["max_active_deals"]),
            True,
        )
        self.logging.info(
            "Profits of "
            + str(self.asyncState.multibot["finished_deals_count"])
            + " finished deals: "
            + format_currency(
                self.asyncState.multibot["finished_deals_profit_usd"],
                "USD",
                locale="en_US",
            ),
            True,
        )
        self.logging.info(
            "uPNL of active deals: "
            + format_currency(
                self.asyncState.multibot["active_deals_usd_profit"],
                "USD",
                locale="en_US",
            ),
            True,
        )

        error, data = self.p3cw.request(
            entity="deals",
            action="",
            action_id="",
            additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
            payload={
                "limit": 100,
                "bot_id": self.asyncState.multibot["id"],
                "scope": "active",
            },
        )
        if error:
            self.logging.error("function report_deals: " + error["msg"])
        else:
            i = 1
            total_bought_volume = 0
            for deals in data:

                if i == 1 and report_latency:
                    self.logging.info(
                        "Time delta between 3cqs signal and actual deal creation: "
                        + format_timedelta(
                            datetime.strptime(
                                deals["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
                            )
                            - self.asyncState.latest_signal_time,
                            locale="en_US",
                        ),
                        True,
                    )
                i += 1

                if (
                    deals["bought_volume"] == None
                ):  # if no bought_volume, then use base_order_volume for bought_volume
                    bought_volume = format_currency(
                        deals["base_order_volume"], "USD", locale="en_US"
                    )
                    total_bought_volume += float(deals["base_order_volume"])
                else:
                    bought_volume = format_currency(
                        deals["bought_volume"], "USD", locale="en_US"
                    )
                    total_bought_volume += float(deals["bought_volume"])
                self.logging.info(
                    "Deal "
                    + deals["pair"]
                    + " open since "
                    + format_timedelta(
                        datetime.utcnow()
                        - datetime.strptime(
                            deals["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        locale="en_US",
                    )
                    + "   Actual profit: "
                    + format_currency(deals["actual_usd_profit"], "USD", locale="en_US")
                    + " ("
                    + deals["actual_profit_percentage"]
                    + "%)"
                    + "   Bought volume: "
                    + bought_volume
                    + "   Deal error: "
                    + str(deals["deal_has_error"]),
                    True,
                )
            self.logging.info(
                "Total bought volume of all deals: "
                + format_currency(total_bought_volume, "USD", locale="en_US"),
                True,
            )
        return

    def report_funds_needed(self, maxdeals):

        self.logging.info(
            "Deal start condition(s): "
            + self.attributes.get("deal_mode", "", self.asyncState.dca_conf),
            True,
        )

        tp = self.attributes.get("tp", "", self.asyncState.dca_conf)
        bo = self.attributes.get("bo", "", self.asyncState.dca_conf)
        so = self.attributes.get("so", "", self.asyncState.dca_conf)
        os = self.attributes.get("os", "", self.asyncState.dca_conf)
        ss = self.attributes.get("ss", "", self.asyncState.dca_conf)
        sos = self.attributes.get("sos", "", self.asyncState.dca_conf)
        mstc = self.attributes.get("mstc", "", self.asyncState.dca_conf)

        fundsneeded = bo + so
        socalc = so
        pd = sos
        for i in range(mstc - 1):
            socalc = socalc * os
            fundsneeded += socalc
            pd = (pd * ss) + sos

        self.logging.info(
            "Using DCA settings ["
            + self.asyncState.dca_conf
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
            True,
        )
        self.logging.info(
            "Max active deals (mad) allowed: "
            + str(maxdeals)
            + "   Max funds per active deal (all SO filled): "
            + format_currency(fundsneeded, "USD", locale="en_US")
            + "   Total funds needed: "
            + format_currency(maxdeals * fundsneeded, "USD", locale="en_US"),
            True,
        )

        return

    def strategy(self):
        if self.attributes.get("deal_mode", "", self.asyncState.dca_conf) == "signal":
            strategy = [{"strategy": "manual"}]
        else:
            try:
                strategy = json.loads(
                    self.attributes.get("deal_mode", "", self.asyncState.dca_conf)
                )
            except ValueError:
                self.logging.error(
                    "Either missing ["
                    + self.asyncState.dca_conf
                    + "] section with DCA settings or decoding JSON string of deal_mode failed. "
                    + "Please check https://jsonformatter.curiousconcept.com/ for correct format"
                )
                sys.exit("Aborting script!")

        return strategy

    def payload(self, pairs, mad, new_bot):

        payload = {
            "name": self.botname,
            "account_id": self.account_data["id"],
            "pairs": pairs,
            "max_active_deals": mad,
            "base_order_volume": self.attributes.get(
                "bo", "", self.asyncState.dca_conf
            ),
            "take_profit": self.attributes.get("tp", "", self.asyncState.dca_conf),
            "safety_order_volume": self.attributes.get(
                "so", "", self.asyncState.dca_conf
            ),
            "martingale_volume_coefficient": self.attributes.get(
                "os", "", self.asyncState.dca_conf
            ),
            "martingale_step_coefficient": self.attributes.get(
                "ss", "", self.asyncState.dca_conf
            ),
            "max_safety_orders": self.attributes.get(
                "mstc", "", self.asyncState.dca_conf
            ),
            "safety_order_step_percentage": self.attributes.get(
                "sos", "", self.asyncState.dca_conf
            ),
            "take_profit_type": "total",
            "active_safety_orders_count": self.attributes.get(
                "max", "", self.asyncState.dca_conf
            ),
            "cooldown": self.attributes.get("cooldown", 0, self.asyncState.dca_conf),
            "strategy_list": self.strategy(),
            "trailing_enabled": self.attributes.get(
                "trailing", False, self.asyncState.dca_conf
            ),
            "trailing_deviation": self.attributes.get(
                "trailing_deviation", 0.2, self.asyncState.dca_conf
            ),
            "allowed_deals_on_same_pair": self.attributes.get(
                "sdsp", "", self.asyncState.dca_conf
            ),
            "min_volume_btc_24h": self.attributes.get(
                "btc_min_vol", 0, self.asyncState.dca_conf
            ),
            "disable_after_deals_count": self.attributes.get(
                "deals_count", 0, self.asyncState.dca_conf
            ),
        }

        if new_bot:
            if payload["disable_after_deals_count"] == 0:
                self.logging.debug(
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

    def adjust_mad(self, pairs, mad):
        # Lower max active deals, when pairs are under mad
        if len(pairs) * self.attributes.get("sdsp") < mad:
            self.logging.debug(
                "Pairs are under 'mad' - Lower max active deals to actual pairs"
            )
            mad = len(pairs)
        # Raise max active deals to minimum pairs or mad if possible
        elif len(pairs) * self.attributes.get("sdsp") >= mad:
            self.logging.debug("Pairs are equal or over 'mad' - nothing to do")
            mad = self.attributes.get("mad")

        return mad

    def search_rename_3cqsbot(self):

        bot_by_id = False
        bot_by_name = False

        # Search 3cqsbot by given botid in config
        if self.config_botid != "":

            self.logging.info(
                "Searching for 3cqsbot with botid: " + self.config_botid, True
            )
            for bot in self.bot_data:

                if self.config_botid == str(bot["id"]):
                    bot_by_id = True
                    self.logging.info(
                        "Botid "
                        + self.config_botid
                        + " with name '"
                        + bot["name"]
                        + "' found. Enabled: '"
                        + str(bot["is_enabled"])
                        + "'",
                        True,
                    )
                    # if 3cqsbot found by id, rename bot if needed according to config name settings
                    if self.botname != bot["name"]:
                        self.logging.info(
                            "Renaming bot name from '"
                            + bot["name"]
                            + "' to '"
                            + self.botname
                            + "' (botid: "
                            + str(bot["id"])
                            + ")",
                            True,
                        )
                    bot["name"] = self.botname

                    mad = self.attributes.get("mad")
                    mad = self.adjust_mad(bot["pairs"], mad)

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
                        self.logging.error(
                            "function search_rename_3cqsbot: " + error["msg"]
                        )
                    else:
                        self.asyncState.multibot = data

                    return

        # If botid given and 3cqsbot not found exit
        if self.config_botid != "" and not bot_by_id:
            self.logging.error(
                "3cqsbot not found with botid: " + self.config_botid, True
            )
            sys.exit("Aborting script. Please check for correct botid in config.ini!")

        # If no botid given and fearandgreed is set to true, then exit
        if self.config_botid == "" and self.attributes.get("fearandgreed", False):
            self.logging.error(
                "Please add 'botid = xxxxxxx' to [dcabot] for using FGI. FGI guided DCA settings will only applied "
                + "to existent 3cqsbot. \n Script will be aborted if no 3cqsbot is found by botname"
            )

        self.logging.info(
            "Searching for 3cqsbot with name '" + self.botname + "' to get botid",
            True,
        )
        for bot in self.bot_data:

            if self.botname == bot["name"]:
                bot_by_name = True
                self.logging.info(
                    "3cqsbot '"
                    + bot["name"]
                    + "' with botid "
                    + str(bot["id"])
                    + " found. Enabled: '"
                    + str(bot["is_enabled"])
                    + "'",
                    True,
                )

                mad = self.attributes.get("mad")
                mad = self.adjust_mad(bot["pairs"], mad)
                # always get a status update when searching first time for the bot
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
                    self.logging.error(
                        "function search_rename_3cqsbot: " + error["msg"]
                    )
                else:
                    self.asyncState.multibot = data

                return

        if not bot_by_name:
            self.logging.info("3cqsbot not found with this name", True)
            bot["name"] = ""

            # If FGI is used and botid is not set in [dcabot], which is mandatory to prevent creating new bots with different botids,
            # abort program for security reasons
            if self.config_botid == "" and self.attributes.get("fearandgreed", False):
                self.logging.error(
                    "No botid set in [dcabot] and no 3cqsbot '"
                    + self.botname
                    + "' found on 3commas"
                )
                self.logging.error(
                    "Please get botid on 3commas for an existent 3cqsbot and add 'botid = <botid of 3cqsbot>' under [dcabot] in config.ini"
                )
                self.logging.error(
                    "If first time run of this script with enabled FGI and no 3cqsbot has been created so far,"
                )
                self.logging.error(
                    "create manually one on 3commas, get botid and leave the bot disabled"
                )
                sys.exit("Aborting script!")

    def enable(self):
        # search for 3cqsbot by id or by name if bot not given
        if not isinstance(self.bot_data, dict) and self.asyncState.multibot == {}:
            self.search_rename_3cqsbot()

        if not self.asyncState.multibot["is_enabled"]:
            self.logging.info(
                "Enabling bot: "
                + self.asyncState.multibot["name"]
                + " (botid: "
                + str(self.asyncState.multibot["id"])
                + ")",
                True,
            )

            error, data = self.p3cw.request(
                entity="bots",
                action="enable",
                action_id=str(self.asyncState.multibot["id"]),
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
            )

            if error:
                self.logging.error("function enable: " + error["msg"])
            else:
                self.asyncState.multibot = data
                self.logging.info("Enabling successful", True)
                self.asyncState.bot_active = True

        elif self.asyncState.multibot["is_enabled"]:
            self.logging.info(
                "'"
                + self.asyncState.multibot["name"]
                + "' (botid: "
                + str(self.asyncState.multibot["id"])
                + ") already enabled",
                True,
            )
            self.asyncState.bot_active = True
        else:
            self.logging.info(
                "'"
                + self.botname
                + "' or botid: "
                + str(self.config_botid)
                + " not found to enable",
                True,
            )

    def disable(self):
        # search for 3cqsbot by id or by name if bot not given
        if not isinstance(self.bot_data, dict) and self.asyncState.multibot == {}:
            self.search_rename_3cqsbot()

        if self.asyncState.multibot["is_enabled"]:
            self.logging.info(
                "Disabling bot: "
                + self.asyncState.multibot["name"]
                + " (botid: "
                + str(self.asyncState.multibot["id"])
                + ")",
                True,
            )

            error, data = self.p3cw.request(
                entity="bots",
                action="disable",
                action_id=str(self.asyncState.multibot["id"]),
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
            )

            if error:
                self.logging.error("function disable: " + error["msg"])
            else:
                self.asyncState.multibot = data
                self.logging.info("Disabling successful", True)
                self.asyncState.bot_active = False

        elif not self.asyncState.multibot["is_enabled"]:
            self.logging.info(
                "'"
                + self.asyncState.multibot["name"]
                + "' (botid: "
                + str(self.asyncState.multibot["id"])
                + ") already disabled",
                True,
            )
            self.asyncState.bot_active = False
        else:
            self.logging.info(
                "'"
                + self.botname
                + "' or botid: "
                + str(self.config_botid)
                + " not found to disable",
                True,
            )

    def new_deal(self, triggerpair):
        more_inform = self.attributes.get("extensive_notifications", False)
        # Triggers a new deal
        if triggerpair:
            pair = triggerpair
        else:
            if self.attributes.get("random_pair", "False"):
                pair = random.choice(self.asyncState.multibot["pairs"])
                self.logging.info(pair + " is the randomly chosen pair to start")
            else:
                pair = ""

        if pair:
            error, data = self.p3cw.request(
                entity="bots",
                action="start_new_deal",
                action_id=str(self.asyncState.multibot["id"]),
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
                payload={"pair": pair},
            )

            if error:
                self.logging.info(
                    "Triggering new deal for pair "
                    + pair
                    + " with strategy: '"
                    + self.strategy()[0]["strategy"]
                    + "' - unsuccessful",
                    True,
                )
                if (
                    self.asyncState.multibot["active_deals_count"]
                    >= self.asyncState.multibot["max_active_deals"]
                ):
                    self.logging.info(
                        "Max active deals of "
                        + str(self.asyncState.multibot["max_active_deals"])
                        + " reached, not adding a new one.",
                        more_inform,
                    )
                else:
                    # modified output because of open deal - this will be the most common error
                    self.logging.info(
                        "No deal triggered because of "
                        + error["msg"].split(":")[1].split(" ")[1],
                        more_inform,
                    )
                return False
            else:
                self.logging.info(
                    "Triggering new deal for pair "
                    + pair
                    + " with strategy: '"
                    + self.strategy()[0]["strategy"]
                    + "' - successful",
                    True,
                )
                self.asyncState.multibot["active_deals_count"] += 1
                return True

    def create(self):
        more_inform = self.attributes.get("extensive_notifications", False)
        # if dealmode is signal (aka strategy == manual for multibot),
        # preserve pair list of bot. 3cqs START signal triggers deal
        dealmode_is_signal = (
            self.attributes.get("deal_mode", "", self.asyncState.dca_conf) == "signal"
        )

        # Check if data of 3cqsbot is given (dict format), else search for existing one in the list before creating a new one
        if not isinstance(self.bot_data, dict) and self.asyncState.multibot == {}:
            self.search_rename_3cqsbot()

        # if 3cqsbot was found use bot's pair list if dealmode_is_signal
        if self.asyncState.multibot and dealmode_is_signal:
            pairs = self.asyncState.multibot["pairs"]
        else:
            pairs = []

        mad = self.attributes.get("mad")
        maxdeals = mad
        # if dealmode_is_signal use signal pair to create/update bot, else check the 30 symrank pairs obtained by symrank call
        if dealmode_is_signal:
            # single pair from START signal with quote currency passed to pairlist for topcoin filter check
            pairlist = self.tg_data["pair"]
        else:
            # initial pair list obtained by symrank call without quote currencies passed
            pairlist = self.tg_data

        # Filter topcoins if set
        # if first_topcoin_call == true then CG API requests are processed with latency of 2.2sec to avoid API timeout erros
        if self.attributes.get("topcoin_filter", False):
            pairlist, pairlist_volume = self.signal.topcoin(
                pairlist,
                self.attributes.get("topcoin_limit", 3500),
                self.attributes.get("topcoin_volume", 0),
                self.attributes.get("topcoin_exchange", "binance"),
                self.attributes.get("market"),
                self.asyncState.first_topcoin_call,
            )
            if isinstance(pairlist, list):
                self.asyncState.first_topcoin_call = False
        else:
            self.logging.info(
                "Topcoin filter disabled, not filtering pairs!", more_inform
            )

        # if no filtered coins left -> exit function
        if not pairlist:
            self.logging.info("No pair(s) left after topcoin filter", True)
            return

        if pairlist and dealmode_is_signal:
            pair = pairlist
            if self.asyncState.multibot:
                if pair in self.asyncState.multibot["pairs"]:
                    self.logging.info(
                        pair + " is already included in the pair list", more_inform
                    )
            elif pair in self.pair_data:
                self.logging.debug(pair + " added to the pair list")
                pairs.append(pair)
            else:
                self.logging.info(
                    pair
                    + " not included because pair is blacklisted on 3commas or in token_denylist "
                    + "or not tradable on '"
                    + self.attributes.get("account_name")
                    + "'",
                    more_inform,
                )
        elif pairlist:
            for pair in pairlist:
                pair = self.attributes.get("market") + "_" + pair
                # Traded on our exchange?
                if pair in self.pair_data:
                    self.logging.debug(pair + " added to the pair list")
                    pairs.append(pair)
                else:
                    self.logging.info(
                        pair
                        + " not included because pair is blacklisted on 3commas or in token_denylist "
                        + "or not tradable on '"
                        + self.attributes.get("account_name")
                        + "'",
                        more_inform,
                    )
            for pair in pairlist_volume:
                market_pair = self.attributes.get("market") + "_" + pair[0]
                if market_pair in self.pair_data:
                    self.asyncState.pairs_volume.append(pair)

        self.logging.debug("Pairs after topcoin filter " + str(pairs))

        # Run filters to adapt mad according to pair list - multibot creation with mad=1 possible
        if self.attributes.get("limit_symrank_pairs_to_mad", False):
            # Limit pairs to the maximal deals (mad)
            if self.attributes.get("mad") == 1:
                maxpairs = 1
            elif len(pairs) >= self.attributes.get("mad"):
                maxpairs = self.attributes.get("mad")
            else:
                maxpairs = len(pairs)
            pairs = pairs[0:maxpairs]
            self.asyncState.pairs_volume = self.asyncState.pairs_volume[0:maxpairs]
            self.logging.info(
                "Limiting volume sorted symrank list to max active deals of "
                + str(maxpairs),
                more_inform,
            )

        # Adapt mad if pairs are under value
        mad = self.adjust_mad(pairs, mad)
        if not dealmode_is_signal:
            self.logging.info(
                str(len(pairs))
                + " out of 30 symrank pairs selected "
                + str(pairs)
                + ". Maximum active deals (mad) set to "
                + str(mad)
                + " out of "
                + str(maxdeals),
                True,
            )

        # Create new multibot
        if self.asyncState.multibot["name"] == "" and mad > 0:
            self.logging.info(
                "Creating multi bot '" + self.botname + "'",
                True,
            )
            self.report_funds_needed(maxdeals)
            # for creating a multibot at least 2 pairs needed
            if mad == 1:
                pairs.append(self.attributes.get("market") + "_BTC")
                self.logging.info(
                    "For creating a multipair bot at least 2 pairs needed, adding "
                    + pairs[1]
                    + " to signal pair "
                    + pairs[0],
                    True,
                )
                mad = 2

            error, data = self.p3cw.request(
                entity="bots",
                action="create_bot",
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
                payload=self.payload(pairs, mad, new_bot=True),
            )

            if error:
                self.logging.error("function create: " + error["msg"])
                if error["msg"].find("Read timed out") > -1:
                    self.logging.error(
                        "HTTPS connection problems to 3commas - exiting program - please retry later",
                        True,
                    )
                    sys.exit(-1)
            else:
                self.asyncState.multibot = data
                if (
                    not self.attributes.get("ext_botswitch", False)
                    and not self.asyncState.btc_downtrend
                    and self.asyncState.fgi_allows_trading
                ):
                    self.enable()

                elif self.attributes.get("ext_botswitch", False):
                    self.logging.info(
                        "ext_botswitch set to true, bot has to be enabled by external TV signal",
                        True,
                    )

                if dealmode_is_signal:
                    successful_deal = self.new_deal(pair)
                elif self.attributes.get("random_pair", "False"):
                    successful_deal = self.new_deal(triggerpair="")

        # Update existing multibot
        elif mad > 0:
            self.logging.info(
                "Updating multi bot '"
                + self.asyncState.multibot["name"]
                + "' (botid: "
                + str(self.asyncState.multibot["id"])
                + ") with filtered pair(s)",
                True,
            )
            self.report_funds_needed(maxdeals)

            error, data = self.p3cw.request(
                entity="bots",
                action="update",
                action_id=str(self.asyncState.multibot["id"]),
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
                payload=self.payload(pairs, mad, new_bot=False),
            )

            if error:
                self.logging.error("function create: " + error["msg"])
            else:
                self.asyncState.multibot = data
                self.logging.debug("Pairs: " + str(pairs))
                if (
                    not self.attributes.get("ext_botswitch", False)
                    and not self.asyncState.btc_downtrend
                    and self.asyncState.fgi_allows_trading
                ):
                    self.enable()
                elif self.attributes.get("ext_botswitch", False):
                    self.logging.info(
                        "ext_botswitch set to true, bot enabling/disabling has to be managed by external TV signal",
                        True,
                    )
        else:
            self.logging.info(
                "No (filtered) pairs left for multi bot. Either weak market phase or symrank/topcoin filter too strict. Bot will be disabled to wait for better times",
                True,
            )
            self.disable()

    def trigger(self, random_only=False):
        more_inform = self.attributes.get("extensive_notifications", False)
        # Updates multi bot with new pairs
        pair = ""
        mad = self.attributes.get("mad")
        dealmode_is_signal = (
            self.attributes.get("deal_mode", "", self.asyncState.dca_conf) == "signal"
        )

        # Check if data of 3cqsbot is given (dict format), else search for existing one in the list before creating a new one
        if not isinstance(self.bot_data, dict) and self.asyncState.multibot == {}:
            self.search_rename_3cqsbot()

        if not random_only and (
            self.asyncState.bot_active
            or self.attributes.get("continuous_update", False)
        ):
            pair = self.tg_data["pair"]  # signal pair with quote currency returned

            if (
                self.attributes.get("continuous_update", False)
                and not self.asyncState.bot_active
            ):
                self.logging.info(
                    "Continuous update active for disabled bot", more_inform
                )

            if self.tg_data["action"] == "START":

                # Filter pair according to topcoin criteria if set
                if self.attributes.get("topcoin_filter", False):
                    pair, pair_volume = self.signal.topcoin(
                        pair,
                        self.attributes.get("topcoin_limit", 3500),
                        self.attributes.get("topcoin_volume", 0),
                        self.attributes.get("topcoin_exchange", "binance"),
                        self.attributes.get("market"),
                        self.asyncState.first_topcoin_call,
                    )
                else:
                    self.logging.info(
                        "Topcoin filter disabled, not filtering pairs!", more_inform
                    )
                if pair:
                    if pair in self.asyncState.multibot["pairs"]:
                        self.logging.info(
                            pair + " is already included in the pair list", more_inform
                        )
                    else:
                        if self.attributes.get("topcoin_filter", False):
                            self.logging.info(
                                "Adding "
                                + pair
                                + " to pair list - topcoin filter criteria passed",
                                True,
                            )
                        else:
                            self.logging.info("Adding " + pair, True)

                        self.asyncState.multibot["pairs"].append(pair)

                        # if limit_symrank_pairs_to_mad == True, add trigger pair to pairs_volume list and sort
                        if (
                            self.attributes.get("limit_symrank_pairs_to_mad", False)
                            and self.asyncState.pairs_volume
                        ):
                            self.asyncState.pairs_volume.append(pair_volume)
                            self.asyncState.pairs_volume = sorted(
                                self.asyncState.pairs_volume,
                                key=lambda x: x[1],
                                reverse=True,
                            )
                            self.asyncState.multibot["pairs"] = []
                            for i in range(len(self.asyncState.pairs_volume)):
                                self.asyncState.multibot["pairs"].append(
                                    self.attributes.get("market")
                                    + "_"
                                    + self.asyncState.pairs_volume[i][0]
                                )

            # do not remove pairs when deal_mode == "signal" to trigger deals faster when next START signal is received
            elif self.tg_data["action"] == "STOP":

                if not dealmode_is_signal:
                    if pair in self.asyncState.multibot["pairs"]:
                        self.logging.info(
                            "STOP signal for "
                            + pair
                            + " received - removing from pair list",
                            True,
                        )
                        self.asyncState.multibot["pairs"].remove(pair)
                    else:
                        self.logging.info(
                            pair + " not removed because it was not in the pair list",
                            more_inform,
                        )
                else:
                    self.logging.info(
                        pair + " ignored because deal_mode is 'signal'", more_inform
                    )

            mad_before = mad
            mad = self.adjust_mad(self.asyncState.multibot["pairs"], mad_before)
            if mad > mad_before:
                self.logging.info("Adjusting mad to: " + str(mad), True)

            # even with no pair, always update get an update of active / finished deals
            error, data = self.p3cw.request(
                entity="bots",
                action="update",
                action_id=str(self.asyncState.multibot["id"]),
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
                payload=self.payload(
                    self.asyncState.multibot["pairs"], mad, new_bot=False
                ),
            )

            if error:
                self.logging.error("function trigger: " + error["msg"])
            else:
                self.asyncState.multibot = data

            # avoid triggering a deal if STOP signal
            if self.tg_data["action"] == "STOP":
                pair = ""

        # if random_only == true and deal_mode == "signal" then
        # initiate deal with a random coin (random_pair=true) from the filtered symrank pair list
        # if pair not empty and deal_mode == "signal" then initiate new deal
        if (
            (random_only or pair)
            and dealmode_is_signal
            and self.asyncState.multibot
            and self.asyncState.bot_active
        ):
            if (
                self.asyncState.multibot["active_deals_count"]
                < self.asyncState.multibot["max_active_deals"]
            ):
                successful_deal = self.new_deal(pair)
            else:
                successful_deal = False
                if self.asyncState.multibot["max_active_deals"] == self.attributes.get(
                    "mad", "", self.asyncState.dca_conf
                ):
                    self.logging.info(
                        "Max active deals reached, not triggering a new one.",
                        more_inform,
                    )
                else:
                    self.logging.info(
                        "Deal with this pair already active, not triggering a new one.",
                        more_inform,
                    )
            self.report_deals(successful_deal)
