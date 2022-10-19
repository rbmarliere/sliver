import datetime

import pandas

import hypnox


def refresh(strategy: hypnox.db.Strategy):
    # ideas:
    # - reset num_orders, spread and refresh_interval dynamically
    # - base decision over price data and inventory (amount opened, risk, etc)

    # update current strategy next refresh time
    strategy.next_refresh = (
        datetime.datetime.utcnow() +
        datetime.timedelta(minutes=strategy.refresh_interval))

    # compute signal for automatic strategies
    if strategy.mode == "auto":
        strategy.signal = get_signal(strategy)

    strategy.save()


def get_signal(strategy: hypnox.db.Strategy):
    return get_indicators(strategy)[-1]["signal"]


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

    tweets.to_csv(hypnox.config["HYPNOX_LOGS_DIR"] + "/bt1_tweets.tsv",
                  sep="\t")

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
    # TODO where intensity > threshold
    tweets["p_score"] = tweets.groupby("floor")["polarity"].sum()
    # remove duplicated indexes
    tweets = tweets.loc[~tweets.index.duplicated(keep='first')]

    tweets.to_csv(hypnox.config["HYPNOX_LOGS_DIR"] + "/bt2_tweets_post.tsv",
                  sep="\t")

    # grab price data
    prices = hypnox.db.Price.select().where(
        (hypnox.db.Price.market == strategy.market)
        & (hypnox.db.Price.timeframe == strategy.timeframe))
    prices = pandas.DataFrame(prices.dicts())

    # check if there is data for given params
    if prices.empty:
        hypnox.watchdog.log.error("no price data found for symbol " +
                                  strategy.market.get_symbol() +
                                  " for timeframe " + strategy.timeframe)
        raise Exception

    # sort by strategy timeframe and set index
    prices.sort_values("time", inplace=True)
    prices.set_index("time", inplace=True)

    prices.to_csv(hypnox.config["HYPNOX_LOGS_DIR"] + "/bt3_prices.tsv",
                  sep="\t")

    # concatenate both dataframes
    indicators = pandas.concat([tweets, prices], join='inner', axis=1)
    # get rid of unused columns
    indicators = indicators[[
        "i_median", "p_score", "open", "high", "low", "close", "volume"
    ]]

    indicators.to_csv(hypnox.config["HYPNOX_LOGS_DIR"] +
                      "/bt4_indicators_pre.tsv",
                      sep="\t")

    # compute signal
    indicators["signal"] = "neutral"
    buy_rule = ((indicators["i_median"] > strategy.i_threshold) &
                (indicators["p_score"] > strategy.p_threshold))
    indicators.loc[buy_rule, "signal"] = "buy"
    sell_rule = ((indicators["i_median"] < strategy.i_threshold) &
                 (indicators["p_score"] < strategy.p_threshold))
    indicators.loc[sell_rule, "signal"] = "sell"

    indicators.to_csv(hypnox.config["HYPNOX_LOGS_DIR"] + "/bt5_indicators.tsv",
                      sep="\t")

    return indicators


def backtest(args):
    # TODO charts, fees?

    strategy = hypnox.db.Strategy.get(id=args.strategy_id)

    # check if symbol is supported by hypnox
    indicators = get_indicators(strategy)
    if indicators.empty:
        hypnox.watchdog.log.error("no indicator data computed")
        raise Exception

    target_cost = 10000

    hypnox.watchdog.log.info("computing positions from " +
                             str(indicators.index[0]) + " until " +
                             str(indicators.index[-1]))

    # compute entries
    positions = []
    for idx, ind in indicators.iterrows():
        if ind["signal"] == "buy":
            entry_amount = target_cost / ind["open"]

            hypnox.watchdog.log.info(
                strategy.market.base.print(entry_amount) + " @ " +
                strategy.market.quote.print(ind["open"]) + " = " +
                strategy.market.quote.print(target_cost))

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
            # tmp_roi = price_delta / position.entry_amount

            # if (tmp_roi >= strategy["MIN_ROI_PCT"]
            #         or tmp_roi <= strategy["STOP_LOSS_PCT"]
            if ind["signal"] == "sell":
                total_pnl += price_delta
                position.exit_time = idx
                position.exit_price = ind["open"]
                position.pnl = price_delta
                break

    if not positions:
        hypnox.watchdog.log.info("no positions entered")
        return

    hypnox.watchdog.log.info("initial balance: " +
                             strategy.market.quote.print(target_cost))
    hypnox.watchdog.log.info(
        "buy and hold amount at first position: " +
        strategy.market.base.print(positions[0].entry_amount))
    hypnox.watchdog.log.info(
        "buy and hold value at last position: " +
        strategy.market.quote.print(positions[-1].entry_price *
                                    positions[0].entry_amount))
    hypnox.watchdog.log.info("number of days: " +
                             str(positions[-1].entry_time -
                                 positions[0].entry_time))
    hypnox.watchdog.log.info("number of trades: " + str(len(positions)))
    hypnox.watchdog.log.info("pnl: " + strategy.market.quote.print(total_pnl))
    hypnox.watchdog.log.info(
        "roi: " + str(round(((total_pnl / target_cost) - 1) * 100, 2)) + "%")
    hypnox.watchdog.log.info("roi vs buy and hold: " + str(
        round(((total_pnl /
                (positions[-1].entry_price * positions[0].entry_amount)) - 1) *
              100, 2)) + "%")
