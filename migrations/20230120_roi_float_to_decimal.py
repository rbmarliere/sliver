import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core


migrator = PostgresqlMigrator(core.db.connection)

roi = peewee.DecimalField(default=0)

migrate(
    migrator.drop_column(core.db.Position._meta.table_name, "roi"),
    migrator.add_column(core.db.Position._meta.table_name,
                        "roi",
                        roi),
)

for pos in core.db.Position.select():
    if pos.status == "closed":
        pos.roi = core.utils.get_return(pos.entry_price, pos.exit_price)
        pos.save()
