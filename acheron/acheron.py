import argparse
import datetime
import json
import logging
import os
import re
from ssl import SSLError

import pandas
import tweepy
from requests.exceptions import Timeout, ConnectionError
from urllib3.exceptions import ReadTimeoutError

# define logging level
logging.basicConfig(level=logging.INFO)

# parsing acheron arguments
tacitus_path = os.path.dirname(os.path.realpath(__file__)) + "/../tacitus"
argp = argparse.ArgumentParser(description="Gather relevant tweets.")
argp.add_argument("--model", help="Path to Tacitus' saved model.", type=os.path.abspath, default=tacitus_path + "/model")
argp.add_argument("--config", help="Path to a configuration file.", type=os.path.abspath, default=os.path.dirname(os.path.realpath(__file__)) + "/config.json")

# check if required files are there
args = argp.parse_args()
if not os.path.exists(args.config):
	print("Configuration not found!")
	exit(1)
if not os.path.exists(args.model):
	print("Model not found!")
	exit(1)

# load config parameters
with open(args.config) as f:
	config = json.load(f)

# load include markers
include = open("include").read().splitlines()

# load exclude markers
exclude = open("exclude").read().splitlines()

class AcheronListener(tweepy.StreamListener):
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

		print("\n" + text)

		# check tweet relevancy
		proc_tweet = False
		for word in text.split():
			# process tweets that contain include words
			if word in include:
				proc_tweet = True
			# ignore tweets that contain exclude words
			if word in exclude:
				proc_tweet = False
				break
		if proc_tweet == False:
			return

		# parse tweet info
		created_at = datetime.datetime.strptime(status._json["created_at"], "%a %b %d %H:%M:%S %z %Y")
		user = status._json["user"]["screen_name"]
		url = "https://twitter.com/" + user + "/status/" + str(status.id)

		# output
		filename = datetime.datetime.now().strftime("%Y%m%d")
		tweet = pandas.DataFrame({ "date": [created_at], "username": [user], "url": [url], "tweet": [text] })
		with open("data/"+filename+".csv", "a") as f:
			tweet.to_csv(f, header=f.tell()==0, mode="a", index=False)

# initialize tweepy api object
auth = tweepy.OAuthHandler(config["CONSUMER_KEY"], config["CONSUMER_SECRET"])
auth.set_access_token(config["ACCESS_KEY"], config["ACCESS_SECRET"])
api = tweepy.API(auth)

# load the ids of the users to track into memory
def load_users():
	logging.info("Loading users...")
	uids = open("uids", "a")
	users = []
	for user in config["TRACK_USERS"]:
		# retrieve user id by name from twitter api
		try:
			uid = str(api.get_user(user.strip()).id)
		except tweepy.error.TweepError:
			logging.warning("User '" + user + "' not found.")
		# save found uids to a file so it doesn't consume api each run
		print(uid, file=uids)
		users.append(uid)
	return users
try:
	# read saved uids file
	uids = open("uids")
	users = uids.read().splitlines()
	# if config was changed, reload all users
	if len(users) != len(config["TRACK_USERS"]):
		os.remove("uids")
		users = load_users()
except FileNotFoundError:
	# initially, if no uids file is found, create one
	users = load_users()

# declare listener and stream
acheron = AcheronListener()
stream = tweepy.Stream(auth = api.auth, listener=acheron, timeout=600)

# start stream with proper exception handling so it doesn't crash
while not stream.running:
	try:
		logging.info("Streaming...")
		stream.filter(
			languages=["en"],
			follow=users,
			#track=[ "bitcoin", "btc", "xbt" ],
			is_async=False
		)
	except (Timeout, SSLError, ReadTimeoutError, ConnectionError) as e:
		logging.warning("Network error!")
	except Exception as e:
		logging.error("Unexpected error!", e)
	finally:
		logging.info("Stream has crashed. System will restart twitter stream!")

