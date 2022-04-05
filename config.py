import configparser
import sys


class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.dataset = self.config.read("config.ini")

    def get(self, attribute, defaultvalue=""):
        data = ""

        if len(self.dataset) != 1:
            sys.tracebacklimit = 0
            sys.exit(
                "Cannot read config.ini! - Please make sure it exists in the folder where 3cqsbot.py is executed."
            )

        sections = self.config.sections()

        for section in sections:
            if self.config.has_option(section, attribute):
                raw_value = self.config[section].get(attribute)

                if raw_value:
                    data = self.check_type(raw_value)
                    break

        if not data and str(defaultvalue):
            data = defaultvalue
        elif not data and not str(defaultvalue):
            sys.tracebacklimit = 0
            sys.exit(
                "Attribute "
                + attribute
                + " is not set, but mandatory! Please check the readme for configuration."
            )

        return data

    def isfloat(self, element):
        try:
            float(element)
            return True
        except ValueError:
            return False

    def check_type(self, raw_value):
        data = ""

        if raw_value.isdigit():
            data = int(raw_value)
        elif raw_value.lower() == "true":
            data = True
        elif raw_value.lower() == "false":
            data = False
        elif self.isfloat(raw_value):
            data = float(raw_value)
        else:
            data = str(raw_value)

        return data
