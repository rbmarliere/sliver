from playhouse.migrate import PostgresqlMigrator, migrate

import sliver.core
from sliver.database import connection, db_init

db_init()

migrator = PostgresqlMigrator(connection)

migrate(
    migrator.add_column(
        sliver.core.BaseStrategy._meta.table_name,
        "reset",
        sliver.core.BaseStrategy.reset,
    ),
)
