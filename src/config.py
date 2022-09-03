import json
import logging
import os
import shutil
import sys

import yaml

try:
    config_path = os.path.abspath(
        os.path.dirname(os.path.abspath(__file__)) + "/../etc/config.json")
    config = json.load(open(config_path))
except OSError:
    logging.error(config_path + " not found")
    sys.exit(1)


class StrategyConfig():

    def __init__(self, name):
        try:
            strategy_path = os.path.abspath(
                os.path.dirname(os.path.abspath(__file__)) +
                "/../etc/strategies/" + name + ".json")
            self.config = json.load(open(strategy_path))
        except OSError:
            logging.error(strategy_path + " not found")
            sys.exit(1)


class ModelConfig():

    def __init__(self, name):
        path = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.abspath(path + "/../etc/" + name + ".yaml")

        # load yaml model configuration
        try:
            with open(self.config_path, "r") as stream:
                self.yaml = yaml.safe_load(stream)
        except OSError:
            logging.error(self.config_path + " not found")
            sys.exit(1)
        except yaml.YAMLError:
            logging.error("could not parse model config file")
            sys.exit(1)

        self.model_path = os.path.abspath(path + "/../lib/" +
                                          self.yaml["name"])
        self.training_path = os.path.abspath(path + "/../lib/training/" +
                                             self.yaml["training_file"])

    def check_model(self):
        # check if model exists
        if not os.path.exists(self.model_path):
            logging.error(self.model_path + " not found")
            sys.exit(1)

    def check_overwrite(self):
        # check if model exists and asks for confirmation
        if os.path.exists(self.model_path):
            logging.warning(self.model_path +
                            " already exists, overwrite? [y|N]")
            if input() != "y":
                sys.exit(1)
            # remove old model upon confirmation
            shutil.rmtree(self.model_path)

    def check_training(self):
        # check if training data file exists
        if not os.path.exists(self.training_path):
            logging.error(self.training_path + " not found")
            sys.exit(1)
