import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core

col = peewee.IntegerField(default=0)

migrator = PostgresqlMigrator(core.db.connection)

migrate(
    migrator.add_column(core.db.Exchange._meta.table_name,
                        "type",
                        col)
)
