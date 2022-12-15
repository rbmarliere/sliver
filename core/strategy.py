import pandas

import core


def refresh(strategy: core.db.Strategy):
    symbol = strategy.market.get_symbol()

    core.watchdog.info("===========================================")
    core.watchdog.info("refreshing strategy {s}".format(s=strategy))
    core.watchdog.info("market is {m}".format(m=symbol))
    core.watchdog.info("timeframe is {T}".format(T=strategy.timeframe))
    core.watchdog.info("exchange is {e}"
                       .format(e=strategy.market.base.exchange.name))
    core.watchdog.info("mode is {m}".format(m=strategy.mode))

    # update tweet scores
    if strategy.model_i:
        model_i = core.models.load(strategy.model_i)
        core.models.replay(model_i)
    if strategy.model_p:
        model_p = core.models.load(strategy.model_p)
        core.models.replay(model_p)

    # download historical price ohlcv data
    core.exchange.download_prices(strategy)

    # ideas:
    # - reset num_orders, spread and refresh_interval dynamically
    # - base decision over price data and inventory (amount opened, risk, etc)

    strategy.refresh_signal()

    strategy.postpone()


def refresh_user(user_strat: core.db.UserStrategy):
    strategy = user_strat.strategy
    exchange = strategy.market.base.exchange
    user = user_strat.user

    core.watchdog.info("...........................................")
    core.watchdog.info("refreshing {u}'s strategy {s}"
                       .format(u=user_strat.user.email,
                               s=user_strat))

    # set api to current exchange
    credential = user.get_active_credential(exchange).get()
    core.exchange.set_api(cred=credential)

    # get active position for current user_strategy
    position = user_strat.get_active_position_or_none()

    if position:
        core.exchange.sync_limit_orders(position)

    # sync user's balances across all exchanges
    core.inventory.sync_balances(user_strat.user)

    if position is None:
        core.watchdog.info("no active position")

        # create position if apt
        if strategy.signal == "buy":
            t_cost = core.inventory.get_target_cost(
                user_strat)

            if (t_cost == 0 or t_cost < strategy.market.cost_min):
                core.watchdog.info("target cost less than minimums, "
                                   "skipping position creation...")

            if t_cost > 0:
                position = core.db.Position.open(user_strat, t_cost)

    if position:
        core.exchange.refresh(position)


def refresh_indicators(strategy: core.db.Strategy,
                       update_only: bool = True) -> int:
    # grab indicators
    indicators_q = strategy.get_indicators()
    if indicators_q.count() == 0:
        core.exchange.download_prices(strategy)
    indicators = pandas.DataFrame(indicators_q.dicts())

    # filter relevant data
    strategy_regex = strategy.tweet_filter.encode("unicode_escape")
    f = core.db.Tweet.text.iregexp(strategy_regex)
    f = f & (core.db.Score.model.is_null(False))
    if update_only:
        existing = indicators.dropna()
        indicators = indicators[indicators.isnull().any(axis=1)]
        if indicators.empty:
            core.watchdog.info("indicator data is up to date")
            return 0
        f = f & (core.db.Tweet.time > indicators.iloc[0].time)

    # grab scores
    intensities_q = core.db.get_tweets_by_model(strategy.model_i).where(f)
    polarities_q = core.db.get_tweets_by_model(strategy.model_p).where(f)
    if intensities_q.count() == 0 or polarities_q.count() == 0:
        core.watchdog.info("indicator data is up to date")
        return 0

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
        core.watchdog.info("indicator data is up to date")
        return 0
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

    return indicators.size
