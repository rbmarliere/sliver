import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core

lm_ratio = peewee.DecimalField(default=0)

migrator = PostgresqlMigrator(core.db.connection)

migrate(
    migrator.add_column(core.db.Strategy._meta.table_name,
                        "lm_ratio",
                        lm_ratio)
)
