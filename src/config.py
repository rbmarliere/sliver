import json
import logging
import sys

class Config():
    def __init__(self):
        try:
            self.config = json.load( open(".env") )
        except:
            logging.error(".env file not found! e.g. `ln -s .env.dev .env`")
            sys.exit(1)

