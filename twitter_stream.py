from requests.exceptions import Timeout, ConnectionError
from ssl import SSLError
from urllib3.exceptions import ReadTimeoutError
import datetime
import json
import logging
import os
import pandas
import re
import tweepy

class Stream(tweepy.Stream):
	def on_status(self, status):
		# ignore retweets
		if "retweeted_status" in status._json:
			return
		# ignore replies
		if status._json["in_reply_to_user_id"]:
			return
		# if tweet is truncated, get all text
		if "extended_tweet" in status._json:
			text = status.extended_tweet["full_text"]
		else:
			text = status.text
		# make the tweet single-line
		text = re.sub("\n", " ", text)
		# parse tweet info
		created_at = datetime.datetime.strptime(status._json["created_at"], "%a %b %d %H:%M:%S %z %Y")
		user = status._json["user"]["screen_name"]
		url = "https://twitter.com/" + user + "/status/" + str(status.id)
		# output
		tweet = pandas.DataFrame({ "date": [created_at], "username": [user], "url": [url], "tweet": [text] })
		logging.info(url)
		logging.info(text)
		with open("data/raw.csv", "a") as f:
			tweet.to_csv(f, header=f.tell()==0, mode="a", index=False)

# save the ids of the users to track to disk
def save_uids(users, api):
	logging.info("loading uids...")
	uids_file = open(".uids", "a")
	uids = []
	for user in users:
		# retrieve user id by name from twitter api
		try:
			uid = str(api.get_user(screen_name=user.strip()).id)
			# save found uids to a file so it doesn't consume api each run
			print(uid, file=uids_file)
			uids.append(uid)
		except tweepy.errors.TweepyException:
			logging.error("User '" + user + "' not found.")
	return uids

def stream(argp, args):
	logging.info("loading config...")
	config = json.load(open("hypnox.conf"))
	if config["TRACK_USERS"] == "":
		logging.error("empty user list in config! (TRACK_USERS) in (" + config_filename + ")")
		return 1

	logging.info("loading twitter API keys...")
	if config["CONSUMER_KEY"] == "" or config["CONSUMER_SECRET"] == "" or config["ACCESS_KEY"] == "" or config["ACCESS_SECRET"] == "":
		logging.error("empty keys in config! (CONSUMER_KEY, CONSUMER_SECRET, ACCESS_KEY, ACCESS_SECRET)")
		return 1
	auth = tweepy.OAuthHandler(config["CONSUMER_KEY"], config["CONSUMER_SECRET"])
	auth.set_access_token(config["ACCESS_KEY"], config["ACCESS_SECRET"])
	api = tweepy.API(auth)

	logging.info("initializing...")
	stream = Stream(config["CONSUMER_KEY"], config["CONSUMER_SECRET"], config["ACCESS_KEY"], config["ACCESS_SECRET"])

	logging.info("reading users...")
	try:
		uids = open(".uids").read().splitlines()
		if len(uids) != len(config["TRACK_USERS"]):
			os.remove(".uids")
			uids = save_uids(config["TRACK_USERS"], api)
	except FileNotFoundError:
		uids = save_uids(config["TRACK_USERS"], api)

	while not stream.running:
		try:
			logging.info("streaming...")
			stream.filter(
				languages=["en"],
				follow=uids,
			)
		except (Timeout, SSLError, ReadTimeoutError, ConnectionError) as e:
			logging.error("network error!")
		except Exception as e:
			logging.error("unexpected error!", e)
		finally:
			logging.error("stream has crashed, restarting...")

