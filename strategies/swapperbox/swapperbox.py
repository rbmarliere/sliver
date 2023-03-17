import datetime

import pandas
import peewee

import core
from ..base import BaseStrategy


path = "strategies/swapperbox/"


class SwapperBoxMessage(core.db.BaseModel):
    telegram_message_id = peewee.TextField()
    date = peewee.DateTimeField()
    text = peewee.TextField()


class SwapperBoxStrategy(BaseStrategy):
    url = peewee.TextField(null=True)
    telegram = peewee.TextField(null=True)

    def init_indicators(self, indicators):
        NEUTRAL = core.strategies.Signal.NEUTRAL.value

        # signals = pandas.read_html(self.url)[1]
        si = pandas.read_csv(path+"signals.tsv", sep="\t")
        si.time = pandas.to_datetime(si.time) \
            .dt.tz_localize("America/Sao_Paulo") \
            .dt.tz_convert("UTC") \
            .dt.tz_localize(None)
        freq = core.utils.get_timeframe_freq(self.strategy.timeframe)
        si = si.set_index("time")

        si = si.resample(freq).ffill()

        indicators.signal = si.signal
        until_last = indicators.loc[indicators.index < si.iloc[-1].name,
                                    "signal"]
        indicators.signal = until_last.fillna(NEUTRAL)

        return indicators

    def refresh_messages(self):
        messages = pandas.DataFrame(SwapperBoxMessage.select().dicts())

        upstream = core.telegram.get_messages(self.telegram, limit=0)

        if upstream is None or upstream.total == len(messages):
            core.watchdog.info("swapperbox: no new messages")
            return messages
        limit = None
        if len(messages) > 0:
            limit = upstream.total - len(messages)

        missing = core.telegram.get_messages(self.telegram, limit=limit)

        if len(missing) > 0:
            new = pandas.DataFrame()
            new["telegram_message_id"] = [msg.id for msg in missing]
            new["text"] = [msg.text for msg in missing]
            new["date"] = [msg.date for msg in missing]
            new.text = new.text.str.strip()
            new.text = new.text.replace(r"\n", " ", regex=True)
            new = new.sort_values("date")

            messages = pandas.concat([messages, new])

            SwapperBoxMessage.\
                insert_many(new.to_dict(orient="records")) \
                .execute()

        return messages

    def refresh(self):
        self.refresh_indicators()

    def refresh_indicators(self):
        SELL = core.strategies.Signal.SELL.value
        NEUTRAL = core.strategies.Signal.NEUTRAL.value
        BUY = core.strategies.Signal.BUY.value

        indicators = pandas.DataFrame(self.get_indicators().dicts())
        indicators = indicators.set_index("time")
        existing = indicators.dropna()

        if existing.empty:
            indicators = self.init_indicators(indicators)

        missing = indicators.loc[indicators.signal.isnull()].copy()
        if not missing.empty:
            missing = missing.assign(signal=NEUTRAL)

            messages = self.refresh_messages()

            messages = messages.dropna()
            messages = messages.drop_duplicates()
            messages.date = pandas.to_datetime(messages.date, utc=True)
            messages.date = messages.date.dt.tz_localize(None)
            messages = messages.set_index("date")

            new_row = pandas.DataFrame(index=[datetime.datetime.utcnow()])
            messages_plus = pandas.concat([messages, new_row])

            freq = core.utils.get_timeframe_freq(self.strategy.timeframe)
            try:
                messages = messages_plus.resample(freq).bfill()
            except ValueError:
                messages = messages.resample(freq).last().bfill()

            shorts = messages.loc[
                messages.text.str.contains("position: SHORT", na=False)].index
            longs = messages.loc[
                messages.text.str.contains("position: LONG", na=False)].index
            missing.loc[missing.index.isin(longs), "signal"] = BUY
            missing.loc[missing.index.isin(shorts), "signal"] = SELL

            indicators.loc[indicators.index.isin(missing.index), "signal"] = \
                missing.signal

        indicators = indicators.loc[indicators.indicator_id.isnull()]

        with core.db.connection.atomic():
            indicators["strategy"] = self.strategy.id
            indicators["price"] = indicators.id

            core.db.Indicator.insert_many(
                indicators[["strategy", "price", "signal"]]
                .to_dict("records")
            ).execute()
