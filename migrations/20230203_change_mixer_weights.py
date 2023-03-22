import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core
import strategies


migrator = PostgresqlMigrator(core.db.connection)

weight = peewee.DecimalField(default=1)

migrate(
    migrator.rename_column(
        strategies.mixer.MixedStrategies._meta.table_name, "weight", "buy_weight"
    ),
    migrator.add_column(
        strategies.mixer.MixedStrategies._meta.table_name, "sell_weight", weight
    ),
)
