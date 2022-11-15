#!/usr/bin/env python3

from datetime import datetime

from tqdm import tqdm

import core

if __name__ == "__main__":
    with core.db.connection.atomic():
        tweets = [t for t in core.db.Tweet.select()]
        for tweet in tqdm(tweets):
            new_time = datetime.utcfromtimestamp(tweet.time.timestamp())
            if new_time != tweet.time:
                print("old time: " + str(tweet.time))
                print("new time for " + str(tweet.id) + ": " + str(new_time))
                tweet.time = new_time
            tweet.model_i = None
            tweet.intensity = None
            tweet.model_p = None
            tweet.polarity = None
            tweet.save()

        answer = input("Task completed. Continue?")
        if answer.lower() in ["n", "no"]:
            raise Exception
