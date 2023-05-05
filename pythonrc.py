import datetime
import os

import debugpy
import numpy
import pandas
import peewee


import sliver.core
from sliver.database import db_init
from sliver.strategies.factory import StrategyFactory
from sliver.exchanges.factory import ExchangeFactory

db_init()

try:
    debugpy.listen(5678)
except:
    pass


def st(id):
    return StrategyFactory.from_base(sliver.core.BaseStrategy.get(id=id))
