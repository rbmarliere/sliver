from playhouse.migrate import PostgresqlMigrator, migrate

import sliver.core
import sliver.database as db

db.init()


migrator = PostgresqlMigrator(db.connection)

migrate(
    migrator.add_column(
        sliver.core.User._meta.table_name,
        "deleted",
        sliver.core.User.deleted,
    ),
)
