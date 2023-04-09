import argparse
import getpass
import sys

import pandas
import peewee
import playhouse.shortcuts

import sliver.database as db
from sliver.strategies.hypnox import HypnoxTweet

if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("--name", required=True)
    argp.add_argument("--host", required=True)
    argp.add_argument("--user", required=True)
    argp.add_argument(
        "-u",
        "--update-only",
        help="if unset, reset table and download everything",
        action="store_true",
    )
    args = argp.parse_args()

    passwd = getpass.getpass("enter db password: ")

    tweet_table = HypnoxTweet

    if not args.update_only:
        print("resetting tweet table...")
        tweet_table.drop_table()
        tweet_table.create_table()

    remote = peewee.PostgresqlDatabase(
        args.name, **{"host": args.host, "user": args.user, "password": passwd}
    )
    remote.bind([tweet_table])
    remote.connect()

    print("fetching tweets upstream...")
    query = tweet_table.select().order_by(tweet_table.id)
    upstream_tweets = [t for t in query]
    print(f"found {len(upstream_tweets)} tweets")

    remote.close()
    db.connection.bind([tweet_table])
    db.connection.connect(reuse_if_open=True)

    print("fetching tweets downstream...")
    query = tweet_table.select().order_by(tweet_table.id)
    tweets = [t for t in query]
    print(f"found {len(tweets)} tweets")

    if args.update_only:
        new_tweets = list(set(upstream_tweets) - set(tweets))
        if len(new_tweets) == 0:
            print("no new tweets to sync")
            sys.exit(1)
    else:
        new_tweets = upstream_tweets

    new_rows = [playhouse.shortcuts.model_to_dict(x) for x in new_tweets]

    df = pandas.DataFrame(new_rows).sort_values("id")

    print(f"inserting {len(df)} new tweets")
    tweet_table.insert_many(df.to_dict("records")).execute()
