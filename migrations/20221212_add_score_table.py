import pandas
import peewee
from playhouse.migrate import PostgresqlMigrator, migrate

import core

core.db.Score.create_table()


class OldTweet(core.db.BaseModel):
    time = peewee.DateTimeField()
    text = peewee.TextField()
    model_i = peewee.TextField(null=True)
    intensity = peewee.DecimalField(null=True)
    model_p = peewee.TextField(null=True)
    polarity = peewee.DecimalField(null=True)

    class Meta:
        table_name = "tweet"


tweets = pandas.DataFrame(OldTweet.select().order_by(OldTweet.id).dicts())

intensities = tweets[["id", "model_i", "intensity"]]
intensities = intensities.rename(
    columns={
        "id": "tweet_id",
        "model_i": "model",
        "intensity": "score"})

polarities = tweets[["id", "model_p", "polarity"]]
polarities = polarities.rename(
    columns={
        "id": "tweet_id",
        "model_p": "model",
        "polarity": "score"})

core.db.Score.insert_many(intensities.to_dict("records")).execute()
core.db.Score.insert_many(polarities.to_dict("records")).execute()

migrator = PostgresqlMigrator(core.db.connection)

migrate(
    migrator.drop_column(core.db.Tweet._meta.table_name, "model_i"),
    migrator.drop_column(core.db.Tweet._meta.table_name, "intensity"),
    migrator.drop_column(core.db.Tweet._meta.table_name, "model_p"),
    migrator.drop_column(core.db.Tweet._meta.table_name, "polarity")
)
