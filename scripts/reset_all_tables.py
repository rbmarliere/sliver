#!/usr/bin/env python3

import hypnox


def reset_tables():
    hypnox.db.Price.drop_table()
    hypnox.db.Order.drop_table()
    hypnox.db.Position.drop_table()
    hypnox.db.UserStrategy.drop_table()
    hypnox.db.Strategy.drop_table()
    hypnox.db.Market.drop_table()
    hypnox.db.Credential.drop_table()
    hypnox.db.Balance.drop_table()
    hypnox.db.ExchangeAsset.drop_table()
    hypnox.db.Exchange.drop_table()
    hypnox.db.User.drop_table()
    hypnox.db.Asset.drop_table()

    hypnox.db.Asset.create_table()
    hypnox.db.User.create_table()
    hypnox.db.Exchange.create_table()
    hypnox.db.ExchangeAsset.create_table()
    hypnox.db.Balance.create_table()
    hypnox.db.Credential.create_table()
    hypnox.db.Market.create_table()
    hypnox.db.Strategy.create_table()
    hypnox.db.UserStrategy.create_table()
    hypnox.db.Position.create_table()
    hypnox.db.Order.create_table()
    hypnox.db.Price.create_table()


if __name__ == "__main__":
    reset_tables()
