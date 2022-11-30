from playhouse.migrate import PostgresqlMigrator, migrate

import core

migrator = PostgresqlMigrator(core.db.connection)

migrate(
    migrator.drop_column("exchange", "rounding_mode")
)
