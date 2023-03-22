from playhouse.migrate import PostgresqlMigrator, migrate

import core
import peewee

migrator = PostgresqlMigrator(core.db.connection)


migrate(
    migrator.rename_column(
        core.db.Position._meta.table_name, "last_price", "last_high"
    ),
    migrator.add_column(
        core.db.Position._meta.table_name, "last_low", peewee.BigIntegerField(default=0)
    ),
)
