def RSI(closes, period=14, scalar=100):
    df = closes.copy()

    delta = df.diff().dropna()

    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)

    avg_gains = gains.rolling(period).mean()
    avg_losses = losses.rolling(period).mean()

    return scalar * avg_gains / (avg_gains + abs(avg_losses))
