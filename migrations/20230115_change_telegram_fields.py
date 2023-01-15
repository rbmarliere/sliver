import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core


active = peewee.BooleanField(default=False)

migrator = PostgresqlMigrator(core.db.connection)

telegram_username = peewee.TextField(null=True)
telegram_chat_id = peewee.TextField(null=True)

migrate(
    migrator.drop_column(core.db.User._meta.table_name, "telegram"),
    migrator.add_column(core.db.User._meta.table_name,
                        "telegram_username",
                        telegram_username),
    migrator.add_column(core.db.User._meta.table_name,
                        "telegram_chat_id",
                        telegram_chat_id)
)
