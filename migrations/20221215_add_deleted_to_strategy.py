import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core

deleted = peewee.BooleanField(default=False)

migrator = PostgresqlMigrator(core.db.connection)

migrate(
    migrator.add_column(core.db.Strategy._meta.table_name, "deleted", deleted),
)
