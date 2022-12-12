import datetime
from decimal import Decimal as D

import pandas

import core


def refresh(strategy: core.db.Strategy,
            next: datetime.datetime = datetime.datetime.utcnow()):
    # ideas:
    # - reset num_orders, spread and refresh_interval dynamically
    # - base decision over price data and inventory (amount opened, risk, etc)

    # update current strategy next refresh time
    strategy.next_refresh = (
        next + datetime.timedelta(minutes=strategy.refresh_interval))

    # compute signal for automatic strategies
    if strategy.mode == "auto":
        refresh_indicators(strategy)
        strategy.signal = strategy.get_asignal()

    elif strategy.mode == "random":
        strategy.signal = strategy.get_rsignal()

    core.watchdog.info("strategy signal is {s}".format(s=strategy.signal))

    strategy.save()


def refresh_indicators(strategy: core.db.Strategy,
                       update_only: bool = True) -> pandas.DataFrame:
    # get price data
    prices = strategy.get_prices()
    if prices.count() == 0:
        core.exchange.set_api(exchange=strategy.market.base.exchange)
        core.exchange.download(strategy.market,
                               strategy.timeframe)

    # grab tweets filtered by strategy regex
    f = core.db.Tweet.text.iregexp(
        strategy.tweet_filter.encode("unicode_escape"))
    tweets = core.db.Tweet.select().where(f).order_by(core.db.Tweet.time)
    tweets = tweets.where(core.db.Tweet.intensity.is_null(False))
    tweets = tweets.where(core.db.Tweet.polarity.is_null(False))

    indicators = [i for i in strategy.indicator_set]

    if indicators and update_only:
        since = indicators[-1].price.time
        prices = prices.where(core.db.Price.time > since)

    # check if there are prices available
    if prices.count() == 0:
        core.watchdog.info(
            "no price data found for computing signals, skipping...")
        return

    # create prices dataframe
    prices = pandas.DataFrame(prices.dicts())
    prices = prices.set_index("time")
    prices = prices.rename(columns={"id": "price_id"})

    # check if there are tweets with given params
    tweets = tweets.where(core.db.Tweet.time >= prices.iloc[0].name)
    if tweets.count() == 0:
        core.watchdog.info(
            "no tweets found for computing signals, skipping...")
        return

    # create tweets dataframe
    tweets = pandas.DataFrame(tweets.dicts())
    tweets = tweets.set_index("time")

    if indicators:
        n_samples = indicators[-1].n_samples + len(tweets)
        i_mean, i_variance = core.utils.get_mean_var(tweets["intensity"],
                                                     indicators[-1].n_samples,
                                                     indicators[-1].i_mean,
                                                     indicators[-1].i_variance)
        p_mean, p_variance = core.utils.get_mean_var(tweets["polarity"],
                                                     indicators[-1].n_samples,
                                                     indicators[-1].p_mean,
                                                     indicators[-1].p_variance)
    else:
        n_samples = len(tweets)
        i_mean, i_variance = core.utils.get_mean_var(tweets["intensity"],
                                                     0, 0, 0)
        p_mean, p_variance = core.utils.get_mean_var(tweets["polarity"],
                                                     0, 0, 0)

    # standardize intensity and polarity scores
    tweets["i_score"] = (
        (tweets["intensity"] - i_mean) / i_variance.sqrt())
    tweets["p_score"] = (
        (tweets["polarity"] - p_mean) / p_variance.sqrt())

    # resample tweets by strat timeframe freq median
    freq = core.utils.get_timeframe_freq(strategy.timeframe)
    tweets = tweets[["i_score", "p_score"]].resample(freq).median().ffill()

    # concatenate both dataframes
    indicators = pandas.concat([tweets, prices], join="inner", axis=1)

    # update new means and variances
    indicators["strategy_id"] = strategy.id
    indicators["n_samples"] = n_samples
    indicators["i_mean"] = i_mean
    indicators["i_variance"] = i_variance
    indicators["p_mean"] = p_mean
    indicators["p_variance"] = p_variance

    # compute signals
    indicators["signal"] = "neutral"
    buy_rule = ((indicators["i_score"] > strategy.i_threshold) &
                (indicators["p_score"] > strategy.p_threshold))
    indicators.loc[buy_rule, "signal"] = "buy"
    sell_rule = ((indicators["i_score"] > strategy.i_threshold) &
                 (indicators["p_score"] < strategy.p_threshold))
    indicators.loc[sell_rule, "signal"] = "sell"

    # reset index
    indicators = indicators.reset_index()

    # get rid of unused columns
    indicators = indicators[[
        "strategy_id",
        "price_id",
        "signal",
        "i_score",
        "i_mean",
        "i_variance",
        "p_score",
        "p_mean",
        "p_variance",
        "n_samples"
    ]]

    # insert rows into the database
    core.db.Indicator.insert_many(indicators.to_dict("records")).execute()
    core.watchdog.info("inserted {c} indicator rows"
                       .format(c=indicators.size))


