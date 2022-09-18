import json
import re
import time
from datetime import datetime

from babel.dates import format_timedelta
from babel.numbers import format_currency
from pytz import UTC

from signals import Signals


class SingleBot:
    def __init__(
        self, tg_data, bot_data, account_data, attributes, p3cw, logging, asyncState
    ):
        self.tg_data = tg_data
        self.bot_data = bot_data
        self.account_data = account_data
        self.attributes = attributes
        self.p3cw = p3cw
        self.logging = logging
        self.asyncState = asyncState
        self.signal = Signals(logging)
        self.prefix = self.attributes.get("prefix", "3CQSBOT", "dcabot")
        self.subprefix = self.attributes.get("subprefix", "SINGLE", "dcabot")
        self.suffix = self.attributes.get("suffix", "dcabot", "dcabot")
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

    def count_active_deals(self):
        #        account = self.account_data
        deals = 0
        bots = []

        for bot in self.bot_data:
            if re.search(self.bot_name, bot["name"]):
                deals += int(bot["active_deals_count"])
                if int(bot["active_deals_count"]) > 0:
                    bots.append(bot)

        self.logging.debug(
            "Active deals of single bots (enabled and disabled): " + str(deals)
        )

        return deals, bots

    def count_active_deals_disabled_bots(self):

        bots = []

        for bot in self.bot_data:
            if (
                re.search(self.bot_name, bot["name"])
                and not bot["is_enabled"]
                and bot["active_deals_count"] > 0
            ):
                bots.append(bot)

        self.logging.debug("Disabled single bots with active deals: " + str(len(bots)))

        return len(bots), bots

    def count_enabled_bots(self):

        bots = []

        for bot in self.bot_data:
            if re.search(self.bot_name, bot["name"]) and bot["is_enabled"]:
                bots.append(bot)

        self.logging.debug("Enabled single bots: " + str(len(bots)))

        return len(bots), bots

    def count_all_bots(self):

        bots = []

        for bot in self.bot_data:
            if re.search(self.bot_name, bot["name"]):
                bots.append(bot)

        self.logging.debug("All single bots: " + str(len(bots)))

        return len(bots), bots

    def report_funds_needed(self, maxdeals):

        tp = self.attributes.get("tp", "", self.asyncState.dca_conf)
        bo = self.attributes.get("bo", "", self.asyncState.dca_conf)
        so = self.attributes.get("so", "", self.asyncState.dca_conf)
        os = self.attributes.get("os", "", self.asyncState.dca_conf)
        ss = self.attributes.get("ss", "", self.asyncState.dca_conf)
        sos = self.attributes.get("sos", "", self.asyncState.dca_conf)
        mstc = self.attributes.get("mstc", "", self.asyncState.dca_conf)

        fundsneeded = bo + so
        amount = so
        pd = sos
        cum_size_base = bo + so / (1 - (1 * sos / 100))
        for i in range(mstc - 1):
            amount = amount * os
            fundsneeded += amount
            pd = (pd * ss) + sos
            price = (100 - pd) / 100
            size_base = amount / price
            cum_size_base += size_base
            avg_price = fundsneeded / cum_size_base
            required_price = avg_price * tp / 100 + avg_price
            required_change = ((required_price / price) - 1) * 100

        self.logging.info(
            "["
            + self.asyncState.dca_conf
            + "] TP: "
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
            + " - covering max price dev: "
            + f"{pd:2.1f}"
            + "% - max required change: "
            + f"{required_change:2.1f}%",
            True,
        )
        self.logging.info(
            "Max possible single bot deals: "
            + str(maxdeals)
            + "   Funds per single bot deal: "
            + format_currency(fundsneeded, "USD", locale="en_US")
            + "   Total funds needed: "
            + format_currency(maxdeals * fundsneeded, "USD", locale="en_US"),
            True,
        )

        return

    def report_deals(self):

        counted_active_deals, bots_with_active_deals = self.count_active_deals()
        counted_all_bots, all_bots = self.count_all_bots()

        self.logging.info(
            "Active deals running: "
            + str(counted_active_deals)
            + "/"
            + str(self.attributes.get("single_count", "", self.asyncState.dca_conf)),
            True,
        )

        total_profit = 0
        for bot in all_bots:
            total_profit += float(bot["finished_deals_profit_usd"])
        self.logging.info(
            "Total profit of "
            + str(counted_all_bots)
            + " single bots with finished deals: "
            + format_currency(total_profit, "USD", locale="en_US"),
            True,
        )

        for bot in bots_with_active_deals:
            error, data = self.p3cw.request(
                entity="deals",
                action="",
                action_id="",
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
                payload={"limit": 100, "bot_id": bot["id"]},
            )
            # sometimes API request error, instead report bot data with less details
            if error:
                self.logging.info(
                    "Open deal "
                    + bot["pairs"][0]
                    + " since "
                    + format_timedelta(
                        datetime.utcnow()
                        - datetime.strptime(bot["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ"),
                        locale="en_US",
                    )
                    + "   Actual profit: "
                    + format_currency(
                        bot["active_deals_usd_profit"], "USD", locale="en_US"
                    )
                )
            else:
                for deals in data:
                    if not deals["finished?"]:
                        if (
                            deals["bought_volume"] == None
                        ):  # if no bought_volume, then use base_order_volume for bought_volume
                            bought_volume = format_currency(
                                deals["base_order_volume"], "USD", locale="en_US"
                            )
                        else:
                            bought_volume = format_currency(
                                deals["bought_volume"], "USD", locale="en_US"
                            )

                        self.logging.info(
                            "Open deal "
                            + deals["pair"]
                            + " since "
                            + format_timedelta(
                                datetime.utcnow()
                                - datetime.strptime(
                                    deals["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
                                ),
                                locale="en_US",
                            )
                            + "   Actual profit: "
                            + format_currency(
                                deals["actual_usd_profit"], "USD", locale="en_US"
                            )
                            + " ("
                            + deals["actual_profit_percentage"]
                            + "%)"
                            + "   Bought volume: "
                            + bought_volume
                            + "   Deal error: "
                            + str(deals["deal_has_error"]),
                            True,
                        )

        return

    def get_deal_mode(self):
        strategy = self.attributes.get("deal_mode", "test", self.asyncState.dca_conf)
        if strategy == "test":
            strategy = self.attributes.get("deal_mode", "")
        return strategy

    def strategy(self):
        deal_mode = self.get_deal_mode()
        if deal_mode == "signal":
            strategy = [{"strategy": "nonstop"}]
        else:
            try:
                strategy = json.loads(deal_mode)
            except ValueError:
                self.logging.error(
                    "Either missing ["
                    + self.asyncState.dca_conf
                    + "] section with DCA settings or decoding JSON string of deal_mode failed. Please check https://jsonformatter.curiousconcept.com/ for correct format"
                )

        return strategy

    def payload(self, pair, new_bot):
        payload = {
            "name": self.attributes.get("prefix", "3CQSBOT", "dcabot")
            + "_"
            + self.attributes.get("subprefix", "SINGLE", "dcabot")
            + "_"
            + pair
            + "_"
            + self.attributes.get("suffix", "dcabot", "dcabot"),
            "account_id": self.account_data["id"],
            "pairs": self.tg_data["pair"],
            "max_active_deals": self.attributes.get(
                "mad", "", self.asyncState.dca_conf
            ),
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
            "cooldown": self.attributes.get("cooldown", 30, self.asyncState.dca_conf),
            "strategy_list": self.strategy(),
            "trailing_enabled": self.attributes.get(
                "trailing", False, self.asyncState.dca_conf
            ),
            "trailing_deviation": self.attributes.get(
                "trailing_deviation", 0.2, self.asyncState.dca_conf
            ),
            "min_volume_btc_24h": self.attributes.get(
                "btc_min_vol", 100, self.asyncState.dca_conf
            ),
            "disable_after_deals_count": self.attributes.get(
                "deals_count", 0, self.asyncState.dca_conf
            ),
        }

        if new_bot:
            if payload["disable_after_deals_count"] == 0:
                self.logging.debug(
                    "This is a new bot and count_active_deals set to 0, removing from payload"
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

    def update(self, bot):
        # Update settings on an existing bot

        error, data = self.p3cw.request(
            entity="bots",
            action="update",
            action_id=str(bot["id"]),
            additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
            payload=self.payload(bot["pairs"][0], new_bot=False),
        )

        if error:
            self.logging.error("function update: " + error["msg"])

    def enable(self, bot):

        self.logging.info(
            "Enabling single bot with pair "
            + bot["pairs"][0]
            + " and strategy: '"
            + str(self.strategy()[0]["strategy"])
            + "'. Applying following DCA settings:",  # DCA settings are reported through trigger function
            True,
        )

        self.update(bot)

        # Enables an existing bot
        error, data = self.p3cw.request(
            entity="bots",
            action="enable",
            action_id=str(bot["id"]),
            additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
        )

        if error:
            self.logging.error("function enable: " + error["msg"])
        else:
            self.asyncState.bot_active = True
            i = 0
            for bot in self.bot_data:
                if bot["name"] == data["name"]:
                    self.bot_data[i]["is_enabled"] = True
                    break
                i += 1

    def disable(self, bots, allbots=False):
        botname = (
            self.attributes.get("prefix", "3CQSBOT", "dcabot")
            + "_"
            + self.attributes.get("subprefix", "SINGLE", "dcabot")
            + "_"
            + self.attributes.get("market")
        )

        # Disable all bots
        error = {}

        if allbots:
            self.asyncState.bot_active = False
            self.logging.info(
                "Disabling all 3cqs single bots because btc-pulse is signaling downtrend",
                True,
            )

            for bot in bots:
                if botname in bot["name"] and bot["is_enabled"]:

                    self.logging.info(
                        "Disabling " + bot["name"],
                        True,
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
                        self.logging.error("function disable: " + error["msg"])
        else:
            # Disables an existing bot
            self.logging.info(
                "Disabling single bot " + bot["name"] + " because of a STOP signal",
                True,
            )

            error, data = self.p3cw.request(
                entity="bots",
                action="disable",
                action_id=str(bot["id"]),
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
            )

            if error:
                self.logging.error("function disable: " + error["msg"])

    def create(self):
        # Creates a single bot with start signal
        error, data = self.p3cw.request(
            entity="bots",
            action="create_bot",
            additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
            payload=self.payload(self.tg_data["pair"], new_bot=True),
        )

        self.logging.info(
            "Creating single bot with pair "
            + self.tg_data["pair"]
            + " and name "
            + data["name"]
            + ".",
            True,
        )

        if error:
            self.logging.error("function create: " + error["msg"])
        else:
            # Insert new bot at the begin of all bot data
            self.bot_data.insert(0, data)
            # Fix - 3commas needs some time for bot creation
            time.sleep(2)
            self.enable(data)

    def delete(self, bot):
        if bot["active_deals_count"] == 0:
            # Deletes a single bot with stop signal
            self.logging.info(
                "Delete single bot with pair " + self.tg_data["pair"], True
            )
            error, data = self.p3cw.request(
                entity="bots",
                action="delete",
                action_id=str(bot["id"]),
                additional_headers={"Forced-Mode": self.attributes.get("trade_mode")},
            )

            if error:
                self.logging.error("function delete: " + error["msg"])
        # Only perform the disable request if necessary
        elif bot["is_enabled"]:
            self.logging.info(
                "Disabling single bot with pair "
                + self.tg_data["pair"]
                + " unable to delete because of active deals or configuration.",
                True,
            )
            self.disable(bot, False)
        # No bot to delete or disable
        else:
            self.logging.info("Bot not enabled, nothing to do!", True)

    def trigger(self):
        # Triggers a single bot deal
        more_inform = self.attributes.get("extensive_notifications", False)
        new_bot = True
        pair = self.tg_data["pair"]
        enabled_bots_counted, bots_enabled = self.count_enabled_bots()
        active_deals_counted, bots_with_active_deals = self.count_active_deals()
        (
            active_deals_of_disabled_bots_counted,
            bots_disabled_with_active_deals,
        ) = self.count_active_deals_disabled_bots()
        maxdeals = self.attributes.get("single_count", "", self.asyncState.dca_conf)

        botname = (
            self.attributes.get("prefix", "3CQSBOT", "dcabot")
            + "_"
            + self.attributes.get("subprefix", "SINGLE", "dcabot")
            + "_"
            + pair
            + "_"
            + self.attributes.get("suffix", "dcabot", "dcabot")
        )

        if self.bot_data:

            for bot in self.bot_data:
                if botname == bot["name"]:
                    new_bot = False
                    break

            if new_bot:
                if self.tg_data["action"] == "START":
                    if enabled_bots_counted < self.attributes.get(
                        "single_count", "", self.asyncState.dca_conf
                    ):

                        if self.attributes.get("topcoin_filter", False):
                            pair = self.signal.topcoin(
                                pair,
                                self.attributes.get(
                                    "topcoin_limit", 3500, self.asyncState.dca_conf
                                ),
                                self.attributes.get(
                                    "topcoin_volume", 0, self.asyncState.dca_conf
                                ),
                                self.attributes.get("topcoin_exchange", "binance"),
                                self.attributes.get("market"),
                                self.asyncState.first_topcoin_call,
                            )
                            self.asyncState.first_topcoin_call = False
                        else:
                            self.logging.info(
                                "Topcoin filter disabled, not filtering pairs!"
                            )

                        if pair:
                            # avoid deals over limit
                            if active_deals_counted < self.attributes.get(
                                "single_count", "", self.asyncState.dca_conf
                            ):
                                if (
                                    enabled_bots_counted
                                    + active_deals_of_disabled_bots_counted
                                ) < self.attributes.get(
                                    "single_count", "", self.asyncState.dca_conf
                                ):
                                    self.create()  # create and enable bot
                                    self.report_funds_needed(maxdeals)
                                    self.report_deals()
                                else:
                                    self.logging.info(
                                        "Single bot not created. Blocking new deals, max deals of "
                                        + str(maxdeals)
                                        + " reached.",
                                        more_inform,
                                    )
                            else:
                                self.logging.info(
                                    "Single bot not created. Blocking new deals, max deals of "
                                    + str(maxdeals)
                                    + " reached.",
                                    more_inform,
                                )
                        else:
                            self.logging.info("Pair not added", more_inform)
                    else:
                        self.logging.info(
                            "Maximum bots/deals of "
                            + str(maxdeals)
                            + " reached. Single bot with "
                            + pair
                            + " not added.",
                            more_inform,
                        )

                elif self.tg_data["action"] == "STOP":
                    self.logging.info(
                        "Stop command on non-existing single bot for pair "
                        + pair
                        + " ignored.",
                        more_inform,
                    )
            else:  # already created bot
                self.logging.debug("Pair: " + pair)
                self.logging.debug("Bot-Name: " + bot["name"])

                if self.tg_data["action"] == "START":
                    if enabled_bots_counted < self.attributes.get(
                        "single_count", "", self.asyncState.dca_conf
                    ):
                        # check if bot reached already max active deals
                        if (bot["active_deals_count"] > 0) and (
                            bot["active_deals_count"] >= bot["max_active_deals"]
                        ):
                            self.logging.info(
                                bot["name"]
                                + " already reached maximum active deals "
                                + str(bot["active_deals_count"])
                                + "/"
                                + str(bot["max_active_deals"])
                                + ". No deal triggered",
                                more_inform,
                            )
                            return
                        # avoid deals over limit
                        if active_deals_counted < self.attributes.get(
                            "single_count", "", self.asyncState.dca_conf
                        ):
                            if (
                                enabled_bots_counted
                                + active_deals_of_disabled_bots_counted
                            ) < self.attributes.get(
                                "single_count", "", self.asyncState.dca_conf
                            ):
                                self.enable(bot)
                                self.report_funds_needed(maxdeals)
                                self.report_deals()
                            else:
                                self.logging.info(
                                    "Blocking new deals, because last enabled bot can potentially reach max deals of "
                                    + str(maxdeals)
                                    + ".",
                                    more_inform,
                                )
                        else:
                            self.logging.info(
                                "Blocking new deals, maximum active deals of "
                                + str(maxdeals)
                                + " reached.",
                                more_inform,
                            )

                    else:
                        self.logging.info(
                            "Maximum enabled bots of "
                            + str(maxdeals)
                            + " reached. No single bot with "
                            + pair
                            + " created/enabled.",
                            more_inform,
                        )
                elif self.tg_data["action"] == "STOP" and self.attributes.get(
                    "delete_single_bots", False
                ):
                    self.delete(bot)
                else:
                    self.disable(bot, False)

        else:
            self.logging.info("No single bots found - creating new ones", True)
            self.create()
            self.report_funds_needed(maxdeals)
            self.report_deals()
