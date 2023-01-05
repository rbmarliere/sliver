from decimal import Decimal as D

import pandas
import peewee

import core


class BaseStrategy(core.db.BaseModel):
    strategy = peewee.ForeignKeyField(core.db.Strategy, primary_key=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__.update(self.strategy.__data__)

    def get_signal(self):
        indicator = self.strategy \
            .indicator_set \
            .order_by(core.db.Indicator.id.desc()) \
            .get_or_none()
        if indicator:
            return indicator.signal
        return "neutral"

    def get_indicators(self):
        return self.strategy.get_prices() \
            .select(core.db.Price, core.db.Indicator) \
            .join(core.db.Indicator,
                  peewee.JOIN.LEFT_OUTER,
                  on=((core.db.Indicator.price_id == core.db.Price.id)
                      & (core.db.Indicator.strategy == self)))

    def get_indicators_df(self, query=None):
        if query is None:
            query = self.get_indicators()

        df = pandas.DataFrame(query.dicts())

        if not df.empty:
            buys = []
            sells = []
            curr_pos = False
            for idx, row in df.iterrows():
                if row.signal == "buy":
                    if not curr_pos:
                        buys.append(idx)
                        curr_pos = True
                elif row.signal == "sell":
                    if curr_pos:
                        sells.append(idx)
                        curr_pos = False
            df.time = df.time.dt.strftime("%Y-%m-%d %H:%M")
            df.open = df.open.apply(self.strategy.market.quote.format)
            df.high = df.high.apply(self.strategy.market.quote.format)
            df.low = df.low.apply(self.strategy.market.quote.format)
            df.close = df.close.apply(self.strategy.market.quote.format)
            df.volume = df.volume.apply(self.strategy.market.base.format)
            df["buys"] = df.open.where(df.index.isin(buys))
            df.buys = df.buys * D("0.995")
            df.buys = df.buys.replace({float("nan"): None})
            df["sells"] = df.open.where(df.index.isin(sells))
            df.sells = df.sells * D("1.005")
            df.sells = df.sells.replace({float("nan"): None})

        return df

    def refresh(self):
        pass

    def load_fields(self, user):
        self.id = self.strategy_id
        self.market_id = self.strategy.market_id
        self.subscribed = user.is_subscribed(self.id)
        self.signal = self.get_signal()
        self.symbol = self.strategy.market.get_symbol()
        self.exchange = self.strategy.market.quote.exchange.name
