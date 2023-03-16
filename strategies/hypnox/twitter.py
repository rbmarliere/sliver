import argparse
import datetime
import re
import ssl

import pandas
import peewee
import requests
import tweepy
import urllib3

import core
import strategies


class Stream(tweepy.StreamingClient):

    def on_disconnect(self):
        core.watchdog.warning("disconnected")
        super().on_disconnect()

    def on_exception(self, exception):
        core.watchdog.error("got exception", exception)
        super().on_exception(exception)

    def on_tweet(self, status):
        # ignore replies
        if status.in_reply_to_user_id:
            return

        time = datetime.datetime.utcnow(),
        text = status.text

        # make the tweet single-line
        text = re.sub("\n", " ", text).strip()
        text = re.sub("\r", " ", text).strip()
        # remove any tab character
        text = re.sub("\t", " ", text).strip()

        # log to stdin
        core.watchdog.info(text)
        tweet = strategies.hypnox.HypnoxTweet(time=time, text=text)
        try:
            tweet.save()
        except Exception as e:
            if (isinstance(e, peewee.InterfaceError)
                    or isinstance(e, peewee.OperationalError)):
                core.db.connection.close()
                try:
                    core.db.connection.connect(reuse_if_open=True)
                    tweet.save()
                except peewee.OperationalError:
                    core.watchdog.warning(
                        "couldn't reestablish connection to database!")

                    # log to cache csv
                    core.watchdog.error(
                        "error on inserting, caching instead...", e)
                    output = pandas.DataFrame({
                        "time": [time],
                        "text": [text]
                    })
                    cache_file = core.config["LOGS_DIR"] + "/cache.tsv"
                    with open(cache_file, "a") as f:
                        output.to_csv(f,
                                      header=f.tell() == 0,
                                      mode="a",
                                      index=False,
                                      sep="\t")


def get_uids():
    client = tweepy.Client(core.config["TWITTER_BEARER_TOKEN"])

    pending = core.strategies.hypnox. \
        HypnoxUser \
        .select() \
        .where(core.strategies.hypnox.HypnoxUser.twitter_user_id.is_null())

    for user in pending:
        t_user = client.get_user(username=user.username)

        if not t_user.data:
            core.watchdog.info("user {u} not found".format(u=user.username))
            continue

        user.twitter_user_id = t_user.data.id
        user.username = t_user.data.username
        user.save()

    u = [u.twitter_user_id for u in core.strategies.hypnox.HypnoxUser.select()]
    if len(u) == 0:
        raise Exception("no users found")
    return u


def get_rules(uids):
    all_rules = []
    curr_rule = []

    for uid in uids:
        new_rule_str = "from:{u}".format(u=uid)
        curr_rule_str = " OR ".join(curr_rule + [new_rule_str])

        if len(curr_rule_str) > 512:
            curr_rule_str = " OR ".join(curr_rule)
            all_rules.append(tweepy.StreamRule(curr_rule_str))
            curr_rule = [new_rule_str]

        curr_rule.append(new_rule_str)

    all_rules.append("lang:en -is:retweet")

    return all_rules


def stream():
    argp = argparse.ArgumentParser()
    argp.add_argument("--reset", action="store_true")
    args = argp.parse_args()

    core.watchdog.set_logger("stream")

    if (core.config["TWITTER_BEARER_TOKEN"] == ""):
        raise core.errors.BaseError("missing TWITTER_BEARER_TOKEN!")

    stream = Stream(core.config["TWITTER_BEARER_TOKEN"])

    if args.reset:
        core.watchdog.info("resetting users and stream rules")
        uids = get_uids()

        curr_rules = stream.get_rules()
        if curr_rules.data:
            stream.delete_rules([rule.id for rule in curr_rules.data])

        stream.add_rules(get_rules(uids))

    core.watchdog.info("streaming...")
    while not stream.running:
        try:
            stream.filter()
        except (requests.exceptions.Timeout, ssl.SSLError,
                urllib3.exceptions.ReadTimeoutError,
                requests.exceptions.ConnectionError) as e:
            core.watchdog.error("network error", e)
        except Exception as e:
            core.watchdog.error("unexpected error", e)
        except KeyboardInterrupt:
            core.watchdog.info("got keyboard interrupt")
            break


if __name__ == "__main__":
    stream()
