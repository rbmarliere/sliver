#!/usr/bin/env python3

import argparse
import getpass
import sys

import peewee

import core

if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("--name", required=True)
    argp.add_argument("--host", required=True)
    argp.add_argument("--user", required=True)
    argp.add_argument("--model", required=True)
    args = argp.parse_args()

    passwd = getpass.getpass("enter db password: ")

    print("fetching scores...")
    f = core.db.Score.model == args.model
    q = core.db.Score \
        .select() \
        .where(f) \
        .order_by(core.db.Score.id)
    if q.count() == 0:
        print("no scores to download")
        sys.exit(1)
    scores = [s for s in q]

    db = peewee.PostgresqlDatabase(
        args.name, **{
            "host": args.host,
            "user": args.user,
            "password": passwd
        })
    db.bind([core.db.Score])
    db.connect()

    with db.atomic():
        c = core.db.Score.delete().where(f).execute()
        print("deleted all {c} upstream scores..."
              .format(c=c))

        print("uploading {c} scores...\n"
              "{first} -- {last}"
              .format(c=len(scores),
                      first=scores[0].id,
                      last=scores[-1].id))
        core.db.Score.insert_many(scores).execute()

        c = core.db.Indicator.delete().execute()
        print("deleted all {c} indicators".format(c=c))
