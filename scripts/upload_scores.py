#!/usr/bin/env python3

import argparse
import getpass

import peewee

import core

if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("--name", required=True)
    argp.add_argument("--host", required=True)
    argp.add_argument("--user", required=True)
    args = argp.parse_args()

    passwd = getpass.getpass("enter db password: ")

    print("grabbing intensity scores...")
    f = ((core.db.Tweet.model_i.is_null(False)) &
         (core.db.Tweet.intensity.is_null(False)))
    fd1 = ["model_i", "intensity"]
    q = core.db.Tweet.select().where(f).order_by(core.db.Tweet.id)
    t1 = [t for t in q]

    print("grabbing polarity scores...")
    f = ((core.db.Tweet.model_p.is_null(False)) &
         (core.db.Tweet.polarity.is_null(False)))
    fd2 = ["model_p", "polarity"]
    q = core.db.Tweet.select().where(f).order_by(core.db.Tweet.id)
    t2 = [t for t in q]

    db = peewee.PostgresqlDatabase(
        args.name, **{
            "host": args.host,
            "user": args.user,
            "password": passwd
        })
    db.bind([core.db.Tweet])
    db.connect()

    with db.atomic():
        print("removing upstream current scores...")
        core.db.Tweet.update({
            core.db.Tweet.model_i: None,
            core.db.Tweet.intensity: None,
            core.db.Tweet.model_p: None,
            core.db.Tweet.polarity: None
        }).execute()

        print("uploading {c} intensity records...\n"
              "{first} -- {last}"
              .format(c=len(t1),
                      first=t1[0].id,
                      last=t1[-1].id))
        core.db.Tweet.bulk_update(t1,
                                  fields=fd1,
                                  batch_size=2048)

        print("uploading {c} polarity records...\n"
              "{first} -- {last}"
              .format(c=len(t2),
                      first=t2[0].id,
                      last=t2[-1].id))
        core.db.Tweet.bulk_update(t2,
                                  fields=fd2,
                                  batch_size=2048)

        c = core.db.Indicator.delete().execute()
        print("deleted all {c} indicators".format(c=c))
