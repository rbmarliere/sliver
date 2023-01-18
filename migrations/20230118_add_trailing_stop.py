import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core

migrator = PostgresqlMigrator(core.db.connection)

roi = peewee.FloatField(default=0)
last_price = peewee.BigIntegerField(default=0)
trailing_gain = peewee.BooleanField(default=False)
trailing_loss = peewee.BooleanField(default=False)

migrate(
    migrator.add_column(core.db.Position._meta.table_name,
                        "roi",
                        roi),
    migrator.add_column(core.db.Position._meta.table_name,
                        "last_price",
                        last_price),
    migrator.add_column(core.db.Strategy._meta.table_name,
                        "trailing_gain",
                        trailing_gain),
    migrator.add_column(core.db.Strategy._meta.table_name,
                        "trailing_loss",
                        trailing_loss),
)

for pos in core.db.Position.select():
    if pos.status == "closed":
        pos.roi = core.utils.get_roi(pos.entry_price, pos.exit_price)
        pos.save()
