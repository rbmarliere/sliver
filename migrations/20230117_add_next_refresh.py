import peewee
from playhouse.migrate import PostgresqlMigrator, migrate
import datetime

import core

next_refresh = peewee.DateTimeField(default=datetime.datetime.utcnow())

migrator = PostgresqlMigrator(core.db.connection)

migrate(
    migrator.add_column(core.db.Position._meta.table_name,
                        "next_refresh",
                        next_refresh)
)
