from decimal import Decimal as D

import peewee

import sliver.database as db
from sliver.alert import get_updates, send_user_message
from sliver.asset import Asset
from sliver.balance import Balance
from sliver.credential import Credential
from sliver.exceptions import AuthenticationError, DisablingError
from sliver.exchange_asset import ExchangeAsset
from sliver.exchanges.factory import ExchangeFactory
from sliver.position import Position
from sliver.print import print
from sliver.user_strategy import UserStrategy


class User(db.BaseModel):
    email = peewee.TextField(unique=True)
    password = peewee.TextField()
    access_key = peewee.TextField(unique=True, null=True)
    max_risk = peewee.DecimalField(default=0.1)
    cash_reserve = peewee.DecimalField(default=0.25)
    telegram_username = peewee.TextField(null=True)
    telegram_chat_id = peewee.TextField(null=True)

    def get_exchange_credential(self, exchange):
        return self.credential_set.where(Credential.exchange == exchange)

    def get_active_credential(self, exchange):
        return self.get_exchange_credential(exchange).where(Credential.active)

    def get_balances_by_asset(self, asset: Asset):
        return (
            Balance.select()
            .join(ExchangeAsset, on=(Balance.asset_id == ExchangeAsset.id))
            .join(Asset)
            .switch(Balance)
            .join(User)
            .where(Balance.user_id == self.id)
            .where(Asset.id == asset.id)
            .order_by(Asset.ticker)
        )

    def get_exchange_balance(self, exchange_asset, sync=False):
        if sync:
            cred = self.get_active_credential(exchange_asset.exchange).get()
            exchange = ExchangeFactory.from_credential(cred)
            exchange.sync_user_balance(self)
        try:
            return Balance.get(user_id=self.id, asset_id=exchange_asset.id)
        except Balance.DoesNotExist:
            raise DisablingError(
                f"(User {self.email}) no balance for "
                f"{exchange_asset.asset.ticker} on {exchange_asset.exchange.name}"
            )

    def is_subscribed(self, strategy_id):
        for u_st in self.userstrategy_set:
            if u_st.strategy_id == strategy_id:
                return u_st.active
        return False

    def send_message(self, message):
        if not self.telegram_username:
            return

        if self.telegram_chat_id is None:
            updates = get_updates()
            for update in updates:
                if update.message.chat.username == self.telegram_username:
                    self.telegram_chat_id = update.message.chat.id
                    self.save()

        if self.telegram_chat_id:
            send_user_message(entity=self.telegram_chat_id, message=message)

    def sync_balances(self):
        active_exchanges = []
        for cred in self.credential_set.where(Credential.active):
            try:
                exchange = ExchangeFactory.from_credential(cred)
                exchange.sync_user_balance(self)
                active_exchanges.append(exchange.id)
            except AuthenticationError:
                cred.disable()

        # delete inactive balances
        for bal in self.balance_set:
            if bal.asset.exchange_id not in active_exchanges:
                bal.delete_instance()

    def get_inventory(self):
        self.sync_balances()

        balances = []
        for asset in Asset.select():
            balance = self.get_balance(asset)
            balances.append(balance)

        return {"balances": balances}

    def get_balance(self, asset):
        balance = {
            "ticker": asset.ticker,
            "total": 0,
        }

        for bal in self.get_balances_by_asset(asset):
            total = bal.asset.format(bal.total)
            balance["total"] += total

        return balance

    def get_free_balances(self, strategy):
        base = strategy.market.base
        base_balance = self.get_exchange_balance(base).total

        quote = strategy.market.quote
        quote_balance = self.get_exchange_balance(quote).total

        print(f"base: {base.print(base_balance)}")
        print(f"quote: {quote.print(quote_balance)}")

        b_count = 0
        q_count = 0

        for u_st in UserStrategy.get_by_exchange(self, quote.exchange):
            strat = u_st.strategy
            if strat == strategy:
                continue

            pos = Position.get_open_by_user_strategy(u_st).get_or_none()

            if pos is None:
                if strat.market.quote == quote:
                    q_count += 1

                if strat.market.base == base:
                    b_count += 1

            else:
                if strategy.side == "long":
                    if (strat.side == "long" and strat.market.quote == quote) or (
                        strat.side == "short" and strat.market.base == quote
                    ):
                        if strat.side == "long":
                            base_balance -= pos.entry_amount
                            quote_balance -= pos.target_cost

                        elif strat.side == "short":
                            base_balance -= pos.entry_cost
                            quote_balance -= pos.target_amount

                    if (strat.side == "long" and strat.market.quote == base) or (
                        strat.side == "short" and strat.market.base == base
                    ):
                        if strat.side == "long":
                            base_balance -= pos.target_cost
                            quote_balance -= pos.entry_amount

                        elif strat.side == "short":
                            base_balance -= pos.target_amount
                            quote_balance -= pos.entry_cost

                elif strategy.side == "short":
                    if (strat.side == "long" and strat.market.quote == base) or (
                        strat.side == "short" and strat.market.base == base
                    ):
                        if strat.side == "long":
                            base_balance -= pos.target_cost
                            quote_balance -= pos.entry_amount

                        elif strat.side == "short":
                            base_balance -= pos.target_amount
                            quote_balance -= pos.entry_cost

                    if (strat.side == "long" and strat.market.quote == quote) or (
                        strat.side == "short" and strat.market.base == quote
                    ):
                        if strat.side == "long":
                            base_balance -= pos.entry_amount
                            quote_balance -= pos.target_cost

                        elif strat.side == "short":
                            base_balance -= pos.entry_cost
                            quote_balance -= pos.target_amount

        base_balance /= b_count + 1
        quote_balance /= q_count + 1

        base_balance = max(D(base_balance), D(0))
        quote_balance = max(D(quote_balance), D(0))

        return base_balance, quote_balance
