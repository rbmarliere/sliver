import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import sliver.database as db
from sliver.credential import Credential

passwd = peewee.TextField(null=True)

migrator = PostgresqlMigrator(db.connection)

migrate(
    # migrator.drop_not_null(Credential._meta.table_name, "api_key"),
    # migrator.drop_not_null(Credential._meta.table_name, "api_secret"),
    migrator.add_column(Credential._meta.table_name, "api_password", passwd),
)
