from playhouse.migrate import PostgresqlMigrator, migrate

import sliver.database as db
from sliver.balance import Balance

migrator = PostgresqlMigrator(db.connection)


migrate(
    migrator.drop_column(Balance._meta.table_name, "value_asset_id"),
    migrator.drop_column(Balance._meta.table_name, "free"),
    migrator.drop_column(Balance._meta.table_name, "used"),
    migrator.drop_column(Balance._meta.table_name, "free_value"),
    migrator.drop_column(Balance._meta.table_name, "used_value"),
    migrator.drop_column(Balance._meta.table_name, "total_value"),
)
