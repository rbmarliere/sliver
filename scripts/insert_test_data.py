#!/usr/bin/env python3

from fetch_markets import fetch_markets

import core

if __name__ == "__main__":
    with core.db.connection.atomic():
        binance = core.db.Exchange(name="binance")
        binance.save()

        k = "BGmuGRnxKGpAQQUF6U7NLejksGyoIf2szKPxklaHXOviJYfAOHs5RKvqmhVFA2wp"
        s = "eSlnlGGWICv2cfMaHGkFHcCnPT2LLJ2yY7kGTsWMbGZRgl1w2aXOmxVvNyWxH9Vv"
        user1 = core.db.User(email="user1@mail.com",
                             password="passwd",
                             name="user1")
        user1.save()
        cred1 = core.db.Credential(user=user1,
                                   exchange=binance,
                                   api_key=k,
                                   api_secret=s)
        cred1.save()

        k = "3qTe6Q63DGD0zhcm6yHd3UNfBWs6udA0hSZngEi3kBHJgINZ5kMyoZNpfUqocz0h"
        s = "6AcrYTsNUmp5znbwYBP9nz5ppBAECPmGhzyZ3j0ePQ4KA9z0thPNDL49fVqPj0mE"
        user2 = core.db.User(email="user2@mail.com",
                             password="passwd",
                             name="user2")
        user2.save()
        cred2 = core.db.Credential(user=user2,
                                   exchange=binance,
                                   api_key=k,
                                   api_secret=s)
        cred2.save()

        core.exchange.set_api(cred1)
        fetch_markets(binance)

        btc = core.db.ExchangeAsset.get(exchange=binance,
                                        asset=core.db.Asset.get(ticker="BTC"))
        eth = core.db.ExchangeAsset.get(exchange=binance,
                                        asset=core.db.Asset.get(ticker="ETH"))
        usdt = core.db.ExchangeAsset.get(
            exchange=binance, asset=core.db.Asset.get(ticker="USDT"))

        btcusdt = core.db.Market.get(base=btc, quote=usdt)
        ethusdt = core.db.Market.get(base=eth, quote=usdt)

        strat1 = core.db.Strategy(market=btcusdt,
                                  active=True,
                                  description="random",
                                  timeframe="1h",
                                  refresh_interval=2,
                                  i_threshold=0.001,
                                  p_threshold=0,
                                  tweet_filter="btc|bitcoin",
                                  num_orders=6,
                                  bucket_interval=5,
                                  spread=0.01,
                                  min_roi=5,
                                  stop_loss=3)
        strat1.save()

        strat2 = core.db.Strategy(market=ethusdt,
                                  active=True,
                                  description="random",
                                  timeframe="4h",
                                  refresh_interval=5,
                                  i_threshold=0.0001,
                                  p_threshold=0,
                                  tweet_filter="eth|ethereum",
                                  num_orders=12,
                                  bucket_interval=10,
                                  spread=1,
                                  min_roi=3,
                                  stop_loss=1.5)
        strat2.save()

        core.db.UserStrategy(user=user1, strategy=strat1, active=True).save()
        core.db.UserStrategy(user=user1, strategy=strat2, active=True).save()
        core.db.UserStrategy(user=user2, strategy=strat1, active=True).save()
