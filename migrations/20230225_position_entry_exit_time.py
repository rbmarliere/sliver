import datetime

import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core


next_refresh = peewee.DateTimeField(default=datetime.datetime.utcnow())

migrator = PostgresqlMigrator(core.db.connection)

col = peewee.DateTimeField(null=True)

migrate(
    migrator.add_column(core.db.Position._meta.table_name, "entry_time", col),
    migrator.add_column(core.db.Position._meta.table_name, "exit_time", col),
)


for p in core.db.Position.select():
    if p.status != "closed":
        continue

    orders = [o for o in p.get_orders()]
    p.entry_time = orders[-1].time
    p.exit_time = orders[0].time
    p.save()
