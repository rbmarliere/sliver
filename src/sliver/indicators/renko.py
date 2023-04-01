import pandas
import math


def RENKO(ohlc, size=10, use_atr=True):
    first = math.floor(ohlc.iloc[0].open / size) * size
    if first == 0:
        first = size

    bricks = []

    for idx, row in ohlc.iterrows():
        price = row.close
        time = row.time

        # first bricks
        if len(bricks) == 0:
            if price > first + 2 * size:
                # green
                size_mult = math.floor((price - first) / size)
                next_bricks = [
                    {
                        "time": time,
                        "open": first + (mult * size),
                        "high": first + ((mult + 1) * size),
                        "low": ohlc.loc[ohlc.index <= idx].close.min()
                        if mult == 0
                        else first + (mult * size),
                        "close": first + ((mult + 1) * size),
                    }
                    for mult in range(0, size_mult)
                ]
                bricks += next_bricks
                curr = next_bricks[-1]
            elif price < first - 2 * size:
                # red
                size_mult = math.floor((first - price) / size)
                next_bricks = [
                    {
                        "time": time,
                        "open": first - (mult * size),
                        "high": ohlc.loc[ohlc.index <= idx].close.max()
                        if mult == 0
                        else first - (mult * size),
                        "low": first - ((mult + 1) * size),
                        "close": first - ((mult + 1) * size),
                    }
                    for mult in range(0, size_mult)
                ]
                bricks += next_bricks
                curr = next_bricks[-1]
            continue

        in_between = ohlc.loc[(ohlc.time > bricks[-1]["time"]) & (ohlc.index <= idx)]
        # in_between.high.max()

        if curr["close"] > curr["open"]:
            # uptrend
            if price > curr["close"] + size:
                # green
                size_mult = math.floor((price - curr["close"]) / size)
                next_bricks = [
                    {
                        "time": time,
                        "open": curr["close"] + (mult * size),
                        "high": curr["close"] + ((mult + 1) * size),
                        "low": in_between.close.min()
                        if mult == 0 and in_between.close.min() < curr["close"] - size
                        else curr["close"] + (mult * size),
                        "close": curr["close"] + ((mult + 1) * size),
                    }
                    for mult in range(0, size_mult)
                ]
                bricks += next_bricks
                curr = next_bricks[-1]
            elif price < curr["open"] - size:
                # red
                size_mult = math.floor((curr["open"] - price) / size)
                next_bricks = [
                    {
                        "time": time,
                        "open": curr["open"] - (mult * size),
                        "high": in_between.close.max()
                        if mult == 0 and in_between.close.max() > curr["open"] + size
                        else curr["open"] - (mult * size),
                        "low": curr["open"] - ((mult + 1) * size),
                        "close": curr["open"] - ((mult + 1) * size),
                    }
                    for mult in range(0, size_mult)
                ]
                bricks += next_bricks
                curr = next_bricks[-1]

        elif curr["open"] > curr["close"]:
            # downtrend
            if price > curr["open"] + size:
                # green
                size_mult = math.floor((price - curr["open"]) / size)
                next_bricks = [
                    {
                        "time": time,
                        "open": curr["open"] + (mult * size),
                        "high": curr["open"] + ((mult + 1) * size),
                        "low": in_between.close.min()
                        if mult == 0 and in_between.close.min() < curr["open"] - size
                        else curr["open"] + (mult * size),
                        "close": curr["open"] + ((mult + 1) * size),
                    }
                    for mult in range(0, size_mult)
                ]
                bricks += next_bricks
                curr = next_bricks[-1]
            elif price < curr["close"] - size:
                # red
                size_mult = math.floor((curr["close"] - price) / size)
                next_bricks = [
                    {
                        "time": time,
                        "open": curr["close"] - (mult * size),
                        "high": in_between.close.max()
                        if mult == 0 and in_between.close.max() > curr["close"] + size
                        else curr["close"] - (mult * size),
                        "low": curr["close"] - ((mult + 1) * size),
                        "close": curr["close"] - ((mult + 1) * size),
                    }
                    for mult in range(0, size_mult)
                ]
                bricks += next_bricks
                curr = next_bricks[-1]

    return pandas.DataFrame(bricks)
