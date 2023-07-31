from playhouse.migrate import PostgresqlMigrator, migrate

import sliver.strategies.hypnox as hypnox
import sliver.database as db

db.init()

migrator = PostgresqlMigrator(db.connection)

migrate(
    migrator.add_column(
        hypnox.HypnoxTweet._meta.table_name,
        "user_id",
        hypnox.HypnoxTweet.user,
    ),
)
