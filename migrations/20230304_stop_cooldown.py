import datetime

import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core


next_refresh = peewee.DateTimeField(default=datetime.datetime.utcnow())

migrator = PostgresqlMigrator(core.db.connection)

stop_cooldown = peewee.IntegerField(default=1440)  # 1 day

migrate(
    migrator.add_column(
        core.db.TradeEngine._meta.table_name, "stop_cooldown", stop_cooldown
    ),
)
