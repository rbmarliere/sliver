from playhouse.migrate import PostgresqlMigrator, migrate

import sliver.core


migrator = PostgresqlMigrator(sliver.core.connection)

migrate(
    migrator.add_column(
        sliver.core.TradeEngine._meta.table_name,
        "creator_id",
        sliver.core.TradeEngine.creator,
    ),
)
