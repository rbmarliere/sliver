import json
import logging
import os
import sys

class Config():
    def __init__(self):
        try:
            path = os.path.dirname(os.path.abspath(__file__))
            self.config = json.load( open(path + "/../etc/.env") )
        except:
            logging.error(".env file not found! e.g. `ln -s .env.dev .env`")
            sys.exit(1)

