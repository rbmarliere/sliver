import peewee

import sliver.database as db
from sliver.alert import get_updates, send_user_message
from sliver.asset import Asset
from sliver.balance import Balance
from sliver.credential import Credential
from sliver.exchange_asset import ExchangeAsset
from sliver.exchanges.factory import ExchangeFactory


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
            exchange = ExchangeFactory.from_credential(cred)
            exchange.sync_user_balance(self)
            active_exchanges.append(exchange)

        # delete inactive balances
        for bal in self.balance_set:
            if bal.asset.exchange not in active_exchanges:
                bal.delete_instance()

    def get_inventory(self):
        from sliver.position import Position

        self.sync_balances()

        balances = []
        inv_free_val = inv_used_val = inv_total_val = 0

        for asset in Asset.select():
            balance = self.get_balance(asset)
            balances.append(balance)
            inv_free_val += balance["free_value"]
            inv_used_val += balance["used_value"]
            inv_total_val += balance["total_value"]

        inventory = {}
        inventory["balances"] = sorted(
            balances, key=lambda k: k["total_value"], reverse=True
        )
        inventory["free_value"] = inv_free_val
        inventory["used_value"] = inv_used_val
        inventory["total_value"] = inv_total_val

        inventory["positions_reserved"] = 0
        inventory["positions_value"] = 0
        for pos in Position.get_open_user_positions(self):
            pos_asset = pos.user_strategy.strategy.market.quote
            # TODO positions_reserved could be other than USDT
            inventory["positions_reserved"] += pos_asset.format(pos.target_cost)
            inventory["positions_value"] += pos_asset.format(
                pos.entry_cost - pos.exit_cost
            )

        inventory["net_liquid"] = (
            inventory["total_value"] - inventory["positions_reserved"]
        )

        inventory["max_risk"] = inventory["net_liquid"] * self.max_risk

        return inventory

    def get_exchange_balance(self, exchange_asset):
        cred = self.get_active_credential(exchange_asset.exchange).get()
        exchange = ExchangeFactory.from_credential(cred)
        exchange.sync_user_balance(self)
        return Balance.get(user_id=self.id, asset_id=exchange_asset.id)

    def get_balance(self, asset):
        balance = {
            "ticker": asset.ticker,
            "free": 0,
            "used": 0,
            "total": 0,
            "free_value": 0,
            "used_value": 0,
            "total_value": 0,
        }

        for bal in self.get_balances_by_asset(asset):
            if bal.total_value == 0:
                continue

            asset = bal.asset.asset

            free = bal.asset.format(bal.free)
            used = bal.asset.format(bal.used)
            total = bal.asset.format(bal.total)
            balance["free"] += free
            balance["used"] += used
            balance["total"] += total

            free_val = bal.value_asset.format(bal.free_value)
            used_val = bal.value_asset.format(bal.used_value)
            total_val = bal.value_asset.format(bal.total_value)
            balance["free_value"] += free_val
            balance["used_value"] += used_val
            balance["total_value"] += total_val

        return balance
