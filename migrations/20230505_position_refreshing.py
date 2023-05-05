from playhouse.migrate import PostgresqlMigrator, migrate

import sliver.core


migrator = PostgresqlMigrator(sliver.core.connection)

migrate(
    migrator.add_column(
        sliver.core.Position._meta.table_name,
        "refreshing",
        sliver.core.Position.refreshing,
    ),
)
