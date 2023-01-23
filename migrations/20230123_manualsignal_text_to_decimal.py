import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core


migrator = PostgresqlMigrator(core.db.connection)

signal = peewee.DecimalField(default=0)

migrate(
    migrator.drop_column(
        core.strategies.ManualStrategy._meta.table_name, "signal"),
    migrator.add_column(
        core.strategies.ManualStrategy._meta.table_name, "signal", signal),
)
