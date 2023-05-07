import argparse
import datetime
import re
import ssl

import pandas
import peewee
import requests
import tweepy
import urllib3

from sliver.database import connection, db_init
from sliver.config import Config
from sliver.exceptions import BaseError
from sliver.print import print
from sliver.strategies.hypnox import HypnoxTweet, HypnoxUser


class Stream(tweepy.StreamingClient):
    # def on_disconnect(self):
    #     print(exception="stream disconnect")
    #     super().on_disconnect()

    # def on_exception(self, exception):
    #     print("stream exception", exception=exception)
    #     super().on_exception(exception)

    # def on_connection_error(self):
    #     print(exception="stream connection error")
    #     super().on_connection_error()

    # def on_request_error(self, status_code):
    #     print(exception=f"stream request error {status_code}")
    #     super().on_request_error()

    def on_tweet(self, status):
        # ignore replies
        if status.in_reply_to_user_id:
            return

        try:
            if hasattr(status, "extended_tweet"):
                text = status.extended_tweet["full_text"]
            else:
                text = status.text
        except AttributeError:
            text = status.text

        time = (datetime.datetime.utcnow(),)

        # make the tweet single-line
        text = re.sub("\n", " ", text).strip()
        text = re.sub("\r", " ", text).strip()
        # remove any tab character
        text = re.sub("\t", " ", text).strip()

        # log to stdin
        print(text)
        tweet = HypnoxTweet(time=time, text=text)
        try:
            tweet.save()
        except Exception as e:
            if isinstance(e, peewee.InterfaceError) or isinstance(
                e, peewee.OperationalError
            ):
                connection.close()
                try:
                    connection.connect(reuse_if_open=True)
                    tweet.save()
                except peewee.OperationalError:
                    print("couldn't reestablish connection to database!")

                    # log to cache csv
                    print("error on inserting, caching instead", exception=e)
                    output = pandas.DataFrame({"time": [time], "text": [text]})
                    cache_file = Config().LOGS_DIR + "/cache.tsv"
                    with open(cache_file, "a") as f:
                        output.to_csv(
                            f, header=f.tell() == 0, mode="a", index=False, sep="\t"
                        )


def get_uids():
    client = tweepy.Client(Config().TWITTER_BEARER_TOKEN)

    pending = HypnoxUser.select().where(HypnoxUser.twitter_user_id.is_null())

    for user in pending:
        t_user = client.get_user(username=user.username)

        if not t_user.data:
            print(f"user {user.username} not found")
            continue

        user.twitter_user_id = t_user.data.id
        user.username = t_user.data.username
        user.save()

    u = [u.twitter_user_id for u in HypnoxUser.select()]
    if len(u) == 0:
        raise Exception("no users found")
    return u


def get_rules(uids):
    all_rules = []
    curr_rule = []

    for uid in uids:
        new_rule_str = f"from:{uid}"
        curr_rule_str = " OR ".join(curr_rule + [new_rule_str])

        if len(curr_rule_str) > 497:
            curr_rule_str = " OR ".join(curr_rule)
            all_rules.append(tweepy.StreamRule(f"{curr_rule_str} -is:retweet"))
            curr_rule = [new_rule_str]

        curr_rule.append(new_rule_str)

    return all_rules


def stream():
    db_init()

    argp = argparse.ArgumentParser()
    argp.add_argument("--reset", action="store_true")
    args = argp.parse_args()

    if Config().TWITTER_BEARER_TOKEN == "":
        raise BaseError("missing TWITTER_BEARER_TOKEN!")

    stream = Stream(Config().TWITTER_BEARER_TOKEN)

    if args.reset:
        print("resetting users and stream rules")
        uids = get_uids()

        curr_rules = stream.get_rules()
        if curr_rules.data:
            stream.delete_rules([rule.id for rule in curr_rules.data])

        stream.add_rules(get_rules(uids))

    print("streaming...")
    while not stream.running:
        try:
            stream.filter()

        except (
            requests.exceptions.Timeout,
            ssl.SSLError,
            urllib3.exceptions.ReadTimeoutError,
            requests.exceptions.ConnectionError,
        ) as e:
            print("network error", exception=e)

        except Exception as e:
            print("unexpected error", exception=e)

        except KeyboardInterrupt:
            print("got keyboard interrupt")
            break


if __name__ == "__main__":
    stream()
