import pandas

import sliver.database as db
from sliver.indicators.atr import ATR
from sliver.indicators.bb import BB
from sliver.indicators.hypnox import HYPNOX
from sliver.indicators.macd import MACD
from sliver.indicators.moon import MOON
from sliver.indicators.renko import RENKO
from sliver.strategies.hypnox import HypnoxTweet


def prepare():
    df = pandas.read_csv("etc/binance_btcusdt_15m.csv")
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

    df = HYPNOX(df, tweets, "15m")
    df = ATR(df, length=9)
    df = BB(df)
    df = MACD(df)
    df = MOON(df)

    df.to_csv("etc/test.csv", index=False)

    bricks = RENKO(df, use_atr=True)

    df.drop(columns=["open", "high", "low", "close"], inplace=True)
    bricks = bricks.merge(df, on="time")
    bricks = bricks.dropna()
    bricks.reset_index(drop=True, inplace=True)
    bricks = bricks[
        [
            "time",
            "open",
            "close",
            "z_score",
            "bolu",
            "bold",
            "macd",
            "macd_signal",
            "moon_phase",
        ]
    ]

    bricks["direction"] = -1
    bricks.loc[(bricks.close - bricks.open > 0), "direction"] = 1

    bricks.bolu = bricks.bolu / bricks.open
    bricks.bold = bricks.bold / bricks.open
    bricks.macd = bricks.macd / bricks.open
    bricks.macd_signal = bricks.macd_signal / bricks.open

    bricks["operation"] = (
        bricks.groupby((bricks.direction != bricks.direction.shift(-1)).cumsum())
        .apply(
            lambda x: pandas.Series(len(x) - 1, x.index)
            .shift()
            .fillna(0)
            .astype("int64")
        )
        .values
    )

    bricks.loc[bricks.direction < 0, "operation"] *= -1
    bricks.operation.clip(upper=4, lower=-4, inplace=True)

    bricks.drop(columns=["open", "close"], inplace=True)

    bricks = bricks.iloc[1:-1].copy()
    bricks.to_csv("etc/windrunner.csv", index=False)


if __name__ == "__main__":
    db.init()
    prepare()
