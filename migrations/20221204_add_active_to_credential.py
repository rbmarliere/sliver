import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core

active = peewee.BooleanField(default=False)

migrator = PostgresqlMigrator(core.db.connection)

migrate(migrator.add_column(core.db.Credential._meta.table_name, "active", active))
