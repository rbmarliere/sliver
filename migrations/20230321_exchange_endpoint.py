import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core

col = peewee.TextField(null=True)

migrator = PostgresqlMigrator(core.db.connection)

migrate(
    migrator.add_column(core.db.Exchange._meta.table_name, "api_endpoint", col),
    migrator.add_column(core.db.Exchange._meta.table_name, "api_sandbox_endpoint", col),
)
