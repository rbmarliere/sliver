import sliver.core
from sliver.strategies.factory import StrategyFactory
from sliver.exchanges.factory import ExchangeFactory

import pandas
import datetime

import datetime
import debugpy
import numpy
import pandas
import peewee


debugpy.listen(5678)


def st(id):
    return StrategyFactory.from_base(sliver.core.BaseStrategy.get(id=id))
