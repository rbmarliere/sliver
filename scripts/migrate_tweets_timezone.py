#!/usr/bin/env python3

from datetime import datetime

from tqdm import tqdm

import core

if __name__ == "__main__":
    with core.db.connection.atomic():
        tweets = [t for t in core.db.Tweet.select()]
        for tweet in tqdm(tweets):
            tweet.time = datetime.utcfromtimestamp(tweet.time.timestamp())
            tweet.model_i = None
            tweet.intensity = None
            tweet.model_p = None
            tweet.polarity = None
            tweet.save()
