import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core


migrator = PostgresqlMigrator(core.db.connection)

# set to not_null in db after migration
exchange = peewee.ForeignKeyField(
    core.db.Exchange, field=core.db.Exchange.id, null=True
)

migrate(
    migrator.add_column(core.db.Market._meta.table_name, "exchange_id", exchange),
)

for m in core.db.Market.select():
    m.exchange = m.base.exchange
    m.save()
