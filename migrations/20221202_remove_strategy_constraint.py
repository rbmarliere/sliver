from playhouse.migrate import PostgresqlMigrator, migrate

import core

migrator = PostgresqlMigrator(core.db.connection)

migrate(
    migrator.drop_constraint("strategy",
                             "strategy_market_id_active_timeframe_key")
)
