import json
import logging
import os
import sys
import yaml
import shutil


class Config():

    def __init__(self):
        try:
            path = os.path.dirname(os.path.abspath(__file__))
            env_path = os.path.abspath(path + "/../etc/config.json")
            self.config = json.load(open(env_path))
        except OSError:
            logging.error(env_path + " not found")
            sys.exit(1)


class ModelConfig():

    def __init__(self, name):
        path = os.path.dirname(os.path.abspath(__file__))
        self.model_path = os.path.abspath(path + "/../models/" + name)
        self.config_path = os.path.abspath(path + "/../etc/" + name + ".yaml")

        # check if config exists
        if not os.path.exists(self.config_path):
            logging.error(self.config_path + " not found")
            sys.exit(1)

        # load yaml model configuration
        with open(self.config_path, "r") as stream:
            try:
                self.yaml = yaml.safe_load(stream)
            except yaml.YAMLError:
                logging.error("could not parse model config file")
                sys.exit(1)

        self.training_path = os.path.abspath(path + "/../data/training/" +
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
