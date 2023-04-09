import peewee

import sliver.database as db


class Price(db.BaseModel):
    market = peewee.DeferredForeignKey("Market", null=True)
    timeframe = peewee.TextField()
    time = peewee.DateTimeField()
    open = peewee.BigIntegerField()
    high = peewee.BigIntegerField()
    low = peewee.BigIntegerField()
    close = peewee.BigIntegerField()
    volume = peewee.BigIntegerField()

    class Meta:
        constraints = [peewee.SQL("UNIQUE (market_id, timeframe, time)")]

    @classmethod
    def get_by_market(cls, market, timeframe):
        return (
            cls.select()
            .where(cls.market == market)
            .where(cls.timeframe == timeframe)
            .order_by(cls.time)
        )

    @classmethod
    def get_by_strategy(cls, strategy):
        return (
            cls.select()
            .where(cls.market == strategy.market)
            .where(cls.timeframe == strategy.timeframe)
            .order_by(cls.time)
        )
