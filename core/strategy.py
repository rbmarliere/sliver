import datetime

import pandas
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import core


def refresh(strategy: core.db.Strategy):
    # ideas:
    # - reset num_orders, spread and refresh_interval dynamically
    # - base decision over price data and inventory (amount opened, risk, etc)

    # update current strategy next refresh time
    strategy.next_refresh = (
        datetime.datetime.utcnow() +
        datetime.timedelta(minutes=strategy.refresh_interval))

    # compute signal for automatic strategies
    if strategy.mode == "auto":
        update_indicators(strategy)
        strategy.signal = get_signal(strategy)

    strategy.save()


# def get_rsignal():
#     import random
#     i = random.randint(0, 100)
#     if i > 80:
#         return 'buy'
#     elif i < 20:
#         return 'sell'
#     else:
#         return 'neutral'


def get_signal(strategy: core.db.Strategy):
    # signal = get_rsignal()
    # core.watchdog.log.info("* current strategy signal is " + signal)
    # return signal

    indicator = strategy.indicator_set.order_by(
        core.db.Indicator.id.desc()).get_or_none()

    signal = indicator.signal if indicator is not None else "neutral"

    core.watchdog.log.info("* current strategy signal is " + signal)

    return signal


def update_indicators(strategy: core.db.Strategy):
    db_indicators = [i for i in strategy.indicator_set]
    if db_indicators:
        since = db_indicators[-1].price.time
    else:
        since = None

    try:
        indicators = get_indicators(strategy, since=since)
    except:
        return

    indicators = indicators[[
        "price_id", "strategy_id", "signal", "i_score", "p_score"
    ]]

    core.db.Indicator.insert_many(indicators.to_dict("records")).execute()


def get_indicators(strategy: core.db.Strategy, since=None):
    # filter price data by time argument
    if since is None:
        time_filter = True
    else:
        time_filter = core.db.Price.time > since
    # grab price data
    prices = core.db.Price.select().where(
        (core.db.Price.market == strategy.market)
        & (core.db.Price.timeframe == strategy.timeframe)
        & (time_filter))
    prices = pandas.DataFrame(prices.dicts())
    # remove last price row so it doesnt compute signal for incomplete interval
    prices.drop(prices.tail(1).index, inplace=True)
    # check if there are prices available
    if prices.empty:
        core.watchdog.log.info(
            "no price data found for computing signals, skipping...")
        raise Exception
    prices = prices.rename(columns={"id": "price_id"})

    # filter tweets based on price data availability
    time_filter = core.db.Tweet.time >= prices.iloc[0].time
    # filter tweets based on strategy regex
    strat_filter = core.db.Tweet.text.iregexp(
        strategy.tweet_filter.encode("unicode_escape"))
    # put query result in a pandas df
    query = core.db.Tweet.select().where((strat_filter) & (time_filter))
    tweets = pandas.DataFrame(query.dicts())
    # check if there are tweets with given params
    if tweets.empty:
        core.watchdog.log.info(
            "no tweets found for computing signals, skipping...")
        raise Exception

    # normalize intensities and polarities
    # TODO what if median() instead?
    aux = tweets["intensity"].astype("float")
    tweets["i_zscore"] = (aux - aux.mean()) / aux.std()
    aux = tweets["polarity"].astype("float")
    tweets["p_zscore"] = (aux - aux.mean()) / aux.std()
    # sort by date
    tweets.sort_values("time", inplace=True)
    # aggregate tweets by timeframe
    tweets["floor"] = tweets.time.dt.floor(strategy.timeframe)
    # set floor as index
    tweets.set_index("floor", inplace=True)
    # compute intensity z-scores from groups
    tweets["i_score"] = tweets.groupby("floor")["i_zscore"].sum()
    # compute polarity sum from groups
    tweets["p_score"] = tweets.groupby("floor")["p_zscore"].sum()
    # remove duplicated indexes
    tweets = tweets.loc[~tweets.index.duplicated(keep="first")]

    # sort by strategy timeframe and set index
    prices = prices.sort_values("time")
    prices = prices.set_index("time")

    # concatenate both dataframes
    indicators = pandas.concat([tweets, prices], join="inner", axis=1)
    # get rid of unused columns
    indicators = indicators[[
        "price_id", "i_score", "p_score",
        "open", "high", "low", "close", "volume"
    ]]

    # compute signals
    indicators["strategy_id"] = strategy.id
    indicators["signal"] = "neutral"
    buy_rule = ((indicators["i_score"] > strategy.i_threshold) &
                (indicators["p_score"] > strategy.p_threshold))
    indicators.loc[buy_rule, "signal"] = "buy"
    sell_rule = ((indicators["i_score"] > strategy.i_threshold) &
                 (indicators["p_score"] < strategy.p_threshold))
    indicators.loc[sell_rule, "signal"] = "sell"

    indicators.index.name = "time"
    indicators.reset_index(inplace=True)

    return indicators


