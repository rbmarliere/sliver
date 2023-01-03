#!/usr/bin/env python3

import pandas
import os
import sys
import core
import strategies

cache_file = core.config["LOGS_DIR"] + "/cache.tsv"

# check if cache_file exists
if not os.path.isfile(cache_file):
    print("cache file does not exist")
    sys.exit(0)

cache = pandas.read_csv(cache_file, sep="\t")

try:
    with core.db.connection.atomic():
        strategies.hypnox.HypnoxTweet.insert_many(
            cache.to_dict("records")).execute()

    print("inserted {c} records".format(c=len(cache)))

    # delete cache_file
    os.remove(cache_file)
except:
    print("error inserting records")
    sys.exit(1)
