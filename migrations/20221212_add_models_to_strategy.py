import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core

model_i = peewee.TextField(null=True)
model_p = peewee.TextField(null=True)

migrator = PostgresqlMigrator(core.db.connection)

migrate(
    migrator.add_column(core.db.Strategy._meta.table_name, "model_i", model_i),
    migrator.add_column(core.db.Strategy._meta.table_name, "model_p", model_p),
)
