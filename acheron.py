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

class Acheron(tweepy.StreamListener):
	def __init__(self, output):
		super().__init__()
		self.output = output
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
		logging.info("\n" + text)
		# parse tweet info
		created_at = datetime.datetime.strptime(status._json["created_at"], "%a %b %d %H:%M:%S %z %Y")
		user = status._json["user"]["screen_name"]
		url = "https://twitter.com/" + user + "/status/" + str(status.id)
		# output
		filename = datetime.datetime.now().strftime("%Y%m%d")
		tweet = pandas.DataFrame({ "date": [created_at], "username": [user], "url": [url], "tweet": [text] })
		with open(self.output+"/"+filename, "a") as f:
			tweet.to_csv(f, header=f.tell()==0, mode="a", index=False)

# save the ids of the users to track to disk
def save_uids(users, api):
	logging.info("loading uids...")
	f = os.path.dirname(os.path.realpath(__file__)) + "/etc/acheron.uids"
	uids_file = open(f, "a")
	uids = []
	for user in users:
		# retrieve user id by name from twitter api
		try:
			uid = str(api.get_user(user.strip()).id)
			# save found uids to a file so it doesn't consume api each run
			print(uid, file=uids_file)
			uids.append(uid)
		except tweepy.error.TweepError:
			logging.error("User '" + user + "' not found.")
	return uids

def stream(argp, args):
	logging.info("loading config...")
	config_file = os.path.dirname(os.path.realpath(__file__)) + "/etc/acheron.conf"
	config = json.load(open(config_file))

	logging.info("loading twitter API keys...")
	if config["CONSUMER_KEY"] == '' or config["CONSUMER_SECRET"] == '' or config["ACCESS_KEY"] == '' or config["ACCESS_SECRET"] == '':
		logging.error("empty keys in config!")
		return 1
	auth = tweepy.OAuthHandler(config["CONSUMER_KEY"], config["CONSUMER_SECRET"])
	auth.set_access_token(config["ACCESS_KEY"], config["ACCESS_SECRET"])
	api = tweepy.API(auth)

	logging.info("initializing...")
	output = os.path.dirname(os.path.realpath(__file__)) + "/data/raw"
	logging.info("output directory set to " + output)
	acheron = Acheron(output)
	stream = tweepy.Stream(auth = api.auth, listener=acheron, timeout=600)

	logging.info("reading users...")
	try:
		# read saved uids file
		uids_file = os.path.dirname(os.path.realpath(__file__)) + "/etc/acheron.uids"
		uids = open(uids_file)
		users = uids.read().splitlines()
		# if config was changed, reload all users
		if len(users) != len(config["TRACK_USERS"]):
			os.remove(uids_file)
			users = save_uids(config["TRACK_USERS"], api)
	except FileNotFoundError:
		# initially, if no uids file is found, create one
		users = save_uids(config["TRACK_USERS"], api)

	# start stream with proper exception handling so it doesn't crash
	while not stream.running:
		try:
			logging.info("streaming...")
			stream.filter(
				languages=["en"],
				#follow=users,
				track=[ "bitcoin", "btc", "xbt" ],
				is_async=False
			)
		except (Timeout, SSLError, ReadTimeoutError, ConnectionError) as e:
			logging.error("network error!")
		except Exception as e:
			logging.error("unexpected error!", e)
		finally:
			logging.error("stream has crashed, restarting...")

