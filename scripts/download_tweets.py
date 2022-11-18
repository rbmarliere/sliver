#!/usr/bin/env python3

import argparse
import getpass
import sys

import pandas
import peewee
import playhouse.shortcuts

import core

if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("--name", required=True)
    argp.add_argument("--host", required=True)
    argp.add_argument("--user", required=True)
    args = argp.parse_args()

    passwd = getpass.getpass("enter db password: ")

    db = peewee.PostgresqlDatabase(
        args.name, **{
            "host": args.host,
            "user": args.user,
            "password": passwd
        })
    db.bind([core.db.Tweet])
    db.connect()

    f = ((core.db.Tweet.model_i.is_null(False)) &
         (core.db.Tweet.model_p.is_null(False)))

    print("grabbing tweets upstream...")
    query = core.db.Tweet.select().where(f).order_by(core.db.Tweet.id)
    upstream_tweets = [t for t in query]
    print("found " + str(len(upstream_tweets)) + " tweets")

    db.close()

    core.db.connection.bind([core.db.Tweet])
    core.db.connection.connect(reuse_if_open=True)

    print("grabbing tweets downstream...")
    query = core.db.Tweet.select().where(f).order_by(core.db.Tweet.id)
    tweets = [t for t in query]
    print("found " + str(len(tweets)) + " tweets")

    new_tweets = list(set(upstream_tweets) - set(tweets))
    if len(new_tweets) == 0:
        print("no new tweets to sync")
        sys.exit(1)

    new_rows = [playhouse.shortcuts.model_to_dict(x) for x in new_tweets]

    df = pandas.DataFrame(new_rows).sort_values("id")

    print("inserting " + str(len(df)) + " new tweets")
    core.db.Tweet.insert_many(df.to_dict("records")).execute()
