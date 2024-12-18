from playhouse.migrate import PostgresqlMigrator, migrate

import sliver.core


migrator = PostgresqlMigrator(sliver.core.connection)

migrate(
    migrator.add_column(
        sliver.core.BaseStrategy._meta.table_name,
        "next_refresh_offset",
        sliver.core.BaseStrategy.next_refresh_offset,
    ),
)
