import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core

timeframes = peewee.TextField(null=True)

migrator = PostgresqlMigrator(core.db.connection)

migrate(
    migrator.add_column(core.db.Exchange._meta.table_name,
                        "timeframes",
                        timeframes)
)
