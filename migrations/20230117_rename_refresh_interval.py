from playhouse.migrate import PostgresqlMigrator, migrate

import core


migrator = PostgresqlMigrator(core.db.connection)

migrate(
    migrator.rename_column(
        core.db.Strategy._meta.table_name, "refresh_interval", "orders_interval"
    )
)
