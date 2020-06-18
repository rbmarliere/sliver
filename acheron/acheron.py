from requests.exceptions import Timeout, ConnectionError
from ssl import SSLError
from urllib3.exceptions import ReadTimeoutError
import argparse
import datetime
import json
import logging
import os
import re
import tensorflow
import tensorflow_hub
import tweepy

logging.basicConfig(level=logging.INFO)

logging.error("Loading USE...")
use = tensorflow_hub.load("https://tfhub.dev/google/universal-sentence-encoder/4")

# parsing acheron arguments
tacitus_path = os.path.dirname(os.path.realpath(__file__)) + "/../tacitus"
argp = argparse.ArgumentParser(description="Gather relevant tweets.")
argp.add_argument("--model", help="Path to Tacitus' saved model.", type=os.path.abspath, default=tacitus_path + "/model")
argp.add_argument("--config", help="Path to a configuration file.", type=os.path.abspath, default=os.path.dirname(os.path.realpath(__file__)) + "/config.json")

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

# load temporal markers
temporal = open("temporal").read().splitlines()

class AcheronListener(tweepy.StreamListener):
	def __init__(self):
		super().__init__()
		self.tacitus = tensorflow.keras.models.load_model(args.model)

	def on_status(self, status):
		# ignore retweets
		if "retweeted_status" in status._json:
			return
		# ignore replies
		if status._json["in_reply_to_user_id"]:
			return
		# if tweet is truncated, get all text
		if "extended_tweet" in status._json:
			tweet = status.extended_tweet["full_text"]
		else:
			tweet = status.text
		tweet = re.sub("\n", " ", tweet)

		print("\n" + tweet)
		for w in temporal:
			if w in tweet:
				pred = self.tacitus.predict(use([tweet]))[0][1]
				score = format(pred, 'f')
				print(">>> SCORE: " + score + "\n")

				created_at = status._json["created_at"]
				user = status._json["user"]["screen_name"]
				url = "https://twitter.com/" + user + "/status/" + str(status._json["id"])

				today = datetime.datetime.now().strftime("%Y%m%d")
				with open("data/" + today + ".txt", "a") as out:
					print(created_at, file=out)
					print(user, file=out)
					print(url, file=out)
					print(tweet, file=out)
					print(">>> SCORE: " + score + "\n", file=out)

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
		print(uid, file=uids)
		users.append(uid)
	return users
try:
	uids = open("uids")
	users = uids.read().splitlines()
	if len(users) != len(config["TRACK_USERS"]):
		os.remove("uids")
		users = load_users()
except FileNotFoundError:
	users = load_users()

acheron = AcheronListener()
stream = tweepy.Stream(auth = api.auth, listener=acheron, timeout=600)

while not stream.running:
	try:
		stream.filter(
			languages=["en"],
			#follow=users,
			track=[ "bitcoin", "btc", "xbt" ],
			is_async=False
		)
	except (Timeout, SSLError, ReadTimeoutError, ConnectionError) as e:
		logging.warning("Network error!")
	except Exception as e:
		logging.error("Unexpected error!", e)
	finally:
		logging.info("Stream has crashed. System will restart twitter stream!")

