import argparse
import json
import os
import re
import tensorflow
import tweepy
import tensorflow_hub

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
				output = open("data", "a")
				print(tweet, file=output)
				pred = self.tacitus.predict(use([tweet]))
				print(">>> SCORE: " + format(pred[0][1], 'f') + "\n")

# initialize tweepy api object
auth = tweepy.OAuthHandler(config["CONSUMER_KEY"], config["CONSUMER_SECRET"])
auth.set_access_token(config["ACCESS_KEY"], config["ACCESS_SECRET"])
api = tweepy.API(auth)

# load the ids of the users to track into memory
def load_users():
	uids = open("uids", "a")
	users = []
	for user in config["TRACK_USERS"]:
		# retrieve user id by name from twitter api
		try:
			uid = str(api.get_user(user.strip()).id)
		except tweepy.error.TweepError:
			print("ERROR: User '" + user + "' not found.")
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
stream.filter(
	languages=["en"],
	follow=users,
	timeout=1000,
	#track=[ "bitcoin", "btc", "xbt" ],
	is_async=True
)

