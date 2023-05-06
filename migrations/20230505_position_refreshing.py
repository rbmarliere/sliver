from playhouse.migrate import PostgresqlMigrator, migrate

import sliver.core
from sliver.database import connection, db_init

db_init()


migrator = PostgresqlMigrator(connection)

migrate(
    migrator.add_column(
        sliver.core.Position._meta.table_name,
        "refreshing",
        sliver.core.Position.refreshing,
    ),
)
