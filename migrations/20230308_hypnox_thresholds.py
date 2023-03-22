import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core
import strategies


migrator = PostgresqlMigrator(core.db.connection)

mode = peewee.TextField(default="buy")
operator = peewee.TextField(default="gt")

with core.db.connection.atomic():
    migrate(
        migrator.drop_column(
            strategies.HypnoxStrategy._meta.table_name, "p_h_threshold"
        ),
        migrator.drop_column(
            strategies.HypnoxStrategy._meta.table_name, "p_l_threshold"
        ),
        migrator.drop_column(
            strategies.HypnoxStrategy._meta.table_name, "i_l_threshold"
        ),
        migrator.drop_column(strategies.HypnoxStrategy._meta.table_name, "model_p"),
        migrator.rename_column(
            strategies.HypnoxStrategy._meta.table_name, "tweet_filter", "filter"
        ),
        migrator.rename_column(
            strategies.HypnoxStrategy._meta.table_name, "i_h_threshold", "threshold"
        ),
        migrator.rename_column(
            strategies.HypnoxStrategy._meta.table_name, "model_i", "model"
        ),
        migrator.add_column(strategies.HypnoxStrategy._meta.table_name, "mode", mode),
        migrator.add_column(
            strategies.HypnoxStrategy._meta.table_name, "operator", operator
        ),
        # migrator.drop_column(strategies.hypnox.HypnoxIndicator._meta.table_name,
        #                      "p_score"),
        # migrator.drop_column(strategies.hypnox.HypnoxIndicator._meta.table_name,
        #                      "p_mean"),
        # migrator.drop_column(strategies.hypnox.HypnoxIndicator._meta.table_name,
        #                      "p_variance"),
        # migrator.rename_column(strategies.hypnox.HypnoxIndicator._meta.table_name,
        #                        "i_score",
        #                        "z_score"),
        # migrator.rename_column(strategies.hypnox.HypnoxIndicator._meta.table_name,
        #                        "i_mean",
        #                        "mean"),
        # migrator.rename_column(strategies.hypnox.HypnoxIndicator._meta.table_name,
        #                        "i_variance",
        #                        "variance"),
    )

    q = core.db.Strategy.select().where(
        core.db.Strategy.type == core.strategies.Types.HYPNOX
    )

    for st in q:
        core.db.Indicator.delete().where(core.db.Indicator.strategy == st).execute()

    strategies.hypnox.HypnoxIndicator.drop_table()
    strategies.hypnox.HypnoxIndicator.create_table()
