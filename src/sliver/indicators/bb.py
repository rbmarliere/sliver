def BB(ohlc, ma_period=20, num_std=2, use_ema=False):
    df = ohlc.copy()

    df["tp"] = (df.high + df.low + df.close) / 3

    if use_ema:
        df["ma"] = df.tp.ewm(span=ma_period).mean()
    else:
        df["ma"] = df.tp.rolling(ma_period).mean()

    std = df.tp.rolling(ma_period).std(ddof=0)
    df["bolu"] = df.ma + num_std * std
    df["bold"] = df.ma - num_std * std

    return df
