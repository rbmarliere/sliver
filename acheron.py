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
	def __init__(self, outputdir):
		super().__init__()
		self.outputdir = outputdir
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
		output_filename = datetime.datetime.now().strftime("%Y%m%d")
		tweet = pandas.DataFrame({ "date": [created_at], "username": [user], "url": [url], "tweet": [text] })
		logging.info(tweet)
		with open(self.outputdir+"/"+output_filename, "a") as f:
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
	config_filename = os.path.dirname(os.path.realpath(__file__)) + "/etc/acheron.conf"
	config = json.load(open(config_filename))
	keys_filename = os.path.dirname(os.path.realpath(__file__)) + "/etc/acheron.keys"
	keys = json.load(open(keys_filename))
	if config["TRACK_USERS"] == '':
		logging.error("empty user list in config! (TRACK_USERS) in (" + config_filename + ")")
		return 1

	logging.info("loading twitter API keys...")
	if keys["CONSUMER_KEY"] == '' or keys["CONSUMER_SECRET"] == '' or keys["ACCESS_KEY"] == '' or keys["ACCESS_SECRET"] == '':
		logging.error("empty keys in config! (CONSUMER_KEY, CONSUMER_SECRET, ACCESS_KEY, ACCESS_SECRET) in file (" + keys_filename + ")")
		return 1
	auth = tweepy.OAuthHandler(keys["CONSUMER_KEY"], keys["CONSUMER_SECRET"])
	auth.set_access_token(keys["ACCESS_KEY"], keys["ACCESS_SECRET"])
	api = tweepy.API(auth)

	logging.info("initializing...")
	outputdir = os.path.dirname(os.path.realpath(__file__)) + "/data/raw"
	if not os.path.exists(outputdir):
		logging.error(outputdir + " doesn't exist!")
		return 1
	logging.info("output directory set to " + outputdir)
	acheron = Acheron(outputdir)
	stream = tweepy.Stream(auth = api.auth, listener=acheron, timeout=600)

	logging.info("reading users...")
	try:
		# read saved uids file
		uids_filename = os.path.dirname(os.path.realpath(__file__)) + "/etc/acheron.uids"
		uids_file = open(uids_filename)
		uids = uids_file.read().splitlines()
		# if config was changed, reload all users
		if len(uids) != len(config["TRACK_USERS"]):
			os.remove(uids_filename)
			uids = save_uids(config["TRACK_USERS"], api)
	except FileNotFoundError:
		# initially, if no uids file is found, create one
		uids = save_uids(config["TRACK_USERS"], api)

	# start stream with proper exception handling so it doesn't crash
	while not stream.running:
		try:
			logging.info("streaming...")
			stream.filter(
				languages=["en"],
				follow=uids,
				#track=[ "bitcoin", "btc", "xbt" ],
				is_async=False
			)
		except (Timeout, SSLError, ReadTimeoutError, ConnectionError) as e:
			logging.error("network error!")
		except Exception as e:
			logging.error("unexpected error!", e)
		finally:
			logging.error("stream has crashed, restarting...")

