import os
import sys

import pandas
import strategies

import sliver.database as db
from sliver.config import Config

if __name__ == "__main__":
    db.init()

    cache_file = f"{Config().LOGS_DIR}/cache.tsv"

    # check if cache_file exists
    if not os.path.isfile(cache_file):
        print("cache file does not exist")
        sys.exit(0)

    cache = pandas.read_csv(cache_file, sep="\t")

    with db.connection.atomic():
        strategies.hypnox.HypnoxTweet.insert_many(cache.to_dict("records")).execute()

    print(f"inserted {len(cache)} records")

    # delete cache_file
    os.remove(cache_file)
