#!/usr/bin/env python3

import sys

sys.path.insert(0, "../..")

import src as hypnox  # noqa: E402

hypnox.db.Order.drop_table()
hypnox.db.Position.drop_table()
hypnox.db.Price.drop_table()
hypnox.db.Market.drop_table()

hypnox.db.Market.create_table()
hypnox.db.Position.create_table()
hypnox.db.Order.create_table()
hypnox.db.Price.create_table()
