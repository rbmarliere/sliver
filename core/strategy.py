import datetime
from decimal import Decimal as D

import pandas

import core


def refresh(strategy: core.db.Strategy):
    # ideas:
    # - reset num_orders, spread and refresh_interval dynamically
    # - base decision over price data and inventory (amount opened, risk, etc)

    # update current strategy next refresh time
    freq = "{i}T".format(i=strategy.refresh_interval)
    now = datetime.datetime.utcnow()
    last = now.replace(minute=0, second=0, microsecond=0)
    range = pandas.date_range(last, periods=61, freq=freq)
    series = range.to_series().asfreq(freq)
    strategy.next_refresh = series.loc[series > now].iloc[0]
    core.watchdog.info("next refresh is {n}".format(n=strategy.next_refresh))

    # compute signal for automatic strategies
    if strategy.mode == "auto":
        refresh_indicators(strategy)
        strategy.signal = strategy.get_asignal()

    elif strategy.mode == "random":
        strategy.signal = strategy.get_rsignal()

    core.watchdog.info("signal is {s}".format(s=strategy.signal))

    strategy.save()


def refresh_indicators(strategy: core.db.Strategy,
                       update_only: bool = True) -> pandas.DataFrame:
    # grab indicators
    indicators_q = strategy.get_indicators()
    if indicators_q.count() == 0:
        core.exchange.set_api(exchange=strategy.market.base.exchange)
        core.exchange.download(strategy.market,
                               strategy.timeframe)
    indicators = pandas.DataFrame(indicators_q.dicts())

    # filter relevant data
    strategy_regex = strategy.tweet_filter.encode("unicode_escape")
    f = core.db.Tweet.text.iregexp(strategy_regex)
    f = f & (core.db.Score.model.is_null(False))
    if update_only:
        existing = indicators.dropna()
        indicators = indicators[indicators.isnull().any(axis=1)]
        if indicators.empty:
            core.watchdog.info("indicator data is up to date, skipping...")
            return
        f = f & (core.db.Tweet.time > indicators.iloc[0].time)

    # grab scores
    intensities_q = core.db.get_tweets_by_model(strategy.model_i).where(f)
    polarities_q = core.db.get_tweets_by_model(strategy.model_p).where(f)
    if intensities_q.count() == 0 or polarities_q.count() == 0:
        core.watchdog.info("indicator data is up to date, skipping...")
        return

    intensities = pandas.DataFrame(intensities_q.dicts())
    intensities = intensities.rename(columns={"score": "intensity"})
    intensities = intensities.set_index("time")

    # grab polarities
    polarities = pandas.DataFrame(polarities_q.dicts())
    polarities = polarities.rename(columns={"score": "polarity"})
    polarities = polarities.set_index("time")

    # build tweets dataframe
    tweets = pandas.concat([intensities, polarities], axis=1)
    if tweets.empty:
        core.watchdog.info("indicator data is up to date, skipping...")
        return
    tweets = tweets[["intensity", "polarity"]]

    # grab last computed metrics
    if existing.empty:
        n_samples = 0
        i_mean = 0
        p_mean = 0
        i_variance = 0
        p_variance = 0
    else:
        n_samples = existing.iloc[-1].n_samples
        i_mean = existing.iloc[-1].i_mean
        p_mean = existing.iloc[-1].p_mean
        i_variance = existing.iloc[-1].i_variance
        p_variance = existing.iloc[-1].p_variance

    # compute new metrics
    i_mean, i_variance = core.utils.get_mean_var(tweets.intensity,
                                                 n_samples,
                                                 i_mean,
                                                 i_variance)
    p_mean, p_variance = core.utils.get_mean_var(tweets.polarity,
                                                 n_samples,
                                                 p_mean,
                                                 p_variance)

    # apply normalization
    tweets["i_score"] = (tweets.intensity - i_mean) / i_variance.sqrt()
    tweets["p_score"] = (tweets.polarity - p_mean) / p_variance.sqrt()

    # resample tweets by strat timeframe freq median
    freq = core.utils.get_timeframe_freq(strategy.timeframe)
    tweets = tweets[["i_score", "p_score"]].resample(freq).median().ffill()

    # join both dataframes
    indicators = indicators.set_index("time")
    indicators = indicators.drop("i_score", axis=1)
    indicators = indicators.drop("p_score", axis=1)
    indicators = pandas.concat([indicators, tweets], join="inner", axis=1)

    # fill out remaining columns
    indicators = indicators.drop("price", axis=1)
    indicators.strategy = strategy.id
    indicators.n_samples = n_samples + len(tweets)
    indicators.i_mean = i_mean
    indicators.i_variance = i_variance
    indicators.p_mean = p_mean
    indicators.p_variance = p_variance
    indicators = indicators.rename(columns={"id": "price_id"})
    indicators = indicators.rename(columns={"strategy": "strategy_id"})

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
