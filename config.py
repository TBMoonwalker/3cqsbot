import configparser
import sys


class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.dataset = self.config.read("config.ini")

    def get(self, attribute, defaultvalue=""):
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
                    if raw_value.isdigit():
                        data = self.config[section].getint(attribute)
                    elif raw_value.lower() == "true" or raw_value.lower() == "false":
                        data = self.config[section].getboolean(attribute)
                    elif self.isfloat(raw_value):
                        data = self.config[section].getfloat(attribute)
                    else:
                        data = self.config[section][attribute]
                    break
                else:
                    data = defaultvalue
                    break

        if not data:
            data = defaultvalue

        return data

    def isfloat(self, element):
        try:
            float(element)
            return True
        except ValueError:
            return False
