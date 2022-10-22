import datetime

import pandas
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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


def get_indicators(strategy: hypnox.db.Strategy, prices: pandas.DataFrame):
    # grab tweets based on strategy regex filter
    filter = hypnox.db.Tweet.text.iregexp(
        strategy.tweet_filter.encode("unicode_escape"))
    query = hypnox.db.Tweet.select().where(filter)
    tweets = pandas.DataFrame(query.dicts())
    # check if there are tweets with given params
    if tweets.empty:
        hypnox.watchdog.log.error("no tweets found")
        raise Exception
    # log first stage
    tweets.to_csv(hypnox.config["HYPNOX_LOGS_DIR"] + "/bt1_tweets.tsv",
                  sep="\t")

    # normalize intensities and polarities
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
    # log second stage
    tweets.to_csv(hypnox.config["HYPNOX_LOGS_DIR"] + "/bt2_tweets_post.tsv",
                  sep="\t")

    # sort by strategy timeframe and set index
    prices = prices.sort_values("time")
    prices = prices.set_index("time")
    # log third stage
    prices.to_csv(hypnox.config["HYPNOX_LOGS_DIR"] + "/bt3_prices.tsv",
                  sep="\t")

    # concatenate both dataframes
    indicators = pandas.concat([tweets, prices], join="inner", axis=1)
    # get rid of unused columns
    indicators = indicators[[
        "i_score", "p_score", "open", "high", "low", "close", "volume"
    ]]
    # log fourth stage
    indicators.to_csv(hypnox.config["HYPNOX_LOGS_DIR"] +
                      "/bt4_indicators_pre.tsv",
                      sep="\t")

    # compute signals
    indicators["signal"] = "neutral"
    buy_rule = ((indicators["i_score"] > strategy.i_threshold) &
                (indicators["p_score"] > strategy.p_threshold))
    indicators.loc[buy_rule, "signal"] = "buy"
    sell_rule = ((indicators["i_score"] > strategy.i_threshold) &
                 (indicators["p_score"] < strategy.p_threshold))
    indicators.loc[sell_rule, "signal"] = "sell"
    # log final stage
    indicators.to_csv(hypnox.config["HYPNOX_LOGS_DIR"] + "/bt5_indicators.tsv",
                      sep="\t")

    indicators.index.name = "time"
    indicators.reset_index(inplace=True)

    return indicators


def backtest(args):
    strategy = hypnox.db.Strategy.get(id=args.strategy_id)

    prices = get_prices(strategy)
    indicators = get_indicators(strategy, prices)
    if indicators.empty:
        hypnox.watchdog.log.error("no indicator data computed")
        raise Exception

    target_cost = strategy.market.quote.transform(10000)

    hypnox.watchdog.log.info("computing positions from " +
                             str(indicators.index[0]) + " until " +
                             str(indicators.index[-1]))

    # compute entries
    positions = []
    for idx, ind in indicators.iterrows():
        if ind["signal"] == "buy":
            entry_amount = strategy.market.base.transform(target_cost /
                                                          ind["open"])

            # hypnox.watchdog.log.info(
            #     strategy.market.base.print(entry_amount) + " @ " +
            #     strategy.market.quote.print(ind["open"]) + " (" +
            #     strategy.market.quote.print(target_cost) + ") -- " +
            #     str(ind["time"]))

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

    init_bal = strategy.market.quote.print(target_cost)
    hypnox.watchdog.log.info("initial balance: " + init_bal)

    init_bh_amount = strategy.market.base.print(positions[0].entry_amount)
    hypnox.watchdog.log.info("buy and hold amount at first position: " +
                             init_bh_amount)

    exit_bh_value = positions[-1].entry_price * strategy.market.base.format(
        positions[0].entry_amount)
    hypnox.watchdog.log.info("buy and hold value at last position: " +
                             strategy.market.quote.print(exit_bh_value))

    n_days = str(positions[-1].entry_time - positions[0].entry_time)
    hypnox.watchdog.log.info("number of days: " + n_days)

    n_trades = str(len(positions))
    hypnox.watchdog.log.info("number of trades: " + n_trades)

    pnl = strategy.market.quote.print(total_pnl)
    hypnox.watchdog.log.info("pnl: " + pnl)

    roi = round(total_pnl / target_cost * 100, 2)
    hypnox.watchdog.log.info("roi: " + str(roi) + "%")

    roi_bh = round(((exit_bh_value / target_cost) - 1) * 100, 2)
    hypnox.watchdog.log.info("buy and hold roi: " + str(roi_bh) + "%")

    roi_vs_bh = round((total_pnl / exit_bh_value) * 100, 2)
    hypnox.watchdog.log.info("roi vs buy and hold: " + str(roi_vs_bh) + "%")

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
                        subplot_titles=("OHLC", "Volume", "i_score",
                                        "p_score"),
                        row_width=[0.2, 0.2, 0.6])

    fig.add_trace(
        go.Ohlc(x=indicators["time"],
                open=indicators["open"],
                high=indicators["high"],
                low=indicators["low"],
                close=indicators["close"],
                showlegend=False))

    indicators["buys"] = indicators["close"].where(indicators["signal"] == "buy")
    fig.add_trace(
        go.Scatter(x=indicators["time"],
                   y=(1 - .003) * indicators["buys"],
                   mode="markers",
                   marker=dict(color="Green", size=8)))

    indicators["sells"] = indicators["high"].where(indicators["signal"] == "sell")
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


def get_prices(strategy: hypnox.db.Strategy):
    # grab price data
    prices = hypnox.db.Price.select().where(
        (hypnox.db.Price.market == strategy.market)
        & (hypnox.db.Price.timeframe == strategy.timeframe))
    prices = pandas.DataFrame(prices.dicts())

    # check if there is data for given market and timeframe
    if prices.empty:
        hypnox.watchdog.log.error("no price data found for symbol " +
                                  strategy.market.get_symbol() +
                                  " for timeframe " + strategy.timeframe)
        raise Exception

    return prices
