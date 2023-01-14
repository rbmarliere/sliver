import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core


min_buckets = peewee.IntegerField(default=1)

migrator = PostgresqlMigrator(core.db.connection)

migrate(
    migrator.add_column(core.db.Strategy._meta.table_name,
                        "min_buckets",
                        min_buckets)
)
