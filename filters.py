class Filters:
    def __init__(self, ws_data, attributes, account, logging):
        self.ws_data = ws_data
        self.attributes = attributes
        self.account = account
        self.logging = logging

    def signal(self):

        # Filter: Check if it is the right signal
        token_signal = False
        signals = [self.attributes.get("symrank_signal")]

        if not isinstance(self.attributes.get("symrank_signal"), int):
            signals = list(map(int, self.attributes.get("symrank_signal").split(",")))

        if (
            self.ws_data["signal_name_id"] in signals
            or self.attributes.get("symrank_signal") == 99
        ):
            token_signal = True
        else:
            self.logging.info("Signal ignored because signal isn't configured")

        return token_signal

    def whitelist(self):

        # Filter: Check if symbol is in whitelist
        token_whitelisted = False

        if self.attributes.get("token_whitelist", []):
            token_whitelisted = self.ws_data["symbol"] in self.attributes.get(
                "token_whitelist", []
            )
        else:
            # No Whitelist configured, so make it True
            token_whitelisted = True

        if not token_whitelisted:
            self.logging.info(
                "Signal ignored because symbol '"
                + str(self.ws_data["symbol"])
                + "' is not whitelisted"
            )

        return token_whitelisted

    def denylist(self):
        # Filter: Check if symbol is in denylist
        token_denylisted = False

        token_denylisted = self.ws_data["symbol"] in self.attributes.get(
            "token_denylist", []
        )

        if token_denylisted:
            self.logging.info(
                "Signal ignored because symbol '"
                + str(self.ws_data["symbol"])
                + "' is on denylist"
            )

        return token_denylisted

    def exchange(self, pairs):

        # Filter: Check if symbol is traded on configured exchange
        token_traded = False

        pair = self.attributes.get("market") + "_" + self.ws_data["symbol"]

        # Futures trading
        if self.attributes.get("trade_future", False):
            pair = (
                self.attributes.get("market")
                + "_"
                + self.ws_data["symbol"]
                + self.attributes.get("market")
            )

        self.logging.debug("Pair to trade: " + str(pair))
        self.logging.debug("Pairs from exchange: " + str(pairs))

        if pair in pairs:
            token_traded = True
        else:
            self.logging.info(
                "Signal ignored because symbol '"
                + str(self.ws_data["symbol"])
                + "' is not traded on '"
                + self.__get_exchange()
                + "' "
            )

        return token_traded

    def symrank(self):

        # Filter: Check if symrank is within configured range
        token_symrank = False

        if self.ws_data["sym_rank"] >= self.attributes.get(
            "symrank_limit_min", 1
        ) and self.ws_data["sym_rank"] <= self.attributes.get("symrank_limit_max", 100):
            token_symrank = True
        else:
            self.logging.info(
                "Signal ignored because configured symrank score filter for symbol '"
                + str(self.ws_data["symbol"])
                + "' did not met "
            )

        return token_symrank

    def price(self):

        # Filter: Check if volatility is within configured range
        token_price = False

        if self.ws_data["price_action_score"] >= self.attributes.get(
            "price_action_limit_min", 0.1
        ) and self.ws_data["price_action_score"] <= self.attributes.get(
            "price_action_limit_max", 100
        ):
            token_price = True
            self.logging.info(
                "Filter: Signal passed because '"
                + self.ws_data["symbol"]
                + "' has price score "
                + str(self.ws_data["price_action_score"])
                + " and is between the price score filter limit of "
                + str(self.attributes.get("price_action_limit_min", 0.1))
                + " - "
                + str(self.attributes.get("price_action_limit_max", 100))
            )
        else:
            self.logging.info(
                "Filter: Signal ignored because symbol '"
                + str(self.ws_data["symbol"])
                + "' has price score "
                + str(self.ws_data["price_action_score"])
                + " and is below or over the price score filter limit of "
                + str(self.attributes.get("price_action_limit_min", 0.1))
                + " - "
                + str(self.attributes.get("price_action_limit_max", 100))
            )

        return token_price

    def volatility(self):

        # Filter: Check if volatility is within configured range
        token_volatility = False

        if self.ws_data["volatility_score"] >= self.attributes.get(
            "volatility_limit_min", 0.1
        ) and self.ws_data["volatility_score"] <= self.attributes.get(
            "volatility_limit_max", 100
        ):
            token_volatility = True
            self.logging.info(
                "Filter: Signal passed because '"
                + self.ws_data["symbol"]
                + "' has volatility score "
                + str(self.ws_data["volatility_score"])
                + " and is between the volatility score filter limit of "
                + str(self.attributes.get("volatility_limit_min", 0.1))
                + " - "
                + str(self.attributes.get("volatility_limit_max", 100))
            )
        else:
            self.logging.info(
                "Filter: Signal ignored because symbol '"
                + str(self.ws_data["symbol"])
                + "' has volatility score "
                + str(self.ws_data["volatility_score"])
                + " and is below or over the volatility score filter limit of "
                + str(self.attributes.get("volatility_limit_min", 0.1))
                + " - "
                + str(self.attributes.get("volatility_limit_max", 100))
            )

        return token_volatility

    def topcoin_limit(self):

        # Filter: Check if marketcap is within configured range
        token_topcoin_limit = True

        if self.attributes.get("topcoin_limit", False):

            # Topcoin marketcap
            if self.ws_data["market_cap_rank"] <= self.attributes.get("topcoin_limit"):
                self.logging.info(
                    "Signal passed because "
                    + self.ws_data["symbol"]
                    + " is ranked #"
                    + str(self.ws_data["market_cap_rank"])
                    + " and is under the marketcap filter limit of #"
                    + str(self.attributes.get("topcoin_limit"))
                )
            else:
                token_topcoin_limit = False
                self.logging.info(
                    "Signal ignored because "
                    + self.ws_data["symbol"]
                    + " is ranked #"
                    + str(self.ws_data["market_cap_rank"])
                    + " and is over the marketcap filter limit of #"
                    + str(self.attributes.get("topcoin_limit"))
                )

        return token_topcoin_limit

    def topcoin_volume(self):

        # Filter: Check if marketcap and volume is within configured range
        token_topcoin_volume = True

        if self.attributes.get("topcoin_volume", False):

            # Topcoin volume
            # Check if pair is traded on exchange
            market = [
                value
                for key, value in self.ws_data["volume_24h"][
                    self.__get_exchange().upper()
                ].items()
                if self.attributes.get("market") in key
            ]

            if market:
                volume = self.ws_data["volume_24h"][self.__get_exchange()][
                    self.attributes.get("market")
                ]

                if self.__convert_volume(volume) >= self.__convert_volume(
                    self.attributes.get("topcoin_volume")
                ):
                    token_topcoin_volume = True
                    self.logging.info(
                        "Signal passed because symbol "
                        + self.ws_data["symbol"]
                        + " daily volume is "
                        + volume
                        + " USD"
                        + " and over the configured value of "
                        + self.attributes.get("topcoin_volume")
                        + " USD"
                    )
                else:
                    token_topcoin_volume = False
                    self.logging.info(
                        "Signal ignored because symbol "
                        + self.ws_data["symbol"]
                        + " daily volume is "
                        + volume
                        + " USD"
                        + " and under the configured value of "
                        + self.attributes.get("topcoin_volume")
                        + " USD"
                    )
            else:
                token_topcoin_volume = False
                self.logging.info(
                    "Signal ignored because symbol "
                    + self.ws_data["symbol"]
                    + " has no volume information in websocket signal"
                )

        return token_topcoin_volume

    def __convert_volume(self, volume):
        volume_length = int(len(volume)) - 1
        converted_volume = 0.0

        if volume[-1] == "k":
            converted_volume = float(volume[0:volume_length]) * 1000
        elif volume[-1] == "M":
            converted_volume = float(volume[0:volume_length]) * 1000000
        else:
            self.logging.info("Unkown divisor")

        return converted_volume

    def __get_exchange(self):

        exchange = self.account["market_code"]

        # Paper trading is statically mapped to Binance
        if self.account["exchange"] == "Paper trading account":
            exchange = "BINANCE"
        elif "binance_futures" in self.account["market_code"]:
            exchange = "BINANCE"

        return exchange
