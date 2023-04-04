def MACD(ohlc, fast=12, slow=26, signal=9, use_ema=True):
    df = ohlc.copy()

    if use_ema:
        df["fast"] = df.close.ewm(span=fast, min_periods=fast).mean()
        df["slow"] = df.close.ewm(span=slow, min_periods=slow).mean()
    else:
        df["fast"] = df.close.rolling(fast).mean()
        df["slow"] = df.close.rolling(slow).mean()

    df["macd"] = df.fast - df.slow
    df["macd_signal"] = df.macd.ewm(span=signal, min_periods=signal).mean()

    df.drop(["fast", "slow"], axis=1, inplace=True)

    return df
