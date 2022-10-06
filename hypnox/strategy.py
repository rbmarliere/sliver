import pandas

import hypnox


def get_rsignal():
    import random
    i = random.randint(0, 100)
    if i > 70:
        hypnox.watchdog.log.warning("received buy signal")
        return "buy"
    elif i < 30:
        hypnox.watchdog.log.warning("received sell signal")
        return "sell"
    else:
        hypnox.watchdog.log.warning("received neutral signal")
        return "neutral"


def get_indicators(strategy):
    # TODO timedelta arg?
    # TODO sell_half signal?
    # TODO weighthing, e.g.
    # 20% * swapperbox + 80% * hypnox_AI + 10% *
    # traditional_TA + 10% * chain_data
    # TODO trend-based EMA cross as weight for the signal?
    # short_avg = ta.EMA(prices, timeperiod=2)
    # long_avg = ta.EMA(prices, timeperiod=17)
    # prices["trend"] = False
    # prices.loc[(short_avg > long_avg), "trend"] = True
    # TODO z-score? (x-avg)/stddev
    # TODO lunar indicator?

    # grab tweets based on strategy filter
    filter = hypnox.db.Tweet.text.iregexp(
        strategy.tweet_filter.encode("unicode_escape"))

    tweets = hypnox.db.Tweet.select().where(filter)
    tweets = pandas.DataFrame(tweets.dicts())

    # check if there are tweets with given params
    if tweets.empty:
        hypnox.watchdog.log.error("no tweets found")
        # TODO
        # for models " + strategy["I_MODEL"] + " and " + strategy["P_MODEL"])
        raise Exception

    # sort by date
    tweets.sort_values("time", inplace=True)
    # aggregate tweets by timeframe
    tweets["floor"] = tweets.time.dt.floor(strategy.timeframe)
    # set floor as index
    tweets.set_index("floor", inplace=True)
    # compute indicators from groups
    tweets["i_median"] = tweets.groupby("floor")["intensity"].median()
    tweets["p_score"] = tweets.groupby("floor")["polarity"].sum()
    # remove duplicated indexes
    tweets = tweets.loc[~tweets.index.duplicated(keep='first')]

    # grab price data
    prices = hypnox.db.Price.select().where(
        (hypnox.db.Price.market == strategy.market)
        & (hypnox.db.Price.timeframe == strategy.timeframe))
    prices = pandas.DataFrame(prices.dicts())

    # check if there is data for given params
    if prices.empty:
        hypnox.watchdog.log.error("no price data found for symbol " +
                                  strategy.market.symbol + " for timeframe " +
                                  strategy.timeframe)
        raise Exception

    # sort by strategy timeframe and set index
    prices.sort_values("time", inplace=True)
    prices.set_index("time", inplace=True)

    # concatenate both dataframes
    indicators = pandas.concat([tweets, prices], join='inner', axis=1)
    # get rid of unused columns
    indicators = indicators[[
        "i_median", "p_score", "open", "high", "low", "close", "volume"
    ]]

    # compute signal
    indicators["signal"] = "neutral"
    buy_rule = (indicators["i_median"] > strategy.i_threshold)  # &
    #(indicators["p_score"] > strategy["POLARITY_THRESHOLD"]))
    indicators.loc[buy_rule, "signal"] = "buy"
    sell_rule = (indicators["i_median"] < strategy.i_threshold)  #&
    #(indicators["p_score"] < strategy["POLARITY_THRESHOLD"]))
    indicators.loc[sell_rule, "signal"] = "sell"

    indicators.to_csv("log/backtest.tsv", sep="\t")

    return indicators


def backtest(args):
    # TODO charts

    # TODO param. strategy
    strategy = hypnox.db.Strategy.get()

    # check if symbol is supported by hypnox
    market = hypnox.db.get_market(hypnox.exchange.api.id, strategy["SYMBOL"])
    if market is None:
        hypnox.watchdog.log.error("can't find market " + strategy["SYMBOL"])
        return 1

    indicators = get_indicators(market, strategy)
    target_cost = 10000

    # TODO fees

    hypnox.watchdog.log.info("computing positions from " +
                             str(indicators.index[0]) + " until " +
                             str(indicators.index[-1]))

    # compute entries
    positions = []
    for idx, ind in indicators.iterrows():
        if ind["signal"] == "buy":
            entry_amount = target_cost / ind["open"]

            hypnox.watchdog.log.info(
                market.bprint(entry_amount) + " @ " +
                market.qprint(ind["open"]) + " = " +
                market.qprint(target_cost))

            positions.append(
                hypnox.db.Position(status="closed",
                                   entry_cost=target_cost,
                                   entry_amount=entry_amount,
                                   entry_price=ind["open"],
                                   entry_time=idx))

    # compute exits
    total_pnl = 0
    for position in positions:
        for idx, ind in indicators.loc[position.entry_time:].iterrows():
            price_delta = ind["open"] - position.entry_price
            tmp_roi = price_delta / position.entry_amount

            if (tmp_roi >= strategy["MIN_ROI_PCT"]
                    or tmp_roi <= strategy["STOP_LOSS_PCT"]
                    or ind["signal"] == "sell"):

                total_pnl += price_delta
                position.exit_time = idx
                position.exit_price = ind["open"]
                position.pnl = price_delta
                break

    if not positions:
        hypnox.watchdog.log.info("no positions entered")
        return

    hypnox.watchdog.log.info("initial balance: " + market.qprint(target_cost))
    hypnox.watchdog.log.info("buy and hold amount at first position: " +
                             market.bprint(positions[0].entry_amount))
    hypnox.watchdog.log.info("buy and hold value at last position: " +
                             market.qprint(positions[-1].entry_price *
                                           positions[0].entry_amount))
    hypnox.watchdog.log.info("number of days: " +
                             str(positions[-1].entry_time -
                                 positions[0].entry_time))
    hypnox.watchdog.log.info("number of trades: " + str(len(positions)))
    hypnox.watchdog.log.info("pnl: " + market.qprint(total_pnl))
    hypnox.watchdog.log.info(
        "roi: " + str(round(((total_pnl / target_cost) - 1) * 100, 2)) + "%")
    hypnox.watchdog.log.info("roi vs buy and hold: " + str(
        round(((total_pnl /
                (positions[-1].entry_price * positions[0].entry_amount)) - 1) *
              100, 2)) + "%")
