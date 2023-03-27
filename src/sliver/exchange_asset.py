from decimal import Decimal as D

import peewee

import sliver.database as db
from sliver.asset import Asset
from sliver.exchange import Exchange


class ExchangeAsset(db.BaseModel):
    exchange = peewee.ForeignKeyField(Exchange)
    asset = peewee.ForeignKeyField(Asset)
    precision = peewee.IntegerField(default=1)

    def div(self, num, den, prec=None):
        if prec is None:
            prec = self.precision

        div = int(D(str(num)) / D(str(den)) * 10**prec)

        if prec == self.precision:
            return div
        else:
            return self.transform(div, prec=(self.precision - prec))

    def format(self, value, prec=None):
        if not value:
            return 0
        if prec is None:
            prec = self.precision
        precision = D("10") ** D(str(-1 * self.precision))
        value = D(str(value)) * precision
        if prec == self.precision:
            return value.quantize(precision)
        else:
            trunc_precision = D("10") ** D(str(-1 * prec))
            return value.quantize(trunc_precision)

    def transform(self, value, prec=None):
        if not value:
            return 0
        if prec is None:
            prec = self.precision
        precision = D("10") ** D(str(prec))
        return int(D(str(value)) * precision)

    def print(self, value):
        value = self.format(value)
        return "{n:.{p}f} {t}".format(n=value, p=self.precision, t=self.asset.ticker)