def backtest(args):
    strategy = core.db.Strategy.get(id=args.strategy_id)

    indicators = get_indicators(strategy)
    if indicators.empty:
        core.watchdog.log.info("no indicator data computed")
        raise Exception

    init_bal = balance = strategy.market.quote.transform(10000)

    core.watchdog.log.info("computing positions from " +
                           str(indicators["time"].iloc[0]) + " until " +
                           str(indicators["time"].iloc[-1]))

    buys = []
    sells = []
    positions = []
    curr_pos = None
    for idx, ind in indicators.iterrows():
        if ind["signal"] == "buy":
            if curr_pos is None:
                buys.append(idx)

                curr_pos = core.db.Position(status="closed",
                                            entry_price=ind["open"],
                                            entry_time=idx)

        elif ind["signal"] == "sell":
            if curr_pos is not None:
                sells.append(idx)

                price_delta = ind["open"] - curr_pos.entry_price

                entry_amount = strategy.market.base.transform(balance /
                                                              ind["open"])

                curr_pos.entry_cost = balance
                curr_pos.entry_amount = entry_amount
                curr_pos.exit_time = idx
                curr_pos.exit_price = ind["open"]
                curr_pos.pnl = price_delta

                balance += price_delta

                positions.append(curr_pos)

                # core.watchdog.log.info(
                #     strategy.market.base.print(curr_pos.entry_amount) +
                #     " @ (" +
                #     strategy.market.quote.print(curr_pos.exit_price) +
                #     " - " +
                #     strategy.market.quote.print(curr_pos.entry_price) +
                #     ") = " +
                #     strategy.market.quote.print(curr_pos.pnl) +
                #     " -- balance: " + strategy.market.quote.print(balance))

                curr_pos = None

    if not positions:
        core.watchdog.log.info("no positions entered")
        return

    core.watchdog.log.info("initial balance: " +
                           strategy.market.quote.print(init_bal))

    core.watchdog.log.info("final balance: " +
                           strategy.market.quote.print(balance))

    init_bh_amount = strategy.market.base.print(positions[0].entry_amount)
    core.watchdog.log.info("buy and hold amount at first position: " +
                           init_bh_amount)

    exit_bh_value = positions[-1].entry_price * strategy.market.base.format(
        positions[0].entry_amount)
    core.watchdog.log.info("buy and hold value at last position: " +
                           strategy.market.quote.print(exit_bh_value))

    n_days = str(positions[-1].entry_time - positions[0].entry_time)
    core.watchdog.log.info("number of days: " + n_days)

    n_trades = str(len(positions))
    core.watchdog.log.info("number of trades: " + n_trades)

    pnl = balance - init_bal
    core.watchdog.log.info("pnl: " + strategy.market.quote.print(pnl))

    roi = round(pnl / init_bal * 100, 2)
    core.watchdog.log.info("roi: " + str(roi) + "%")

    roi_bh = round(((exit_bh_value / init_bal) - 1) * 100, 2)
    core.watchdog.log.info("buy and hold roi: " + str(roi_bh) + "%")

    roi_vs_bh = round((pnl / exit_bh_value) * 100, 2)
    core.watchdog.log.info("roi vs buy and hold: " + str(roi_vs_bh) + "%")

    indicators["open"] = indicators["open"].apply(strategy.market.quote.format)
    indicators["high"] = indicators["high"].apply(strategy.market.quote.format)
    indicators["low"] = indicators["low"].apply(strategy.market.quote.format)
    indicators["close"] = indicators["close"].apply(
        strategy.market.quote.format)
    indicators["volume"] = indicators["volume"].apply(
        strategy.market.quote.format)

    fig = make_subplots(rows=3,
                        cols=1,
                        shared_xaxes=True,
                        vertical_spacing=0.03,
                        subplot_titles=("", "i_score", "p_score"),
                        row_width=[0.2, 0.2, 0.6])

    fig.add_trace(
        go.Ohlc(x=indicators["time"],
                open=indicators["open"],
                high=indicators["high"],
                low=indicators["low"],
                close=indicators["close"],
                showlegend=False))

    indicators["buys"] = indicators["low"].where(indicators.index.isin(buys))
    fig.add_trace(
        go.Scatter(x=indicators["time"],
                   y=(1 - .003) * indicators["buys"],
                   mode="markers",
                   marker=dict(color="Green", size=8)))

    indicators["sells"] = indicators["high"].where(
        indicators.index.isin(sells))
    fig.add_trace(
        go.Scatter(x=indicators["time"],
                   y=(1 + .003) * indicators["sells"],
                   mode="markers",
                   marker=dict(color="Red", size=8)))

    fig.add_trace(go.Bar(x=indicators["time"],
                         y=indicators["i_score"],
                         showlegend=False),
                  row=2,
                  col=1)

    fig.add_trace(go.Bar(x=indicators["time"],
                         y=indicators["p_score"],
                         showlegend=False),
                  row=3,
                  col=1)

    fig.update(layout_xaxis_rangeslider_visible=False)

    fig.show()
