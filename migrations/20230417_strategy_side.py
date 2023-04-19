import peewee
from playhouse.migrate import PostgresqlMigrator, migrate
import sliver.database as db
from sliver.strategy import BaseStrategy


side = peewee.TextField(default="long")

migrator = PostgresqlMigrator(db.connection)

migrate(
    migrator.add_column(BaseStrategy._meta.table_name, "side", side)
)
