import peewee

import sliver.database as db
from sliver.exchange import Exchange
from sliver.exchange_asset import ExchangeAsset


class Market(db.BaseModel):
    symbol = peewee.TextField()
    exchange = peewee.ForeignKeyField(Exchange)
    base = peewee.ForeignKeyField(ExchangeAsset)
    quote = peewee.ForeignKeyField(ExchangeAsset)
    amount_precision = peewee.IntegerField(null=True)
    price_precision = peewee.IntegerField(null=True)
    amount_min = peewee.BigIntegerField(null=True)
    cost_min = peewee.BigIntegerField(null=True)
    price_min = peewee.BigIntegerField(null=True)

    class Meta:
        constraints = [peewee.SQL("UNIQUE (base_id, quote_id)")]

    def get_symbol(self):
        return self.base.asset.ticker + "/" + self.quote.asset.ticker

    def is_valid_amount(self, amount, price):
        try:
            assert amount >= self.amount_min
            assert price >= self.price_min
            assert self.base.format(amount) * price >= self.cost_min
        except AssertionError:
            return False

        return True
