import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core
import strategies


migrator = PostgresqlMigrator(core.db.connection)

sell_w_signal = peewee.DecimalField(default=0)

migrate(
    migrator.rename_column(strategies.mixer.MixerIndicator._meta.table_name,
                           "weighted_signal",
                           "buy_w_signal"),
    migrator.add_column(strategies.mixer.MixerIndicator._meta.table_name,
                        "sell_w_signal",
                        sell_w_signal)
)

strategies.mixer.MixerIndicator.delete().execute()
