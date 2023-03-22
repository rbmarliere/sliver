import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core


migrator = PostgresqlMigrator(core.db.connection)

col = peewee.DecimalField(default=0)

migrate(
    migrator.rename_column("hypnoxstrategy", "i_threshold", "i_h_threshold"),
    migrator.rename_column("hypnoxstrategy", "p_threshold", "p_h_threshold"),
    migrator.add_column("hypnoxstrategy", "i_l_threshold", col),
    migrator.add_column("hypnoxstrategy", "p_l_threshold", col),
)
