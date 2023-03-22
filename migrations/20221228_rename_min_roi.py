from playhouse.migrate import PostgresqlMigrator, migrate

import core


migrator = PostgresqlMigrator(core.db.connection)

migrate(
    migrator.rename_column(core.db.Strategy._meta.table_name, "min_roi", "stop_gain")
)
