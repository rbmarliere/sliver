from tensorflow.keras.models import load_model
import argparse
import json
import nltk
import os
import re
import tweepy
import preprocessor

# download stopwords from nltk
nltk.download("stopwords")

# parsing acheron arguments
argp = argparse.ArgumentParser(description="Gather relevant tweets.")
argp.add_argument("--model", help="Path to Tacitus' saved model.", type=os.path.abspath, default=os.path.dirname(os.path.realpath(__file__)) + "/../tacitus/model")
argp.add_argument("--config", help="Path to a configuration file.", type=os.path.abspath, default=os.path.dirname(os.path.realpath(__file__)) + "/config.json")

args = argp.parse_args()
if not os.path.exists(args.config):
	print("Configuration not found!")
	exit(1)
if not os.path.exists(args.model):
	print("Model not found!")
	exit(1)

# load config parameters to memory
with open(args.config) as f:
	config = json.load(f)

class AcheronListener(tweepy.StreamListener):
	def __init__(self):
		super().__init__()
		self.tacitus = load_model(args.model)

	def on_status(self, status):
		# ignore retweets
		if "retweeted_status" in status._json:
			return
		# ignore replies
		#if status._json["in_reply_to_user_id"]:
		#	return
		# if tweet is truncated, get all text
		if "extended_tweet" in status._json:
			tweet = status.extended_tweet["full_text"]
		else:
			tweet = status.text
		tweet = re.sub("\n", " ", tweet)
		print(tweet)
		# clean the tweet text
		tweet = preprocessor.clean(tweet)
		with open("data", "a") as output:
			if len(tweet.split()) > 3:
				print(tweet, file=output)
				pred = self.tacitus.predict([tweet])
				print(pred[0][0])
				print()

# initialize tweepy api object
auth = tweepy.OAuthHandler(config["CONSUMER_KEY"], config["CONSUMER_SECRET"])
auth.set_access_token(config["ACCESS_KEY"], config["ACCESS_SECRET"])
api = tweepy.API(auth)

# load the ids of the users to track into memory
try:
	with open("uids") as uids:
		users = uids.read().splitlines()
except FileNotFoundError:
	users = []
	with open("uids", "a") as uids:
		for user in config["TRACK_USERS"]:
			# retrieve user id by name from twitter api
			uid = str(api.get_user(user.strip()).id)
			print(uid, file=uids)
			users.append(uid)

acheron = AcheronListener()
stream = tweepy.Stream(auth = api.auth, listener=acheron)
#stream.filter(languages=["en"], follow=users, is_async=True)
stream.filter(languages=["en"], track=["bitcoin", "btc", "xbt"], is_async=True)

