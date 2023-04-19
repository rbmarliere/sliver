import peewee
from playhouse.migrate import PostgresqlMigrator, migrate
import sliver.database as db
from sliver.position import Position


target_amount = peewee.BigIntegerField(null=True)

migrator = PostgresqlMigrator(db.connection)

migrate(
    migrator.drop_not_null(Position._meta.table_name, "target_cost"),
    migrator.add_column(Position._meta.table_name, "target_amount", target_amount),
)
