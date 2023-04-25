from playhouse.migrate import PostgresqlMigrator, migrate

import sliver.database as db
from sliver.position import Position

migrator = PostgresqlMigrator(db.connection)

with db.connection.atomic():
    for position in Position.select():
        if position.stopped:
            position.status = "stopped"
            position.save()

    migrate(
        migrator.drop_column(Position._meta.table_name, "stopped"),
    )
