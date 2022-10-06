#!/usr/bin/env python3

import hypnox


def fetch_markets(cred: hypnox.db.Credential):
    table_exists = hypnox.db.Market.table_exists()
    if not table_exists:
        hypnox.db.Market.create_table()

    hypnox.watchdog.script_log.info(
        "fetching all markets from exchange api...")

    hypnox.exchange.set_api(cred)
    ex_markets = hypnox.exchange.api.fetch_markets()

    for ex_market in ex_markets:
        market = hypnox.db.Market(
            exchange=cred.exchange,
            symbol=ex_market["symbol"],
            base=ex_market["base"],
            quote=ex_market["quote"],
            amount_precision=ex_market["precision"]["amount"],
            base_precision=ex_market["precision"]["base"],
            price_precision=ex_market["precision"]["price"],
            quote_precision=ex_market["precision"]["quote"])

        amount_min = ex_market["limits"]["amount"]["min"]
        cost_min = ex_market["limits"]["cost"]["min"]
        price_min = ex_market["limits"]["price"]["min"]

        market.amount_min = market.btransform(amount_min)
        market.cost_min = market.qtransform(cost_min)
        market.price_min = market.qtransform(price_min)

        market.save(force_insert=table_exists)

        hypnox.watchdog.script_log.info("saved market " + market.symbol)


if __name__ == "__main__":
    with hypnox.db.connection.atomic():
        binance = hypnox.db.Exchange(name="binance")
        binance.save()

        k = "BGmuGRnxKGpAQQUF6U7NLejksGyoIf2szKPxklaHXOviJYfAOHs5RKvqmhVFA2wp"
        s = "eSlnlGGWICv2cfMaHGkFHcCnPT2LLJ2yY7kGTsWMbGZRgl1w2aXOmxVvNyWxH9Vv"
        user1 = hypnox.db.User(name="user1")
        user1.save()
        cred1 = hypnox.db.Credential(user=user1,
                                     exchange=binance,
                                     api_key=k,
                                     api_secret=s)
        cred1.save()

        k = "3qTe6Q63DGD0zhcm6yHd3UNfBWs6udA0hSZngEi3kBHJgINZ5kMyoZNpfUqocz0h"
        s = "6AcrYTsNUmp5znbwYBP9nz5ppBAECPmGhzyZ3j0ePQ4KA9z0thPNDL49fVqPj0mE"
        user2 = hypnox.db.User(name="user2")
        user2.save()
        cred2 = hypnox.db.Credential(user=user2,
                                     exchange=binance,
                                     api_key=k,
                                     api_secret=s)
        cred2.save()

        fetch_markets(cred1)

        btcusdt = binance.get_market_by_symbol("BTC/USDT")
        assert btcusdt
        ethusdt = binance.get_market_by_symbol("ETH/USDT")
        assert ethusdt

        strat1 = hypnox.db.Strategy(market=btcusdt,
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

        strat2 = hypnox.db.Strategy(market=ethusdt,
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

        hypnox.db.UserStrategy(user=user1, strategy=strat1, active=True).save()
        hypnox.db.UserStrategy(user=user1, strategy=strat2, active=True).save()
        hypnox.db.UserStrategy(user=user2, strategy=strat1, active=True).save()
