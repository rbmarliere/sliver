import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core

user = peewee.ForeignKeyField(core.db.User, field=core.db.User.id, default=1)
backtest_log = peewee.TextField(null=True)

migrator = PostgresqlMigrator(core.db.connection)

migrate(
    migrator.add_column(core.db.Strategy._meta.table_name, "user_id", user),
    migrator.add_column(core.db.Strategy._meta.table_name,
                        "backtest_log", backtest_log),
)
