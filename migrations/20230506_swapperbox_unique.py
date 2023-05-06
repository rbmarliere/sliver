from playhouse.migrate import PostgresqlMigrator, migrate

import sliver.core
from sliver.database import connection, db_init
from sliver.strategies.swapperbox import SwapperBoxMessage

db_init()


migrator = PostgresqlMigrator(connection)

migrate(
    migrator.add_unique(
        SwapperBoxMessage._meta.table_name,
        "telegram_message_id",
    ),
)
