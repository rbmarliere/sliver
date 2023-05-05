from abc import ABCMeta

import peewee

from sliver.config import Config


connection = peewee.PostgresqlDatabase(None)


def db_init():
    connection.init(
        Config().DB_NAME,
        host=Config().DB_HOST,
        user=Config().DB_USER,
        password=Config().DB_PASSWORD,
    )


class BaseModel(peewee.Model):
    __metaclass__ = ABCMeta

    class Meta:
        database = connection