def backtest(strategy: core.db.Strategy):
    refresh(strategy)

    indicators = pandas.DataFrame(strategy.get_indicators().dicts())

    init_bal = balance = strategy.market.quote.transform(10000)

    buys = []
    sells = []
    positions = []
    positions_timedeltas = []
    curr_pos = None
    for idx, ind in indicators.iterrows():
        if ind["signal"] == "buy":
            if curr_pos is None:
                buys.append(idx)

                curr_pos = core.db.Position(status="closed",
                                            entry_price=ind["open"],
                                            entry_time=ind["time"])

        elif ind["signal"] == "sell":
            if curr_pos is not None:
                sells.append(idx)

                price_delta = ind["open"] - curr_pos.entry_price

                entry_amount = strategy.market.base.transform(balance /
                                                              ind["open"])

                curr_pos.entry_cost = balance
                curr_pos.entry_amount = entry_amount
                curr_pos.exit_time = ind["time"]
                curr_pos.exit_price = ind["open"]
                curr_pos.pnl = price_delta

                balance += price_delta

                time_in_position = curr_pos.exit_time - curr_pos.entry_time
                positions_timedeltas.append(time_in_position)

                positions.append(curr_pos)

                curr_pos = None

    n_days = str(indicators.iloc[-1].time - indicators.iloc[0].time)

    indicators.open = indicators.open.apply(strategy.market.quote.format)
    indicators.high = indicators.high.apply(strategy.market.quote.format)
    indicators.low = indicators.low.apply(strategy.market.quote.format)
    indicators.close = indicators.close.apply(strategy.market.quote.format)
    indicators.volume = indicators.volume.apply(strategy.market.base.format)
    indicators.time = indicators.time.dt.strftime("%Y-%m-%d %H:%M")

    indicators["buys"] = (
        D(1 + .003) *
        indicators.low.where(indicators.index.isin(buys)))
    indicators.buys = indicators.buys.replace({float("nan"): None})

    indicators["sells"] = (
        D(1 + .003) *
        indicators.high.where(indicators.index.isin(sells)))
    indicators.sells = indicators.sells.replace({float("nan"): None})

    if not positions:
        res = indicators.to_dict("list")
        res["backtest_log"] = "no positions entered"
        return res

    init_bh_amount = strategy.market.base.print(positions[0].entry_amount)
    exit_bh_value = (positions[-1].entry_price *
                     strategy.market.base.format(positions[0].entry_amount))
    n_trades = str(len(positions))
    pnl = balance - init_bal
    roi = round(pnl / init_bal * 100, 2)
    roi_bh = round(((exit_bh_value / init_bal) - 1) * 100, 2)
    roi_vs_bh = round((pnl / exit_bh_value) * 100, 2)
    init_bal = strategy.market.quote.print(init_bal)
    balance = strategy.market.quote.print(balance)
    exit_bh_value = strategy.market.quote.print(exit_bh_value)
    pnl = strategy.market.quote.print(pnl)
    avg_timedelta = pandas.Series(positions_timedeltas).mean()

    log = """initial balance: {init_bal}
final balance: {balance}
buy and hold amount at first position: {init_bh_amount}
buy and hold value at last position: {exit_bh_value}
total timedelta: {n_days}
number of trades: {n_trades}
average timedelta in position: {avg_timedelta}
pnl: {pnl}
roi: {roi}%
buy and hold roi: {roi_bh}%
roi vs buy and hold: {roi_vs_bh}%
""".format(init_bal=init_bal,
           balance=balance,
           init_bh_amount=init_bh_amount,
           exit_bh_value=exit_bh_value,
           n_days=n_days,
           n_trades=n_trades,
           pnl=pnl,
           roi=roi,
           roi_bh=roi_bh,
           roi_vs_bh=roi_vs_bh,
           avg_timedelta=avg_timedelta)

    res = indicators.to_dict("list")
    res["backtest_log"] = log

    return res
