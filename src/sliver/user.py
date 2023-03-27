import peewee

import sliver.database as db
from sliver.alert import send_user_message
from sliver.asset import Asset
from sliver.balance import Balance
from sliver.credential import Credential
from sliver.exchange_asset import ExchangeAsset


class User(db.BaseModel):
    email = peewee.TextField(unique=True)
    password = peewee.TextField()
    access_key = peewee.TextField(unique=True, null=True)
    max_risk = peewee.DecimalField(default=0.1)
    cash_reserve = peewee.DecimalField(default=0.25)
    telegram_username = peewee.TextField(null=True)
    telegram_chat_id = peewee.TextField(null=True)  # TODO remove

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

    def is_subscribed(self, strategy_id):
        for u_st in self.userstrategy_set:
            if u_st.strategy_id == strategy_id:
                return u_st.active
        return False

    def send_message(self, message):
        if not self.telegram_username:
            return

        send_user_message(self.telegram_username, message)

    def sync_balances(self):
        ...

    def get_inventory(self):
        self.sync_balances()
        ...

    def get_balance(self, exchange_asset):
        ...

    def get_target_cost(strategy):
        ...
