import argparse
import getpass
import sys

import peewee

import sliver.database as db
from sliver.strategies.hypnox import HypnoxIndicator, HypnoxScore

if __name__ == "__main__":
    db.init()

    argp = argparse.ArgumentParser()
    argp.add_argument("--name", required=True)
    argp.add_argument("--host", required=True)
    argp.add_argument("--user", required=True)
    argp.add_argument("--model", required=True)
    args = argp.parse_args()

    passwd = getpass.getpass("enter db password: ")

    remote = peewee.PostgresqlDatabase(
        args.name, **{"host": args.host, "user": args.user, "password": passwd}
    )
    remote.bind([HypnoxScore])
    remote.connect()

    print("downloading scores...")
    f = HypnoxScore.model == args.model
    q = HypnoxScore.select().where(f).order_by(HypnoxScore.id)
    if q.count() == 0:
        print("no scores to download")
        sys.exit(1)
    scores = [s for s in q]

    remote.close()
    db.connection.bind([HypnoxScore])
    db.connection.connect(reuse_if_open=True)

    with remote.atomic():
        c = HypnoxScore.delete().where(f).execute()
        print(f"deleted all {c} downstream scores")

        print(f"inserting {len(scores)} scores...")
        print(f"{scores[0].id} -- {scores[-1].id}")

        HypnoxScore.insert_many(scores).execute()

        c = HypnoxIndicator.delete().execute()
        print(f"deleted all {c} indicators")
