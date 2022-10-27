#!/usr/bin/env python3

import core


def reset_tables():
    core.db.Price.drop_table()
    core.db.Order.drop_table()
    core.db.Position.drop_table()
    core.db.UserStrategy.drop_table()
    core.db.Strategy.drop_table()
    core.db.Market.drop_table()
    core.db.Credential.drop_table()
    core.db.Balance.drop_table()
    core.db.ExchangeAsset.drop_table()
    core.db.Exchange.drop_table()
    core.db.User.drop_table()
    core.db.Asset.drop_table()

    core.db.Asset.create_table()
    core.db.User.create_table()
    core.db.Exchange.create_table()
    core.db.ExchangeAsset.create_table()
    core.db.Balance.create_table()
    core.db.Credential.create_table()
    core.db.Market.create_table()
    core.db.Strategy.create_table()
    core.db.UserStrategy.create_table()
    core.db.Position.create_table()
    core.db.Order.create_table()
    core.db.Price.create_table()


if __name__ == "__main__":
    reset_tables()
