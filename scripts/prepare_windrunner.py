import pandas

from sliver.indicators.hypnox import HYPNOX
from sliver.strategies.hypnox import HypnoxTweet
from sliver.indicators.bb import BB
from sliver.indicators.atr import ATR
from sliver.indicators.macd import MACD
from sliver.indicators.renko import RENKO
from sliver.indicators.moon import MOON


def prepare():
    df = pandas.read_csv("etc/binance_ohlc_4h.csv")
    df.time = pandas.to_datetime(df.time).dt.tz_localize(None)

    filter = b"btc|bitcoin"

    q = (
        HypnoxTweet.get_tweets_by_model("i20230219")
        .where(HypnoxTweet.text.iregexp(filter))
        .where(HypnoxTweet.time > df.iloc[0].time)
    )
    tweets = pandas.DataFrame(q.dicts())
    tweets = tweets.dropna()
    # 216688 tweets from 20200704001304 until 20230404164147

    df = HYPNOX(df, tweets, "4h")
    df = ATR(df)
    df = BB(df)
    df = MACD(df)
    df = MOON(df)

    bricks = RENKO(df, use_atr=True)

    df.drop(columns=["open", "high", "low", "close"], inplace=True)
    bricks = bricks.merge(df, on="time")
    bricks = bricks.dropna()
    bricks.drop(
        columns=["time", "high", "low", "atr", "ma", "n_samples", "mean", "variance"],
        inplace=True,
    )
    bricks.reset_index(drop=True, inplace=True)

    bricks["direction"] = -1
    bricks.loc[(bricks.close - bricks.open > 0), "direction"] = 1

    bricks.bolu = bricks.bolu / bricks.close
    bricks.bold = bricks.bold / bricks.close
    bricks.macd = bricks.macd / bricks.close
    bricks.macd_signal = bricks.macd_signal / bricks.close

    bricks["operation"] = 0
    for idx, brick in bricks.iterrows():
        if idx == 0:
            continue
        last_brick = bricks.iloc[idx - 1]
        if brick.direction == last_brick.direction:
            if last_brick.operation > -4 and last_brick.operation < 4:
                bricks.at[idx, "operation"] = last_brick.operation + brick.direction

    bricks.drop(columns=["open", "close"], inplace=True)

    bricks = bricks.iloc[1:-1].copy()
    bricks.to_csv("etc/windrunner.csv", index=False)


if __name__ == "__main__":
    prepare()
