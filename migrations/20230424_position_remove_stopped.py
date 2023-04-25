import datetime

import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import sliver.database as db
from sliver.user_strategy import UserStrategy

migrator = PostgresqlMigrator(db.connection)


class Position(db.BaseModel):
    user_strategy = peewee.ForeignKeyField(UserStrategy)
    next_refresh = peewee.DateTimeField(default=datetime.datetime.utcnow())
    next_bucket = peewee.DateTimeField(default=datetime.datetime.utcnow())
    bucket_max = peewee.BigIntegerField()
    bucket = peewee.BigIntegerField(default=0)
    status = peewee.TextField()
    target_amount = peewee.BigIntegerField(default=0)
    target_cost = peewee.BigIntegerField(default=0)
    entry_cost = peewee.BigIntegerField(default=0)
    entry_amount = peewee.BigIntegerField(default=0)
    entry_price = peewee.BigIntegerField(default=0)
    entry_time = peewee.DateTimeField(null=True)
    exit_time = peewee.DateTimeField(null=True)
    exit_price = peewee.BigIntegerField(default=0)
    exit_amount = peewee.BigIntegerField(default=0)
    exit_cost = peewee.BigIntegerField(default=0)
    fee = peewee.BigIntegerField(default=0)
    pnl = peewee.BigIntegerField(default=0)
    roi = peewee.DecimalField(default=0)
    last_high = peewee.BigIntegerField(default=0)
    last_low = peewee.BigIntegerField(default=0)
    stopped = peewee.BooleanField(default=False)


with db.connection.atomic():
    for position in Position.select():
        if position.stopped:
            position.status = "stopped"
            position.save()

    migrate(
        migrator.drop_column(Position._meta.table_name, "stopped"),
    )
