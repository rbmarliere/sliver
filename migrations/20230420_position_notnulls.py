import peewee
from playhouse.migrate import PostgresqlMigrator, migrate
import sliver.database as db
from sliver.position import Position


f = peewee.BigIntegerField(default=0)

migrator = PostgresqlMigrator(db.connection)

with db.connection.atomic():
    for position in Position.select():
        if position.target_cost is None:
            position.target_cost = 0
            position.save()

        if position.target_amount is None:
            position.target_amount = 0
            position.save()

    migrate(
        migrator.add_not_null(Position._meta.table_name, "target_cost"),
        migrator.add_not_null(Position._meta.table_name, "target_amount"),
    )
