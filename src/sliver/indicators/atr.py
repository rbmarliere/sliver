def ATR(ohlc, length=14, smoothing="sma"):
    df = ohlc.copy()

    df["tr0"] = abs(df.high - df.low)
    df["tr1"] = abs(df.high - df.close.shift(1))
    df["tr2"] = abs(df.close.shift(1) - df.low)

    df["tr"] = df[["tr0", "tr1", "tr2"]].max(axis=1)

    if smoothing == "rma":
        # https://www.tradingview.com/pine-script-reference/v5/#fun_ta{dot}rma
        alpha = 1 / length
        first = df.tr.loc[: length - 1].mean()
        df.loc[length - 1, "atr"] = first
        for idx, row in df.loc[length:].iterrows():
            df.loc[idx, "atr"] = alpha * row.tr + (1 - alpha) * df.atr.loc[idx - 1]

    elif smoothing == "ema":
        df["atr"] = df.tr.ewm(span=length).mean()
    elif smoothing == "sma":
        df["atr"] = df.tr.rolling(length).mean()
    else:
        raise ValueError("invalid smoothing method")

    df.drop(["tr0", "tr1", "tr2", "tr"], axis=1, inplace=True)

    # fill NaN with 0
    df.atr.fillna(0, inplace=True)

    return df
