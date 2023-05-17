import datetime
import os

import debugpy
import numpy
import pandas
import peewee


import sliver.core
import sliver.database as db
from sliver.strategies.factory import StrategyFactory
from sliver.exchanges.factory import ExchangeFactory

db.init()

try:
    debugpy.listen(5678)
except:
    pass


def st(id):
    return StrategyFactory.from_base(sliver.core.BaseStrategy.get(id=id))


def ex(id):
    return ExchangeFactory.from_base(sliver.core.Exchange.get(id=id))


def exc(id):
    return ExchangeFactory.from_credential(sliver.core.Credential.get(id=id))
