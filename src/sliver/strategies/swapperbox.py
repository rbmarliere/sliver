import datetime
from logging import info

import pandas
import peewee

import sliver.database as db
from sliver.alert import get_messages
from sliver.strategies.signals import StrategySignals
from sliver.strategy import IStrategy
from sliver.utils import get_timeframe_freq


class SwapperBoxMessage(db.BaseModel):
    telegram_message_id = peewee.TextField(unique=True)
    date = peewee.DateTimeField()
    text = peewee.TextField(null=True)


class SwapperBoxStrategy(IStrategy):
    url = peewee.TextField(null=True)
    telegram = peewee.TextField(null=True)

    @staticmethod
    def setup():
        db.connection.create_tables([SwapperBoxStrategy, SwapperBoxMessage])

    def init_indicators(self, indicators):
        NEUTRAL = StrategySignals.NEUTRAL

        # signals = pandas.read_html(self.url)[1]
        si = pandas.read_csv("etc/swapperbox_signals.tsv", sep="\t")
        si.time = (
            pandas.to_datetime(si.time)
            .dt.tz_localize("America/Sao_Paulo")
            .dt.tz_convert("UTC")
            .dt.tz_localize(None)
        )
        freq = get_timeframe_freq(self.strategy.timeframe)
        si = si.set_index("time")

        si = si.resample(freq).ffill()

        indicators.set_index("time", inplace=True)
        indicators.signal = si.signal
        until_last = indicators.loc[indicators.index < si.iloc[-1].name, "signal"]
        indicators.signal = until_last.fillna(NEUTRAL)
        indicators.reset_index(inplace=True)

        return indicators

    def refresh_messages(self):
        messages = pandas.DataFrame(SwapperBoxMessage.select().dicts())

        upstream = get_messages(entity=self.telegram, limit=0)

        if upstream is None or upstream.total == len(messages):
            info("swapperbox: no new messages")
            return messages
        limit = None
        if len(messages) > 0:
            limit = upstream.total - len(messages)

        missing = get_messages(entity=self.telegram, limit=limit)

        if len(missing) > 0:
            new = pandas.DataFrame()
            new["telegram_message_id"] = [msg.id for msg in missing]
            new["text"] = [msg.text for msg in missing]
            new["date"] = [msg.date for msg in missing]
            new.text = new.text.str.strip()
            new.text = new.text.replace(r"\n", " ", regex=True)
            new = new.sort_values("date")

            messages = pandas.concat([messages, new])

            with db.connection.atomic():
                try:
                    SwapperBoxMessage.insert_many(
                        new.to_dict(orient="records")
                    ).execute()
                except peewee.IntegrityError:
                    info("swapperbox: message(s) already in database")

        return messages

    def refresh_indicators(self, indicators, pending, reset=False):
        SELL = StrategySignals.SELL
        NEUTRAL = StrategySignals.NEUTRAL
        BUY = StrategySignals.BUY

        pending = pending.assign(signal=NEUTRAL)

        if len(indicators) == len(pending):
            pending = self.init_indicators(indicators)

        messages = self.refresh_messages()

        messages = messages[["telegram_message_id", "date", "text"]]
        messages = messages.dropna()
        messages = messages.drop_duplicates()
        messages.date = pandas.to_datetime(messages.date, utc=True)
        messages.date = messages.date.dt.tz_localize(None)
        messages = messages.set_index("date")

        pending = pending.set_index("time")

        new_row = pandas.DataFrame(index=[datetime.datetime.utcnow()])
        messages_plus = pandas.concat([messages, new_row])

        freq = get_timeframe_freq(self.strategy.timeframe)
        try:
            messages = messages_plus.resample(freq).bfill()
        except ValueError:
            messages = messages.resample(freq).last().bfill()

        shorts = messages.loc[
            messages.text.str.contains("position: SHORT", na=False)
        ].index
        longs = messages.loc[
            messages.text.str.contains("position: LONG", na=False)
        ].index
        pending.loc[pending.index.isin(longs), "signal"] = BUY
        pending.loc[pending.index.isin(shorts), "signal"] = SELL

        pending = pending.reset_index()

        return pending
