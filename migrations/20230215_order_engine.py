import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core


migrator = PostgresqlMigrator(core.db.connection)

migrate(
    migrator.drop_column("strategy", "orders_interval"),
    migrator.drop_column("strategy", "num_orders"),
    migrator.drop_column("strategy", "bucket_interval"),
    migrator.drop_column("strategy", "min_buckets"),
    migrator.drop_column("strategy", "spread"),
    migrator.drop_column("strategy", "stop_gain"),
    migrator.drop_column("strategy", "stop_loss"),
    migrator.drop_column("strategy", "lm_ratio"),
    migrator.drop_column("strategy", "trailing_gain"),
    migrator.drop_column("strategy", "trailing_loss"),
)

core.db.TradeEngine.drop_table()
core.db.TradeEngine.create_table()
core.db.TradeEngine.create(
    description="default",
    deleted=False,
    refresh_interval=1,
    num_orders=1,
    bucket_interval=60,
    min_buckets=1,
    spread=1,
    stop_gain=5,
    trailing_gain=False,
    stop_loss=5,
    trailing_loss=False,
    lm_ratio=1,
)

engine = peewee.ForeignKeyField(core.db.TradeEngine,
                                field=core.db.TradeEngine.id,
                                default=1)
migrate(
    migrator.add_column("strategy", "buy_engine_id", engine),
    migrator.add_column("strategy", "sell_engine_id", engine),
    migrator.add_column("strategy", "stop_engine_id", engine),
)

migrate(
    migrator.add_column("position",
                        "stopped",
                        peewee.BooleanField(default=False)),
)
