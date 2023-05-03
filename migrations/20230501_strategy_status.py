import datetime

import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import sliver.core
import sliver.database as db
from sliver.strategies.status import StrategyStatus

migrator = PostgresqlMigrator(sliver.core.connection)


class Strategy(db.BaseModel):
    creator = peewee.ForeignKeyField(sliver.core.User, null=True)
    description = peewee.TextField()
    type = peewee.IntegerField(default=0)
    active = peewee.BooleanField(default=False)
    refreshing = peewee.BooleanField(default=False)
    deleted = peewee.BooleanField(default=False)
    market = peewee.ForeignKeyField(sliver.core.Market)
    timeframe = peewee.TextField(default="1d")
    next_refresh = peewee.DateTimeField(default=datetime.datetime.utcnow())
    buy_engine = peewee.ForeignKeyField(sliver.core.TradeEngine)
    sell_engine = peewee.ForeignKeyField(sliver.core.TradeEngine)
    stop_engine = peewee.ForeignKeyField(sliver.core.TradeEngine, null=True)
    side = peewee.TextField(default="long")
    status = peewee.IntegerField(default=StrategyStatus.INACTIVE)


with sliver.core.connection.atomic():
    migrate(
        migrator.add_column(
            Strategy._meta.table_name,
            "status",
            Strategy.status,
        )
    )

    for s in Strategy.select():
        s.status = StrategyStatus.IDLE

        if s.refreshing:
            s.status = StrategyStatus.REFRESHING

        if not s.active:
            s.status = StrategyStatus.INACTIVE

        if s.deleted:
            s.status = StrategyStatus.DELETED

        s.save()

    migrate(
        migrator.drop_column(Strategy._meta.table_name, "active"),
        migrator.drop_column(Strategy._meta.table_name, "refreshing"),
        migrator.drop_column(Strategy._meta.table_name, "deleted"),
    )
