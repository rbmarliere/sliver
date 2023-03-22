import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core


migrator = PostgresqlMigrator(core.db.connection)

# set to not_null in db after migration
symbol = peewee.TextField(null=True)

migrate(
    migrator.add_column(core.db.Market._meta.table_name, "symbol", symbol),
)

for m in core.db.Market.select():
    m.symbol = m.get_symbol()
    print("{i} - {s}".format(i=m.id, s=m.symbol))
    m.save()
