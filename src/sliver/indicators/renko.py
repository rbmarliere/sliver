import pandas
import math


def RENKO(ohlc, size=10, use_atr=True):
    first = math.floor(ohlc.iloc[0].close / size) * size
    if first == 0:
        first = size

    bricks = []

    for idx, row in ohlc.iterrows():
        price = row.close
        time = row.time

        if len(bricks) == 0:
            if price > first + size:
                curr = {
                    "time": time,
                    "open": first,
                    "close": first + size,
                }
                bricks.append(curr)
            elif price < first - size:
                curr = {
                    "time": time,
                    "open": first,
                    "close": first - size,
                }
                bricks.append(curr)
            continue

        if curr["close"] > curr["open"]:
            # uptrend
            if price > curr["close"] + size:
                # green
                size_mult = math.floor((price - curr["close"]) / size)
                next_bricks = [
                    {
                        "time": time,
                        "open": curr["close"] + (mult * size),
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
                        "close": curr["close"] - ((mult + 1) * size),
                    }
                    for mult in range(0, size_mult)
                ]
                bricks += next_bricks
                curr = next_bricks[-1]

    return pandas.DataFrame(bricks)
